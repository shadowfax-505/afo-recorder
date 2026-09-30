#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdarg.h>
#include <sys/types.h>

typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_ERR_TIMEOUT 0x107
#define ESP_INTR_FLAG_LEVEL2 (1<<2)
#define ESP_ERROR_CHECK(e) ((void)(e))
#define ESP_LOGI(...) ((void)0)
#define ESP_LOGE(...) ((void)0)
#define ESP_LOGW(...) ((void)0)
const char *esp_err_to_name(esp_err_t e);
int64_t esp_timer_get_time(void);
uint32_t esp_random(void);

typedef struct {uint64_t pin_bit_mask;int mode,pull_up_en,intr_type;} gpio_config_t;
#define GPIO_MODE_INPUT 0
#define GPIO_MODE_OUTPUT 1
#define GPIO_INTR_POSEDGE 1
#define GPIO_INTR_NEGEDGE 2
int gpio_get_level(int pin);
esp_err_t gpio_set_level(int pin,int level);
esp_err_t gpio_config(const gpio_config_t *config);
esp_err_t gpio_intr_enable(int pin);
esp_err_t gpio_intr_disable(int pin);
esp_err_t gpio_install_isr_service(int flags);
esp_err_t gpio_isr_handler_add(int pin,void (*handler)(void *),void *arg);

typedef int BaseType_t;
typedef unsigned TickType_t;
typedef unsigned EventBits_t;
typedef struct mock_queue *QueueHandle_t;
typedef struct mock_event *EventGroupHandle_t;
typedef struct mock_task *TaskHandle_t;
typedef enum {eRunning,eReady,eBlocked,eSuspended,eDeleted} eTaskState;
typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(p) ((void)(p))
#define portEXIT_CRITICAL(p) ((void)(p))
#define portENTER_CRITICAL_ISR(p) ((void)(p))
#define portEXIT_CRITICAL_ISR(p) ((void)(p))
#define portYIELD_FROM_ISR() ((void)0)
#define pdFALSE 0
#define pdTRUE 1
#define pdPASS 1
#define portMAX_DELAY UINT32_MAX
#define pdMS_TO_TICKS(ms) (ms)
QueueHandle_t xQueueCreate(unsigned length,size_t item_size);
BaseType_t xQueueSend(QueueHandle_t q,const void *item,TickType_t wait);
BaseType_t xQueueReceive(QueueHandle_t q,void *item,TickType_t wait);
unsigned uxQueueMessagesWaiting(QueueHandle_t q);
void xQueueReset(QueueHandle_t q);
EventGroupHandle_t xEventGroupCreate(void);
EventBits_t xEventGroupSetBits(EventGroupHandle_t group,EventBits_t bits);
EventBits_t xEventGroupClearBits(EventGroupHandle_t group,EventBits_t bits);
EventBits_t xEventGroupWaitBits(EventGroupHandle_t group,EventBits_t bits,
                              BaseType_t clear,BaseType_t all,TickType_t wait);
BaseType_t xTaskCreatePinnedToCore(void (*entry)(void *),const char *name,
    unsigned stack,void *arg,unsigned priority,TaskHandle_t *out,int core);
void xTaskNotifyGive(TaskHandle_t task);
void vTaskNotifyGiveFromISR(TaskHandle_t task,BaseType_t *wake);
uint32_t ulTaskNotifyTake(BaseType_t clear,TickType_t wait);
TaskHandle_t xTaskGetCurrentTaskHandle(void);
void vTaskDelay(TickType_t ticks);
void vTaskDelete(TaskHandle_t task);
void vTaskSuspend(TaskHandle_t task);
eTaskState eTaskGetState(TaskHandle_t task);

typedef struct {int max_freq_khz;} sdmmc_host_t;
typedef struct {int width,clk,cmd,d0;} sdmmc_slot_config_t;
typedef struct {bool format_if_mount_failed;int max_files,allocation_unit_size;} esp_vfs_fat_sdmmc_mount_config_t;
typedef struct {int unused;} sdmmc_card_t;
#define SDMMC_HOST_DEFAULT() ((sdmmc_host_t){0})
#define SDMMC_SLOT_CONFIG_DEFAULT() ((sdmmc_slot_config_t){0})
#define SDMMC_FREQ_DEFAULT 20000
esp_err_t esp_vfs_fat_info(const char *mount,uint64_t *total,uint64_t *free_bytes);
esp_err_t esp_vfs_fat_sdmmc_mount(const char *mount,const sdmmc_host_t *host,
    const sdmmc_slot_config_t *slot,const esp_vfs_fat_sdmmc_mount_config_t *config,sdmmc_card_t **card);

int mock_open(const char *path,int flags,...);
ssize_t mock_write(int fd,const void *data,size_t size);
int mock_fsync(int fd);
int mock_close(int fd);
