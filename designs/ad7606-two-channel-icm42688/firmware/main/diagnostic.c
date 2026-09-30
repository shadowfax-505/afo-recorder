/* Bench-only diagnostic: no SD mount, networking, or recording session.
 * USB is intentionally usable for instrumented tests. NEVER attach electrodes.
 * Stage 2 needs only controller/power; 3-5 add ADC/analog; 6 adds IMUs.
 */
#include <stdio.h>
#include <inttypes.h>
#include <limits.h>
#include <math.h>
#include <stdatomic.h>
#include "board.h"
#include "sensors.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
static TaskHandle_t reader;
static portMUX_TYPE lock=portMUX_INITIALIZER_UNLOCKED;
static uint32_t edges,imu_edges[2],imu_packets[2];
static int16_t imu_last[2][6];
static uint16_t imu_ticks[2];
static atomic_bool diagnostic_fault;
static void imu_irq(void *arg){
    unsigned id=(unsigned)(uintptr_t)arg;
    portENTER_CRITICAL_ISR(&lock);imu_edges[id]++;portEXIT_CRITICAL_ISR(&lock);
}
static void irq(void *arg) {
    portENTER_CRITICAL_ISR(&lock);edges++;portEXIT_CRITICAL_ISR(&lock);
    BaseType_t wake=pdFALSE;vTaskNotifyGiveFromISR(reader,&wake);
    if(wake)portYIELD_FROM_ISR();
}
static void fail(const char *step,esp_err_t e){
    bool first=!atomic_exchange(&diagnostic_fault,true);
    adc_stream_stop();
    if(first)printf("FAIL,%s,%s\n",step,esp_err_to_name(e));
    gpio_set_level(LED_ERROR,1);
    while(1)vTaskDelay(pdMS_TO_TICKS(1000));
}
static void imu_reader(void *arg){
    (void)arg;uint8_t buf[2048];
    while(1){
        for(unsigned i=0;i<AFO_IMU_COUNT;i++){
            size_t packets=0;bool overflow=false;
            esp_err_t e=imu_fifo(i,buf,sizeof(buf),&packets,&overflow);
            if(e!=ESP_OK||overflow)fail("IMU FIFO/read",e!=ESP_OK?e:ESP_ERR_INVALID_SIZE);
            for(size_t k=0;k<packets;k++)if((buf[k*16]&0xfc)!=0x68)fail("IMU FIFO header",ESP_ERR_INVALID_RESPONSE);
            portENTER_CRITICAL(&lock);imu_packets[i]+=packets;
            if(packets){
                const uint8_t *last=buf+(packets-1)*16;
                for(unsigned axis=0;axis<6;axis++)imu_last[i][axis]=(int16_t)((last[1+2*axis]<<8)|last[2+2*axis]);
                imu_ticks[i]=(last[14]<<8)|last[15];
            }
            portEXIT_CRITICAL(&lock);
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
void app_main(void){
    gpio_config_t out={.pin_bit_mask=(1ULL<<LED_RECORD)|(1ULL<<LED_ERROR)|(1ULL<<LED_BATTERY),.mode=GPIO_MODE_OUTPUT};
    ESP_ERROR_CHECK(gpio_config(&out));
    gpio_config_t in={.pin_bit_mask=(1ULL<<BUTTON_PIN)|(1ULL<<USB_PRESENT_PIN),.mode=GPIO_MODE_INPUT,.pull_up_en=GPIO_PULLUP_ENABLE};
    ESP_ERROR_CHECK(gpio_config(&in));
    printf("BENCH ONLY; NO ELECTRODES. stage=%d hardware=%s channels=%d\n",AFO_DIAGNOSTIC_STAGE,HARDWARE_VARIANT,EMG_CHANNEL_COUNT);
    if(AFO_DIAGNOSTIC_STAGE==2){
        unsigned tick=0;
        while(1){gpio_set_level(LED_RECORD,tick&1);gpio_set_level(LED_ERROR,(tick>>1)&1);gpio_set_level(LED_BATTERY,(tick>>2)&1);
            printf("CONTROLLER,tick=%u,button=%d,usb_attached=%d\n",tick++,!gpio_get_level(BUTTON_PIN),!gpio_get_level(USB_PRESENT_PIN));vTaskDelay(pdMS_TO_TICKS(500));}
    }
    esp_err_t e=adc_bus_init();if(e!=ESP_OK)fail("ADC bus/reset",e);
    reader=xTaskGetCurrentTaskHandle();
    gpio_config_t drdy={.pin_bit_mask=1ULL<<ADC_DRDY,.mode=GPIO_MODE_INPUT,.intr_type=GPIO_INTR_NEGEDGE};
    ESP_ERROR_CHECK(gpio_config(&drdy));ESP_ERROR_CHECK(gpio_install_isr_service(0));ESP_ERROR_CHECK(gpio_isr_handler_add(ADC_DRDY,irq,NULL));
    if(AFO_DIAGNOSTIC_STAGE==6){
        e=imu_bus_init(AFO_IMU_COUNT);if(e!=ESP_OK)fail("IMU init/identity/readback",e);
        for(unsigned i=0;i<AFO_IMU_COUNT;i++){
            unsigned pin=i?SHANK_INT:FOOT_INT;
            gpio_config_t in={.pin_bit_mask=1ULL<<pin,.mode=GPIO_MODE_INPUT,.intr_type=GPIO_INTR_POSEDGE};
            ESP_ERROR_CHECK(gpio_config(&in));ESP_ERROR_CHECK(gpio_isr_handler_add(pin,imu_irq,(void *)(uintptr_t)i));
            e=imu_start(i);if(e!=ESP_OK)fail("IMU start",e);
        }
        // Lower-priority FIFO service never blocks the ADC reader on SPI3.
        if(xTaskCreatePinnedToCore(imu_reader,"diagnostic_imu",8192,NULL,10,NULL,0)!=pdPASS)fail("IMU task",ESP_ERR_NO_MEM);
    }
    vTaskPrioritySet(NULL,22);
    while(1){
        int32_t low[4]={INT_MAX,INT_MAX,INT_MAX,INT_MAX},high[4]={INT_MIN,INT_MIN,INT_MIN,INT_MIN};
        int64_t sum[4]={0};double sumsq[4]={0};uint32_t good=0;
        uint32_t prior_irq[2],prior_packets[2];
        portENTER_CRITICAL(&lock);
        for(unsigned i=0;i<2;i++){prior_irq[i]=imu_edges[i];prior_packets[i]=imu_packets[i];}
        portEXIT_CRITICAL(&lock);
        ulTaskNotifyTake(pdTRUE,0);
        portENTER_CRITICAL(&lock);edges=0;portEXIT_CRITICAL(&lock);
        if(atomic_load(&diagnostic_fault))fail("latched diagnostic fault",ESP_ERR_INVALID_STATE);
        int64_t start=esp_timer_get_time();ESP_ERROR_CHECK(adc_stream_start());
        while(esp_timer_get_time()-start<1000000){
            uint32_t n=ulTaskNotifyTake(pdTRUE,pdMS_TO_TICKS(100));
            if(atomic_load(&diagnostic_fault))fail("latched diagnostic fault",ESP_ERR_INVALID_STATE);
            if(!n)fail("ADC BUSY edge timeout",ESP_ERR_TIMEOUT);
            if(n!=1)fail("ADC missed notification",ESP_ERR_INVALID_STATE);
            int32_t code[4];uint16_t status,crc;e=emg_frame(code,&status,&crc);
            if(e!=ESP_OK)fail("ADC late conversion/read",e);
            good++;for(unsigned i=0;i<EMG_CHANNEL_COUNT;i++){
                sum[i]+=code[i];sumsq[i]+=(double)code[i]*code[i];
                if(code[i]<low[i])low[i]=code[i];
                if(code[i]>high[i])high[i]=code[i];
            }
        }
        adc_stream_stop(); // UART printing is outside the acquisition window.
        if(atomic_load(&diagnostic_fault))fail("latched diagnostic fault",ESP_ERR_INVALID_STATE);
        int64_t elapsed=esp_timer_get_time()-start;
        portENTER_CRITICAL(&lock);uint32_t count=edges;portEXIT_CRITICAL(&lock);
        printf("ADC,elapsed_us=%"PRId64",edges=%"PRIu32",good=%"PRIu32,elapsed,count,good);
        for(unsigned i=0;i<EMG_CHANNEL_COUNT;i++)printf(",ch%u_mean=%.2f,min=%"PRId32",max=%"PRId32",rms_ac_codes=%.3f",i+1,(double)sum[i]/good,low[i],high[i],sqrt(fmax(0,sumsq[i]/good-pow((double)sum[i]/good,2))));
        printf("\n");
        if(AFO_DIAGNOSTIC_STAGE==6)for(unsigned i=0;i<AFO_IMU_COUNT;i++){
            int16_t axes[6];
            portENTER_CRITICAL(&lock);uint32_t irq_n=imu_edges[i]-prior_irq[i],packets=imu_packets[i]-prior_packets[i];
            for(unsigned a=0;a<6;a++)axes[a]=imu_last[i][a];
            unsigned ticks=imu_ticks[i];portEXIT_CRITICAL(&lock);
            printf("IMU,%u,packets=%"PRIu32",interrupts=%"PRIu32",ax_raw=%d,ay_raw=%d,az_raw=%d,gx_raw=%d,gy_raw=%d,gz_raw=%d,timestamp_raw=%u\n",i,packets,irq_n,axes[0],axes[1],axes[2],axes[3],axes[4],axes[5],ticks);
            if(!irq_n||!packets)fail("IMU missing interrupts/data",ESP_ERR_TIMEOUT);
        }
        printf("WINDOW_COMPLETE; codes require comparison with applied test voltages\n");
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
