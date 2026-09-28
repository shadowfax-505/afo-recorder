#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include "board.h"
#include "format.h"
#include "sensors.h"
#include "wifi_live.h"
#include "driver/gpio.h"

#include "driver/sdmmc_host.h"
#include "esp_vfs_fat.h"
#include "esp_timer.h"
#include "esp_random.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/event_groups.h"

static const char *TAG="afo";
enum { STOP_NORMAL=0, STOP_STORAGE=1, STOP_QUEUE=2, STOP_SENSOR=3,
       STOP_BATTERY=4, STOP_LIMIT=5, STOP_TIMING=6, STOP_USB=7 };
static QueueHandle_t queue;
static EventGroupHandle_t done;
static TaskHandle_t emg_task_handle;
static uint64_t adc_irq_time;
static uint32_t adc_irq_count;
static atomic_bool running;
static atomic_int fault;
static atomic_uint timer_missed,queue_dropped,imu_errors,fifo_overflows,adc_errors;
static atomic_uint emg_records,foot_records,shank_records,queue_high_water;
static portMUX_TYPE irq_lock=portMUX_INITIALIZER_UNLOCKED;
static uint64_t irq_time[2];
static uint32_t irq_count[2];
static int current_battery;
static uint32_t status_seq;
static uint8_t block[8192];
static size_t block_used;

