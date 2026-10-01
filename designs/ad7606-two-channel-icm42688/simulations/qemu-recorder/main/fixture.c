// Adapted simulation fixture; production firmware sources are included unchanged.
#include "model.h"
// Simulation fixture: production recorder, sensor drivers, FatFS and lwIP.
// Only storage media, measured battery voltage and user controls are replaced.
#define app_main recorder_entry
#include "../../../firmware/main/main.c"
#undef app_main
#include <assert.h>
#include <stdarg.h>
#include "diskio_impl.h"
#include "esp_heap_caps.h"
#include "lwip/sockets.h"
#include "mbedtls/base64.h"

enum { CASE_NORMAL=0, CASE_DELAY_WRITE=1, CASE_QUEUE_STALL=2,
       CASE_WRITE_FAIL=3, CASE_USB=4, CASE_BATTERY=5, CASE_BUSY=6,
       CASE_IMU_OVERFLOW=7, CASE_MISSING_IRQ=8, CASE_NO_SUBSCRIBER=9,
       CASE_PACKET_LOSS=10, CASE_POWER_CUT=11, CASE_MOUNT_FAIL=12,
       CASE_FULL_CARD=13, CASE_WAVEFORM=14, CASE_IMU_ABSENT=15 };
static unsigned test_case;
static atomic_int button_level=1,usb_level=1;
static atomic_bool ready,finished,peer_running=true;
static atomic_bool capture_packets=true;
static int record_fd=-1;
static char record_path[96];
static int64_t recording_at;
static unsigned write_calls,sync_calls,close_calls;
static uint8_t *packet_capture;
static size_t capture_used;
static unsigned udp_received,udp_discarded;
static bool injected;
extern volatile uint32_t adc_trace_reason;
extern volatile uint32_t adc_trace_fault_phase;
extern volatile uint64_t adc_trace_fault_at,adc_trace_read_start,adc_trace_read_end;
esp_err_t __real_emg_frame(int32_t codes[4],uint16_t *status,uint16_t *crc);
esp_err_t __wrap_emg_frame(int32_t codes[4],uint16_t *status,uint16_t *crc) {
    esp_err_t e=__real_emg_frame(codes,status,crc);
    if(e!=ESP_OK)printf("INTEGRATED_ADC_FAULT,error=%d,reason=%u,fault_at=%llu,trigger=%llu,read_start=%llu,read_end=%llu,phase=%u,irq_at=%llu,irq_phase=%u\n",
        e,(unsigned)adc_trace_reason,(unsigned long long)adc_trace_fault_at,(unsigned long long)adc_sample_timestamp(),
        (unsigned long long)adc_trace_read_start,(unsigned long long)adc_trace_read_end,(unsigned)adc_trace_fault_phase,
        (unsigned long long)emg_trace_irq_entered,(unsigned)emg_trace_irq_phase);
    return e;
}
esp_err_t __real_imu_fifo(unsigned id,uint8_t *data,size_t cap,size_t *packets,bool *overflow);
esp_err_t __wrap_imu_fifo(unsigned id,uint8_t *data,size_t cap,size_t *packets,bool *overflow) {
    esp_err_t error=__real_imu_fifo(id,data,cap,packets,overflow);
    bool bad=false;
    for(unsigned i=0;i<*packets;i++)if((data[i*16]&0xfc)!=0x68)bad=true;
    if(error!=ESP_OK||*overflow||bad)
        printf("INTEGRATED_IMU_FAULT,id=%u,error=%d,overflow=%u,packets=%u,header=%u\n",id,error,*overflow,(unsigned)*packets,*packets?data[0]:0);
    return error;
}

