// Simulation only: real ESP-IDF FreeRTOS with production task lifecycle code.
// Peripheral entry points are stubs; this image cannot record from hardware.
#define app_main recorder_hardware_entry_not_used
#include "../../../../firmware/main/main.c"
#undef app_main
#include <assert.h>

esp_err_t sensors_init(void) {return ESP_FAIL;}
esp_err_t battery_init(void) {return ESP_FAIL;}
int battery_mv(void) {return 3800;}
esp_err_t adc_configure(void) {return ESP_FAIL;}
esp_err_t adc_stream_start(void) {return ESP_FAIL;}
void adc_stream_stop(void) {}
uint64_t adc_sample_timestamp(void) {return 0;}
esp_err_t emg_frame(int32_t codes[4],uint16_t *status,uint16_t *crc) {
    (void)codes;(void)status;(void)crc;return ESP_FAIL;
}
esp_err_t imu_start(unsigned id) {(void)id;return ESP_FAIL;}
esp_err_t imu_stop(unsigned id) {(void)id;return ESP_OK;}
esp_err_t imu_fifo(unsigned id,uint8_t *data,size_t capacity,size_t *packets,bool *overflow) {
    (void)id;(void)data;(void)capacity;*packets=0;*overflow=false;return ESP_OK;
}
esp_err_t wifi_live_init(void) {return ESP_OK;}
void wifi_live_begin(const char *json) {(void)json;}
void wifi_live_offer(const afo_record_t *record) {(void)record;}

static void create_workers(bool with_imu) {
    reset_stats();atomic_store(&running,true);
    assert(xTaskCreatePinnedToCore(emg_task,"emg",4096,NULL,22,&emg_task_handle,1)==pdPASS);
    if(with_imu)assert(xTaskCreatePinnedToCore(imu_task,"imu",12288,NULL,18,&imu_task_handle,0)==pdPASS);
    else xEventGroupSetBits(done,2);
}
void app_main(void) {
    afo_format_init();queue=xQueueCreate(RECORD_QUEUE_LENGTH,sizeof(afo_record_t));done=xEventGroupCreate();
    assert(queue&&done);
    gpio_config_t usb={.pin_bit_mask=1ULL<<USB_PRESENT_PIN,.mode=GPIO_MODE_INPUT,.pull_up_en=1};
    ESP_ERROR_CHECK(gpio_config(&usb));
    for(unsigned family=0;family<3;family++) {
        for(unsigned n=0;n<100;n++) {
            create_workers(family!=2);
            if(family==1) {
                set_fault(STOP_TIMING);
                assert((xEventGroupWaitBits(done,3,pdFALSE,pdTRUE,pdMS_TO_TICKS(100))&3)==3);
                int64_t deadline=esp_timer_get_time()+100000;
                while(eTaskGetState(emg_task_handle)!=eSuspended||eTaskGetState(imu_task_handle)!=eSuspended) {
                    assert(esp_timer_get_time()<deadline);vTaskDelay(pdMS_TO_TICKS(1));
                }
                assert(eTaskGetState(emg_task_handle)==eSuspended);
                assert(eTaskGetState(imu_task_handle)==eSuspended);
            }
            join_workers();
            assert(!emg_task_handle&&!imu_task_handle&&!atomic_load(&running));
            if(family==1)assert(atomic_load(&fault)==STOP_TIMING);
            else assert(atomic_load(&fault)==STOP_NORMAL);
        }
        printf("LIFECYCLE_PASS,family=%u,cycles=100\n",family);
    }
    printf("LIFECYCLE_COMPLETE,cases=300,hardware_measured=false\n");
}