static void set_fault(int why) {
    if(why==STOP_STORAGE) {atomic_store(&fault,why);return;}
    int expected=0; atomic_compare_exchange_strong(&fault,&expected,why);
}
static void enqueue(const afo_record_t *r) {
    if(xQueueSend(queue,r,0)!=pdTRUE) { queue_dropped++; set_fault(STOP_QUEUE); }
    else {
        unsigned n=uxQueueMessagesWaiting(queue),old=queue_high_water;
        while(n>old&&!atomic_compare_exchange_weak(&queue_high_water,&old,n)) {}
    }
}
static void adc_irq(void *arg) {
    (void)arg;BaseType_t wake=pdFALSE;
    portENTER_CRITICAL_ISR(&irq_lock);
    adc_irq_time=adc_sample_timestamp();adc_irq_count++;
    portEXIT_CRITICAL_ISR(&irq_lock);
    if(emg_task_handle)vTaskNotifyGiveFromISR(emg_task_handle,&wake);
    if(wake)portYIELD_FROM_ISR();
}
static void imu_irq(void *arg) {
    unsigned id=(unsigned)(uintptr_t)arg;
    portENTER_CRITICAL_ISR(&irq_lock);
    irq_time[id]=(uint64_t)esp_timer_get_time(); irq_count[id]++;
    portEXIT_CRITICAL_ISR(&irq_lock);
}
static void irq_snapshot(unsigned id,uint64_t *time,uint32_t *count) {
    portENTER_CRITICAL(&irq_lock); *time=irq_time[id]; *count=irq_count[id];
    portEXIT_CRITICAL(&irq_lock);
}
static void emg_task(void *arg) {
    (void)arg;uint32_t previous=0;
    while(atomic_load(&running)) {
        uint32_t n=ulTaskNotifyTake(pdTRUE,pdMS_TO_TICKS(20));
        if(!atomic_load(&running))break;
        if(!gpio_get_level(USB_PRESENT_PIN)){set_fault(STOP_USB);atomic_store(&running,false);break;}
        if(!n){set_fault(STOP_TIMING);break;}
        uint64_t stamp;uint32_t seq;
        portENTER_CRITICAL(&irq_lock);stamp=adc_irq_time;seq=adc_irq_count;portEXIT_CRITICAL(&irq_lock);
        uint32_t slots=seq-previous;previous=seq;
        if(!slots)continue;
        if(slots>1)timer_missed+=slots-1;
        emg_payload_t p={.elapsed_slots=slots,.active_mask=(1u<<EMG_CHANNEL_COUNT)-1};
        p.read_start_us=esp_timer_get_time();
        int32_t codes[4];uint16_t status,crc;
        esp_err_t e=emg_frame(codes,&status,&crc);
        p.read_duration_us=esp_timer_get_time()-p.read_start_us;
        if(e!=ESP_OK){adc_errors++;set_fault(STOP_SENSOR);break;}
        memcpy(p.codes,codes,sizeof(codes));p.adc_status=status;p.adc_crc=crc;
        portENTER_CRITICAL(&irq_lock);uint32_t after=adc_irq_count;portEXIT_CRITICAL(&irq_lock);
        uint8_t flags=slots>1?FLAG_GAP:0;
        if(after!=seq){flags|=FLAG_TIMING_UNCERTAIN;set_fault(STOP_TIMING);}
        afo_record_t r;afo_record_init(&r,AFO_EMG_RECORD_KIND,flags,seq,stamp,&p,sizeof(p));
        emg_records++;enqueue(&r);
    }
    xEventGroupSetBits(done,1);vTaskDelete(NULL);
}
static void imu_task(void *arg) {
    (void)arg; uint8_t data[2048];uint32_t seq[2]={0};
    while(atomic_load(&running)) {
        for(unsigned id=0;id<2;id++) {
            uint64_t anchor,after_time;uint32_t before,after;
            irq_snapshot(id,&anchor,&before);
            uint64_t t0=esp_timer_get_time();size_t packets;bool overflow;
            esp_err_t e=imu_fifo(id,data,sizeof(data),&packets,&overflow);
            uint64_t t1=esp_timer_get_time();irq_snapshot(id,&after_time,&after);
            if(e!=ESP_OK) { imu_errors++;set_fault(STOP_SENSOR);continue; }
            if(overflow) { fifo_overflows++;set_fault(STOP_SENSOR);continue; }
            if(!anchor||t1-anchor>100000) { imu_errors++;set_fault(STOP_SENSOR);continue; }
            if(!packets) continue;
            // Back-propagate FIFO intervals from the latest IRQ anchor. This is an
            // estimate, not calibrated physical sample time; preserve all raw evidence.
            uint64_t lag[128]={0};
            for(int k=(int)packets-2;k>=0;k--) {
                uint16_t a=(data[k*16+14]<<8)|data[k*16+15];
                uint16_t b=(data[(k+1)*16+14]<<8)|data[(k+1)*16+15];
                lag[k]=lag[k+1]+(uint16_t)(b-a);
            }
            for(size_t k=0;k<packets;k++) {
                const uint8_t *p=data+16*k;
                // Standard packet: accel+gyro, 16-bit format, ODR timestamp.
                if((p[0]&0xfc)!=0x68) { imu_errors++;set_fault(STOP_SENSOR);continue; }
                imu_payload_t out;memcpy(out.fifo_packet,p,16);
                out.read_start_us=t0;out.read_end_us=t1;out.irq_anchor_us=anchor;
                uint8_t flags=FLAG_TIMING_UNCERTAIN;
                if(after!=before||anchor<lag[k]) flags|=FLAG_GAP;
                for(unsigned j=1;j<13;j+=2)
                    if(p[j]==0x80&&p[j+1]==0) flags|=FLAG_INVALID;
                uint64_t estimate=anchor>=lag[k]?anchor-lag[k]:0;
                afo_record_t r;afo_record_init(&r,id?REC_SHANK:REC_FOOT,flags,
                    ++seq[id],estimate,&out,sizeof(out));
                if(id)shank_records++;else foot_records++;
                enqueue(&r);
            }
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    xEventGroupSetBits(done,2);vTaskDelete(NULL);
}
static status_payload_t snapshot(void) {
    status_payload_t s={timer_missed,queue_dropped,imu_errors,fifo_overflows,
        adc_errors,emg_records,foot_records,shank_records,
        current_battery>0?(uint32_t)current_battery:0,queue_high_water};return s;
}
static bool write_all(int fd,const void *data,size_t size) {
    const uint8_t *p=data;
    while(size) {
        ssize_t n=write(fd,p,size);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)return false;
        p+=n;size-=(size_t)n;
    }
    return true;
}
static bool flush_block(int fd) {
    if(!block_used)return true;
    if(!write_all(fd,block,block_used))return false;
    block_used=0;return true;
}
static bool append_record(int fd,const afo_record_t *r) {
    if(block_used+sizeof(*r)>sizeof(block)&&!flush_block(fd))return false;
    memcpy(block+block_used,r,sizeof(*r));block_used+=sizeof(*r);wifi_live_offer(r);return true;
}
static bool free_space_ok(void) {
    uint64_t total,free;
    return esp_vfs_fat_info(SD_MOUNT,&total,&free)==ESP_OK&&free>=MIN_FREE_BYTES;
}
static int open_session(char *path,size_t capacity) {
    for(unsigned i=0;i<100;i++) {
        snprintf(path,capacity,SD_MOUNT "/trial_%08lx.afolog",(unsigned long)esp_random());
        int fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0644);
        if(fd>=0)return fd;
        if(errno!=EEXIST)return -1;
    }
    return -1;
}
static bool button_press(void) {
    static int stable=1,last=1;static int64_t changed=0;
    int level=gpio_get_level(BUTTON_PIN);int64_t now=esp_timer_get_time();
    if(level!=last) {last=level;changed=now;}
    if(now-changed>50000&&stable!=level) {stable=level;return stable==0;}
    return false;
}
static void reset_stats(void) {
    timer_missed=0;queue_dropped=0;imu_errors=0;fifo_overflows=0;adc_errors=0;
    emg_records=0;foot_records=0;shank_records=0;queue_high_water=0;status_seq=0;
    fault=0;block_used=0;xQueueReset(queue);xEventGroupClearBits(done,3);
}
static void record_session(void) {
    current_battery=battery_mv();
    if(!gpio_get_level(USB_PRESENT_PIN)||current_battery<BATTERY_WARN_MV||!free_space_ok()) {
        gpio_set_level(LED_ERROR,1);ESP_LOGE(TAG,"Start refused: USB attached, battery, or free space");return;
    }
    if(adc_configure()!=ESP_OK){gpio_set_level(LED_ERROR,1);return;}
    char path[80];int fd=open_session(path,sizeof(path));
    if(fd<0) {gpio_set_level(LED_ERROR,1);ESP_LOGE(TAG,"Cannot create recording");return;}
    reset_stats();gpio_set_level(LED_ERROR,0);
    char meta[2048];
    snprintf(meta,sizeof(meta),
      "{" AFO_ADC_METADATA AFO_SD_METADATA
      "\"firmware\":\"dual-1.1\",\"hardware_variant\":\"" HARDWARE_VARIANT "\","
      "\"synthetic\":false,\"trial_id\":\"%s\",\"clock\":\"esp_timer_boot_us\","
      "\"emg_hz\":8000,\"imu_hz\":200,\"imu_enabled\":true,"
      "\"active_channel_count\":%d,\"emg_channels\":%s,"
      "\"calibration_state\":\"uncalibrated\",\"simultaneous\":true,"
      "\"accel_range_g\":16,\"gyro_range_dps\":2000,\"imu_timestamp_tick_us\":1,"
      "\"imu_timing_calibrated\":false,\"imu_locations\":[\"foot\",\"shank\"],"
      "\"placement_verified\":false,\"record_bytes\":64,\"usb_recording_inhibit\":true,"
      "\"analog_filter\":\"3.3k/47nF buffer; equal 6.65k RAW/VMID mixer and 47nF buffer; 100R per ADC leg and 1nF differential\","
      "\"clock_or_filter_delay_correction\":\"none\",\"notes\":\"Engineering prototype; physical validation pending\"}",
      strrchr(path,'/')+1,EMG_CHANNEL_COUNT,
      EMG_CHANNEL_COUNT==2?"[\"EMG1\",\"EMG2\"]":"[\"EMG1\",\"EMG2\",\"EMG3\",\"EMG4\"]");
    uint8_t *header=malloc(AFO_HEADER_BYTES);
    bool good=header&&afo_header(header,meta)==0&&write_all(fd,header,AFO_HEADER_BYTES)&&fsync(fd)==0;
    free(header);
    if(!good) {close(fd);gpio_set_level(LED_ERROR,1);return;}
    portENTER_CRITICAL(&irq_lock);memset(irq_time,0,sizeof(irq_time));memset(irq_count,0,sizeof(irq_count));portEXIT_CRITICAL(&irq_lock);
    if(ENABLE_IMUS) {gpio_intr_enable(FOOT_INT);gpio_intr_enable(SHANK_INT);}
    if(ENABLE_IMUS&&(imu_start(0)!=ESP_OK||imu_start(1)!=ESP_OK)) {
        imu_stop(0);imu_stop(1);gpio_intr_disable(FOOT_INT);gpio_intr_disable(SHANK_INT);
        close(fd);gpio_set_level(LED_ERROR,1);return;
    }
    portENTER_CRITICAL(&irq_lock);adc_irq_time=0;adc_irq_count=0;portEXIT_CRITICAL(&irq_lock);
    wifi_live_begin(meta);
    running=true;
    BaseType_t a=xTaskCreatePinnedToCore(emg_task,"emg",4096,NULL,22,&emg_task_handle,1);
    BaseType_t b=pdPASS;
    if(ENABLE_IMUS)b=xTaskCreatePinnedToCore(imu_task,"imu",12288,NULL,18,NULL,0);
    else xEventGroupSetBits(done,2);
    if(a!=pdPASS||b!=pdPASS) {
        running=false;if(a==pdPASS)xTaskNotifyGive(emg_task_handle);
        if(a!=pdPASS)xEventGroupSetBits(done,1);
        if(b!=pdPASS)xEventGroupSetBits(done,2);
        xEventGroupWaitBits(done,3,pdFALSE,pdTRUE,portMAX_DELAY);
        if(ENABLE_IMUS) {imu_stop(0);imu_stop(1);}
        close(fd);gpio_set_level(LED_ERROR,1);return;
    }
    gpio_intr_enable(ADC_DRDY);
    if(adc_stream_start()!=ESP_OK)set_fault(STOP_SENSOR);
    gpio_set_level(LED_RECORD,1);ESP_LOGI(TAG,"Recording %s",path);
    int64_t start=esp_timer_get_time(),health=start;unsigned low_count=0;
    while(!atomic_load(&fault)) {
        afo_record_t r;
        if(xQueueReceive(queue,&r,pdMS_TO_TICKS(10))==pdTRUE&&!append_record(fd,&r))set_fault(STOP_STORAGE);
        if(!gpio_get_level(USB_PRESENT_PIN))set_fault(STOP_USB);
        if(button_press())break;
        int64_t now=esp_timer_get_time();
        if(now-health>=1000000) {
            health=now;current_battery=battery_mv();
            gpio_set_level(LED_BATTERY,current_battery<BATTERY_WARN_MV);
            if(current_battery<0) set_fault(STOP_SENSOR);
            if(current_battery<BATTERY_STOP_MV)low_count++;else low_count=0;
            if(low_count>=3)set_fault(STOP_BATTERY);
            status_payload_t s=snapshot();afo_record_init(&r,REC_STATUS,0,++status_seq,now,&s,sizeof(s));
            if(!append_record(fd,&r)||!flush_block(fd)||fsync(fd)!=0||!free_space_ok())set_fault(STOP_STORAGE);
            if((uint64_t)(now-start)>=MAX_SESSION_US)set_fault(STOP_LIMIT);
        }
    }
    adc_stream_stop();gpio_intr_disable(ADC_DRDY);running=false;xTaskNotifyGive(emg_task_handle);
    gpio_intr_disable(FOOT_INT);gpio_intr_disable(SHANK_INT);
    xEventGroupWaitBits(done,3,pdFALSE,pdTRUE,portMAX_DELAY);
    if(ENABLE_IMUS&&(imu_stop(0)!=ESP_OK||imu_stop(1)!=ESP_OK))set_fault(STOP_SENSOR);
    emg_task_handle=NULL;
    afo_record_t r;
    while(xQueueReceive(queue,&r,0)==pdTRUE) {
        if(atomic_load(&fault)!=STOP_STORAGE&&!append_record(fd,&r))set_fault(STOP_STORAGE);
    }
    status_payload_t final=snapshot();int reason=atomic_load(&fault);
    afo_record_init(&r,REC_END,(uint8_t)reason,++status_seq,esp_timer_get_time(),&final,sizeof(final));
    bool saved=reason!=STOP_STORAGE&&append_record(fd,&r)&&flush_block(fd)&&fsync(fd)==0;
    if(close(fd)!=0)saved=false;
    gpio_set_level(LED_RECORD,0);gpio_set_level(LED_ERROR,!saved||reason!=STOP_NORMAL);
    ESP_LOGI(TAG,"Stopped, reason=%d, finalized=%d, missed=%lu, dropped=%lu",reason,saved,
       (unsigned long)final.timer_missed,(unsigned long)final.queue_dropped);
}
void app_main(void) {
    afo_format_init();
    gpio_config_t out={.pin_bit_mask=(1ULL<<LED_RECORD)|(1ULL<<LED_ERROR)|(1ULL<<LED_BATTERY),.mode=GPIO_MODE_OUTPUT};
    ESP_ERROR_CHECK(gpio_config(&out));
    gpio_config_t button={.pin_bit_mask=1ULL<<BUTTON_PIN,.mode=GPIO_MODE_INPUT,.pull_up_en=1};
    ESP_ERROR_CHECK(gpio_config(&button));
    gpio_config_t ints={.pin_bit_mask=(1ULL<<FOOT_INT)|(1ULL<<SHANK_INT),.mode=GPIO_MODE_INPUT,.intr_type=GPIO_INTR_POSEDGE};
    ESP_ERROR_CHECK(gpio_config(&ints));ESP_ERROR_CHECK(gpio_install_isr_service(0));
    ESP_ERROR_CHECK(gpio_isr_handler_add(FOOT_INT,imu_irq,(void*)0));
    ESP_ERROR_CHECK(gpio_isr_handler_add(SHANK_INT,imu_irq,(void*)1));
    gpio_intr_disable(FOOT_INT);gpio_intr_disable(SHANK_INT);
    gpio_config_t usb={.pin_bit_mask=1ULL<<USB_PRESENT_PIN,.mode=GPIO_MODE_INPUT};
    ESP_ERROR_CHECK(gpio_config(&usb));
    gpio_config_t drdy={.pin_bit_mask=1ULL<<ADC_DRDY,.mode=GPIO_MODE_INPUT,.intr_type=GPIO_INTR_NEGEDGE};
    ESP_ERROR_CHECK(gpio_config(&drdy));ESP_ERROR_CHECK(gpio_isr_handler_add(ADC_DRDY,adc_irq,NULL));
    gpio_intr_disable(ADC_DRDY);
    queue=xQueueCreate(RECORD_QUEUE_LENGTH,sizeof(afo_record_t));done=xEventGroupCreate();
    if(!queue||!done||sensors_init()!=ESP_OK||battery_init()!=ESP_OK)goto failed;
    sdmmc_host_t host=SDMMC_HOST_DEFAULT();host.max_freq_khz=SDMMC_FREQ_DEFAULT;
    sdmmc_slot_config_t slot=SDMMC_SLOT_CONFIG_DEFAULT();
    slot.width=1;slot.clk=SD_CLK;slot.cmd=SD_CMD;slot.d0=SD_D0;
    esp_vfs_fat_sdmmc_mount_config_t mount={.format_if_mount_failed=false,.max_files=2,.allocation_unit_size=16384};
    sdmmc_card_t *card;
    if(esp_vfs_fat_sdmmc_mount(SD_MOUNT,&host,&slot,&mount,&card)!=ESP_OK)goto failed;
    esp_err_t wifi_result=wifi_live_init();
    if(wifi_result!=ESP_OK)ESP_LOGW(TAG,"Wi-Fi unavailable (%s); SD-only operation",esp_err_to_name(wifi_result));
    ESP_LOGI(TAG,"Ready; press button to record. Never attach electrodes while charging.");
    for(;;) {
        current_battery=battery_mv();gpio_set_level(LED_BATTERY,current_battery<BATTERY_WARN_MV);
        if(button_press())record_session();
        vTaskDelay(pdMS_TO_TICKS(20));
    }
failed:
    ESP_LOGE(TAG,"Initialization failed; recording disabled. Check sensors, battery monitor and SD.");
    for(;;) {gpio_set_level(LED_ERROR,1);vTaskDelay(pdMS_TO_TICKS(250));gpio_set_level(LED_ERROR,0);vTaskDelay(pdMS_TO_TICKS(250));}
}