// Sparse 128 MiB block medium, backed by allocated PSRAM pages. It is not SDMMC.
#define SECTOR_BYTES 512U
#define PAGE_BYTES 16384U
#define DISK_BYTES (128U*1024U*1024U)
static uint8_t *pages[DISK_BYTES/PAGE_BYTES];
static unsigned pages_used,sector_reads,sector_writes;
static FATFS *mounted_fs;
static char mounted_drive[3];
static DSTATUS medium_init(BYTE drive) {(void)drive;return 0;}
static DSTATUS medium_status(BYTE drive) {(void)drive;return 0;}
static DRESULT medium_read(BYTE drive,BYTE *data,DWORD sector,UINT count) {
    (void)drive;
    if((uint64_t)sector+count>DISK_BYTES/SECTOR_BYTES)return RES_PARERR;
    sector_reads+=count;
    for(unsigned i=0;i<count;i++) {
        size_t offset=((size_t)sector+i)*SECTOR_BYTES;
        uint8_t *page=pages[offset/PAGE_BYTES];
        if(page)memcpy(data+i*SECTOR_BYTES,page+offset%PAGE_BYTES,SECTOR_BYTES);
        else memset(data+i*SECTOR_BYTES,0,SECTOR_BYTES);
    }
    return RES_OK;
}
static DRESULT medium_write(BYTE drive,const BYTE *data,DWORD sector,UINT count) {
    (void)drive;
    if((uint64_t)sector+count>DISK_BYTES/SECTOR_BYTES)return RES_PARERR;
    sector_writes+=count;
    for(unsigned i=0;i<count;i++) {
        size_t offset=((size_t)sector+i)*SECTOR_BYTES,index=offset/PAGE_BYTES;
        if(!pages[index]) {
            pages[index]=heap_caps_calloc(1,PAGE_BYTES,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
            if(!pages[index])return RES_ERROR;
            pages_used++;
        }
        memcpy(pages[index]+offset%PAGE_BYTES,data+i*SECTOR_BYTES,SECTOR_BYTES);
    }
    return RES_OK;
}
static DRESULT medium_ioctl(BYTE drive,BYTE cmd,void *buffer) {
    (void)drive;
    switch(cmd) {
      case CTRL_SYNC:return RES_OK;
      case GET_SECTOR_COUNT:*(DWORD*)buffer=DISK_BYTES/SECTOR_BYTES;return RES_OK;
      case GET_SECTOR_SIZE:*(WORD*)buffer=SECTOR_BYTES;return RES_OK;
      case GET_BLOCK_SIZE:*(DWORD*)buffer=1;return RES_OK;
      default:return RES_PARERR;
    }
}
esp_err_t __wrap_esp_vfs_fat_sdmmc_mount(const char *path,const sdmmc_host_t *host,
    const void *slot_arg,const esp_vfs_fat_mount_config_t *config,sdmmc_card_t **card) {
    const sdmmc_slot_config_t *slot=slot_arg;
    assert(host->max_freq_khz==SDMMC_FREQ_DEFAULT&&slot->width==1);
    assert(slot->clk==SD_CLK&&slot->cmd==SD_CMD&&slot->d0==SD_D0);
    assert(!config->format_if_mount_failed);
    if(test_case==CASE_MOUNT_FAIL)return ESP_FAIL;
    // Reserve hot data pages before acquisition. Allocating/zeroing a PSRAM
    // page while interrupts are running is a fixture load, not an SD transaction.
    for(unsigned i=0;i<192;i++) {
        pages[i]=heap_caps_calloc(1,PAGE_BYTES,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
        assert(pages[i]);pages_used++;
    }
    BYTE drive;ESP_ERROR_CHECK(ff_diskio_get_drive(&drive));
    const ff_diskio_impl_t disk={medium_init,medium_status,medium_read,medium_write,medium_ioctl};
    ff_diskio_register(drive,&disk);
    char name[3]={(char)('0'+drive),':',0};FATFS *fs;
    esp_vfs_fat_conf_t conf={.base_path=path,.fat_drive=name,.max_files=4};
    ESP_ERROR_CHECK(esp_vfs_fat_register_cfg(&conf,&fs));
    uint8_t *work=malloc(4096);assert(work);
    MKFS_PARM format={.fmt=FM_FAT|FM_SFD,.au_size=16384};
    FRESULT result=f_mkfs(name,&format,work,4096);free(work);
    assert(result==FR_OK);assert(f_mount(fs,name,1)==FR_OK);
    mounted_fs=fs;memcpy(mounted_drive,name,sizeof(mounted_drive));
    *card=NULL;
    // Free-card gate is also tested with a deliberately filled logical medium.
    if(test_case==CASE_FULL_CARD) {
        FIL file;assert(f_open(&file,"0:/FILL.BIN",FA_CREATE_ALWAYS|FA_WRITE)==FR_OK);
        assert(f_expand(&file,70U*1024U*1024U,1)==FR_OK);assert(f_close(&file)==FR_OK);
    }
    printf("INTEGRATED_MEDIA,FatFS_sparse_RAM,sector_bytes=%u,sdmmc_substituted=true\n",SECTOR_BYTES);
    return ESP_OK;
}
esp_err_t __wrap_battery_init(void) {return ESP_OK;}
int __wrap_battery_mv(void) {
    return test_case==CASE_BATTERY&&recording_at&&esp_timer_get_time()-recording_at>1000000?3200:3800;
}
int qemu_model_gpio_get_level(gpio_num_t pin);
int __wrap_gpio_get_level(gpio_num_t pin) {
    if(pin==BUTTON_PIN)return atomic_load(&button_level);
    if(pin==USB_PRESENT_PIN)return atomic_load(&usb_level);
    return qemu_model_gpio_get_level(pin);
}
esp_err_t __real_wifi_live_init(void);
esp_err_t __wrap_wifi_live_init(void) {
    esp_err_t result=__real_wifi_live_init();
    printf("INTEGRATED_WIFI_INIT,result=%d,udp_peer=loopback,rf_measured=false\n",result);
    assert(result==ESP_OK);atomic_store(&ready,true);return result;
}
int __real_open(const char *path,int flags,...);
int __wrap_open(const char *path,int flags,...) {
    mode_t mode=0;if(flags&O_CREAT){va_list args;va_start(args,flags);mode=va_arg(args,int);va_end(args);}
    int fd=__real_open(path,flags,mode);
    if(fd>=0&&(flags&O_WRONLY)&&strstr(path,".afolog")) {
        record_fd=fd;strncpy(record_path,path,sizeof(record_path)-1);
        atomic_store(&finished,false);write_calls=sync_calls=close_calls=0;injected=false;
    }
    return fd;
}
ssize_t __real_write(int fd,const void *data,size_t size);
ssize_t __wrap_write(int fd,const void *data,size_t size) {
    if(fd==record_fd) {
        write_calls++;
        if(write_calls==2&&!injected) {
            injected=true;
            if(test_case==CASE_DELAY_WRITE)vTaskDelay(pdMS_TO_TICKS(50));
            if(test_case==CASE_QUEUE_STALL)vTaskDelay(pdMS_TO_TICKS(350));
        }
        if(test_case==CASE_WRITE_FAIL&&write_calls==3){errno=EIO;return -1;}
    }
    return __real_write(fd,data,size);
}
int __real_fsync(int fd);
int __wrap_fsync(int fd) {
    if(fd==record_fd)sync_calls++;
    return __real_fsync(fd);
}
int __real_close(int fd);
int __wrap_close(int fd) {
    int result=__real_close(fd);
    if(fd==record_fd) {close_calls++;record_fd=-1;atomic_store(&finished,true);}
    return result;
}

// A real lwIP UDP subscriber in the same emulated MCU; not a Wi-Fi laptop link.
static void subscriber_task(void *arg) {
    (void)arg;
    while(!atomic_load(&ready))vTaskDelay(pdMS_TO_TICKS(10));
    int sock=socket(AF_INET,SOCK_DGRAM,IPPROTO_IP);assert(sock>=0);
    struct sockaddr_in local={.sin_family=AF_INET,.sin_addr.s_addr=htonl(INADDR_LOOPBACK)};
    assert(bind(sock,(struct sockaddr*)&local,sizeof(local))==0);
    assert(fcntl(sock,F_SETFL,O_NONBLOCK)==0);
    struct sockaddr_in server={.sin_family=AF_INET,.sin_port=htons(WIFI_LIVE_PORT),
        .sin_addr.s_addr=htonl(INADDR_LOOPBACK)};
    int64_t hello_at=0;
    while(atomic_load(&peer_running)) {
        int64_t now=esp_timer_get_time();
        if(test_case!=CASE_NO_SUBSCRIBER&&now-hello_at>=500000) {
            assert(sendto(sock,"AFO-LIVE1",9,0,(struct sockaddr*)&server,sizeof(server))==9);hello_at=now;
        }
        uint8_t bytes[1400];ssize_t n;
        while((n=recvfrom(sock,bytes,sizeof(bytes),0,NULL,NULL))>0) {
            assert(n>=32&&n<=1312);udp_received++;
            bool drop=test_case==CASE_PACKET_LOSS&&bytes[5]==2&&udp_received%7==0;
            if(drop){udp_discarded++;continue;}
            if(atomic_load(&capture_packets)) {
                assert(capture_used+2+n<=4U*1024U*1024U);
                packet_capture[capture_used++]=n&255;packet_capture[capture_used++]=(unsigned)n>>8;
                memcpy(packet_capture+capture_used,bytes,n);capture_used+=n;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    close(sock);vTaskDelete(NULL);
}
static void dump_bytes(const char *kind,const uint8_t *bytes,size_t size) {
    unsigned offset=0;
    while(offset<size) {
        size_t chunk=size-offset;if(chunk>768)chunk=768;
        unsigned char encoded[1028];size_t length;
        assert(mbedtls_base64_encode(encoded,sizeof(encoded),&length,bytes+offset,chunk)==0);
        encoded[length]=0;printf("EXPORT,%s,%u,%s\n",kind,offset,encoded);offset+=chunk;
        // Export happens after acquisition stops. Let the idle task run while
        // large evidence captures leave the UART; keep the watchdog enabled.
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    printf("EXPORT_END,%s,%u\n",kind,offset);
}
static void dump_file(void) {
    if(!record_path[0])return;
    // Extraction bypasses fault-injection wrappers; all recording used actual FatFS.
    int fd=__real_open(record_path,O_RDONLY);assert(fd>=0);
    struct stat info;assert(fstat(fd,&info)==0);
    unsigned char bytes[768],encoded[1028];size_t count=0,length;ssize_t n;
    while((n=read(fd,bytes,sizeof(bytes)))>0) {
        assert(mbedtls_base64_encode(encoded,sizeof(encoded),&length,bytes,n)==0);
        encoded[length]=0;printf("EXPORT,AFO,%u,%s\n",(unsigned)count,encoded);count+=n;
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    assert(count==(size_t)info.st_size);__real_close(fd);
    printf("EXPORT_END,AFO,%u\n",(unsigned)count);
}
static void test_controller(void *arg) {
    (void)arg;
    int64_t deadline=esp_timer_get_time()+10000000;
    while(!atomic_load(&ready)&&esp_timer_get_time()<deadline)vTaskDelay(pdMS_TO_TICKS(10));
    if(!atomic_load(&ready)) {
        assert(test_case==CASE_MOUNT_FAIL||test_case==CASE_IMU_ABSENT);
        assert(!record_path[0]&&!atomic_load(&running));
        printf("INTEGRATED_COMPLETE,case=%u,refused=true,hardware_measured=false\n",test_case);vTaskDelete(NULL);
    }
    vTaskDelay(pdMS_TO_TICKS(500));atomic_store(&button_level,0);vTaskDelay(pdMS_TO_TICKS(100));atomic_store(&button_level,1);
    if(test_case==CASE_FULL_CARD) {
        vTaskDelay(pdMS_TO_TICKS(300));assert(!record_path[0]&&!atomic_load(&running));
        printf("INTEGRATED_COMPLETE,case=%u,refused=true,hardware_measured=false\n",test_case);vTaskDelete(NULL);
    }
    deadline=esp_timer_get_time()+2000000;
    while(!atomic_load(&running)&&!atomic_load(&finished)&&esp_timer_get_time()<deadline)vTaskDelay(pdMS_TO_TICKS(1));
    assert(atomic_load(&running)||atomic_load(&finished));recording_at=esp_timer_get_time();
    if(test_case==CASE_USB) {vTaskDelay(pdMS_TO_TICKS(400));atomic_store(&usb_level,0);}
    else if(test_case==CASE_POWER_CUT) {
        vTaskDelay(pdMS_TO_TICKS(1100));
        // Suspend production control/workers at a deterministic failure point.
        // This represents interrupted software, not actual flash power-loss physics.
        vTaskSuspend(xTaskGetHandle("main"));
        adc_stream_stop();gpio_intr_disable(ADC_DRDY);gpio_intr_disable(FOOT_INT);gpio_intr_disable(SHANK_INT);
        if(emg_task_handle)vTaskSuspend(emg_task_handle);
        if(imu_task_handle)vTaskSuspend(imu_task_handle);
        atomic_store(&capture_packets,false);
        // Discard the in-memory FatFS state without closing/syncing the writer.
        // Reopen the directory entry from the block medium's last written state.
        assert(f_mount(NULL,mounted_drive,0)==FR_OK);
        assert(f_mount(mounted_fs,mounted_drive,1)==FR_OK);record_fd=-1;
    }
    else if(test_case==CASE_NORMAL||test_case==CASE_DELAY_WRITE||test_case==CASE_NO_SUBSCRIBER||test_case==CASE_PACKET_LOSS||test_case==CASE_WAVEFORM) {
        deadline=esp_timer_get_time()+1200000;
        while(atomic_load(&running)&&esp_timer_get_time()<deadline)vTaskDelay(pdMS_TO_TICKS(10));
        if(atomic_load(&running)) {
            atomic_store(&button_level,0);vTaskDelay(pdMS_TO_TICKS(80));atomic_store(&button_level,1);
        }
    }
    deadline=esp_timer_get_time()+6000000;
    while(test_case!=CASE_POWER_CUT&&!atomic_load(&finished)&&esp_timer_get_time()<deadline)vTaskDelay(pdMS_TO_TICKS(10));
    if(test_case!=CASE_POWER_CUT)assert(atomic_load(&finished));
    vTaskDelay(pdMS_TO_TICKS(100));atomic_store(&peer_running,false);vTaskDelay(pdMS_TO_TICKS(20));
    status_payload_t s=snapshot();
    printf("INTEGRATED_RESULT,case=%u,fault=%d,emg=%u,foot=%u,shank=%u,missed=%u,dropped=%u,imu_errors=%u,fifo_overflows=%u,adc_errors=%u,queue_peak=%u,udp=%u,discarded=%u,writes=%u,syncs=%u,closes=%u,pages=%u\n",
        test_case,atomic_load(&fault),(unsigned)s.emg_records,(unsigned)s.foot_records,(unsigned)s.shank_records,
        (unsigned)s.timer_missed,(unsigned)s.queue_dropped,(unsigned)s.imu_errors,(unsigned)s.fifo_overflows,
        (unsigned)s.adc_errors,(unsigned)s.queue_high_water,udp_received,udp_discarded,write_calls,sync_calls,close_calls,pages_used);
    dump_file();dump_bytes("UDP",packet_capture,capture_used);
    printf("INTEGRATED_COMPLETE,case=%u,hardware_measured=false\n",test_case);
    vTaskDelete(NULL);
}
void qemu_fixture_main(void) {
    // Four fixture-only case selection pins are absent from the recorder circuit.
    const unsigned pins[4]={3,14,46,48};
    gpio_config_t config={.pin_bit_mask=(1ULL<<3)|(1ULL<<14)|(1ULL<<46)|(1ULL<<48),.mode=GPIO_MODE_INPUT};
    ESP_ERROR_CHECK(gpio_config(&config));
    for(unsigned i=0;i<4;i++)test_case|=qemu_model_gpio_get_level(pins[i])<<i;
    packet_capture=heap_caps_malloc(4U*1024U*1024U,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);assert(packet_capture);
    assert(xTaskCreatePinnedToCore(test_controller,"fixture",12288,NULL,1,NULL,0)==pdPASS);
    assert(xTaskCreatePinnedToCore(subscriber_task,"subscriber",4096,NULL,2,NULL,0)==pdPASS);
    printf("INTEGRATED_BEGIN,case=%u,production_adc_imu=true,storage=FatFS_sparse_RAM,network=lwIP_loopback\n",test_case);
    recorder_entry();
}
