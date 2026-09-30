// Executes the production recorder and serializer with deterministic API shims.
#include "shim.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

#define open mock_open
#define write mock_write
#define fsync mock_fsync
#define close mock_close
#ifndef AFO_RECORDER_SOURCE
#define AFO_RECORDER_SOURCE "../../firmware/main/main.c"
#endif
#include AFO_RECORDER_SOURCE
#undef open
#undef write
#undef fsync
#undef close
#include "../../firmware/main/format.c"

struct mock_queue {afo_record_t records[RECORD_QUEUE_LENGTH];unsigned head,count,capacity;};
struct mock_event {EventBits_t bits;};
struct mock_task {void (*entry)(void *);eTaskState state;unsigned bit;};
static struct mock_queue test_queue;
static struct mock_event test_event;
static struct mock_task tasks[2],*current_task;
static jmp_buf worker_return;
static const char *scenario;
static uint64_t clock_us=1000000;
static uint8_t disk[1024*1024],live[1024*1024];
static size_t disk_used,live_used;
static unsigned write_calls,sync_calls,close_calls,created,deleted,notified;
static unsigned imu_stops[2],free_queries;
static bool stream_started,stream_stopped,closed,interrupted,partial;
static int leds[49];
static char live_metadata[2048];
static bool is(const char *name) {return strcmp(scenario,name)==0;}

static void run_worker(struct mock_task *task) {
    if(task->state==eSuspended)return;
    assert(task->state!=eDeleted);
    current_task=task;task->state=eRunning;
    if(setjmp(worker_return)==0)task->entry(NULL);
    current_task=NULL;
}
static void synthetic_records(unsigned count) {
    uint32_t imu_seq=0;
    for(unsigned n=1;n<=count;n++) {
        const uint64_t stamp=1000000+(uint64_t)n*125;
        emg_payload_t p={.codes={6554,13107,0,0},.read_duration_us=16,
            .elapsed_slots=1,.active_mask=3,.read_start_us=stamp+4};
        afo_record_t r;afo_record_init(&r,AFO_EMG_RECORD_KIND,0,n,stamp,&p,sizeof(p));
        emg_records++;enqueue(&r);
        if(!atomic_load(&running))break;
        if(n%40==0) {
            imu_seq++;
            for(unsigned id=0;id<2;id++) {
                imu_payload_t m={.read_start_us=stamp+10,.read_end_us=stamp+40,.irq_anchor_us=stamp};
                m.fifo_packet[0]=0x68;m.fifo_packet[2]=id+1;m.fifo_packet[5]=8;
                uint16_t ts=(uint16_t)(n*125);m.fifo_packet[14]=ts>>8;m.fifo_packet[15]=ts;
                afo_record_init(&r,id?REC_SHANK:REC_FOOT,FLAG_TIMING_UNCERTAIN,imu_seq,stamp,&m,sizeof(m));
                if(id)shank_records++;else foot_records++;
                enqueue(&r);
                if(!atomic_load(&running))break;
            }
        }
    }
}

int64_t esp_timer_get_time(void) {clock_us+=100;return clock_us;}
uint32_t esp_random(void) {return 0x12345678;}
const char *esp_err_to_name(esp_err_t e) {(void)e;return "mock error";}
int gpio_get_level(int pin) {
    if(pin==USB_PRESENT_PIN)return !(is("usb-attached")|| (is("usb-during-recording")&&stream_started));
    if(pin==BUTTON_PIN)return is("card-full")||is("battery-low")?1:0;
    return 0;
}
esp_err_t gpio_set_level(int pin,int level) {leds[pin]=level;return ESP_OK;}
esp_err_t gpio_config(const gpio_config_t *c) {(void)c;return ESP_OK;}
esp_err_t gpio_intr_enable(int p) {(void)p;return ESP_OK;}
esp_err_t gpio_intr_disable(int p) {(void)p;return ESP_OK;}
esp_err_t gpio_install_isr_service(int f) {(void)f;return ESP_OK;}
esp_err_t gpio_isr_handler_add(int p,void (*h)(void *),void *a) {(void)p;(void)h;(void)a;return ESP_OK;}

QueueHandle_t xQueueCreate(unsigned length,size_t item_size) {
    assert(length<=RECORD_QUEUE_LENGTH&&item_size==sizeof(afo_record_t));
    memset(&test_queue,0,sizeof(test_queue));test_queue.capacity=length;return &test_queue;
}
BaseType_t xQueueSend(QueueHandle_t q,const void *r,TickType_t wait) {
    assert(wait==0);if(q->count==q->capacity)return pdFALSE;
    q->records[(q->head+q->count)%q->capacity]=*(const afo_record_t *)r;q->count++;return pdTRUE;
}
BaseType_t xQueueReceive(QueueHandle_t q,void *r,TickType_t wait) {
    if(!q->count){clock_us+=(uint64_t)wait*1000;return pdFALSE;}
    *(afo_record_t *)r=q->records[q->head];q->head=(q->head+1)%q->capacity;q->count--;return pdTRUE;
}
unsigned uxQueueMessagesWaiting(QueueHandle_t q) {return q->count;}
void xQueueReset(QueueHandle_t q) {q->head=q->count=0;}
EventGroupHandle_t xEventGroupCreate(void) {test_event.bits=0;return &test_event;}
EventBits_t xEventGroupSetBits(EventGroupHandle_t g,EventBits_t bits) {g->bits|=bits;return g->bits;}
EventBits_t xEventGroupClearBits(EventGroupHandle_t g,EventBits_t bits) {g->bits&=~bits;return g->bits;}
EventBits_t xEventGroupWaitBits(EventGroupHandle_t g,EventBits_t bits,BaseType_t clear,BaseType_t all,TickType_t wait) {
    (void)clear;(void)all;(void)wait;
    for(unsigned i=0;i<2;i++)if(!(g->bits&tasks[i].bit)&&tasks[i].state!=eDeleted)run_worker(&tasks[i]);
    assert((g->bits&bits)==bits);return g->bits;
}
BaseType_t xTaskCreatePinnedToCore(void (*entry)(void *),const char *name,unsigned stack,
    void *arg,unsigned priority,TaskHandle_t *out,int core) {
    (void)stack;(void)arg;(void)priority;(void)core;unsigned i=strcmp(name,"emg")==0?0:1;
    tasks[i]=(struct mock_task){.entry=entry,.state=eDeleted,.bit=1u<<i};
    if((i==0&&is("emg-task-create-failure"))||(i==1&&is("imu-task-create-failure")))return pdFALSE;
    tasks[i].state=eReady;created++;if(out)*out=&tasks[i];return pdPASS;
}
void xTaskNotifyGive(TaskHandle_t task) {
    // This assertion fails for the old self-deleting worker implementation.
    assert(task&&task->state!=eDeleted);notified++;
}
void vTaskNotifyGiveFromISR(TaskHandle_t t,BaseType_t *wake) {xTaskNotifyGive(t);*wake=pdFALSE;}
uint32_t ulTaskNotifyTake(BaseType_t clear,TickType_t wait) {(void)clear;clock_us+=(uint64_t)wait*1000;return 0;}
void vTaskDelay(TickType_t ticks) {clock_us+=(uint64_t)ticks*1000;}
void vTaskDelete(TaskHandle_t task) {
    if(!task){assert(current_task);current_task->state=eDeleted;deleted++;longjmp(worker_return,1);}
    assert(task->state==eSuspended);task->state=eDeleted;deleted++;
}
void vTaskSuspend(TaskHandle_t task) {
    assert(!task&&current_task);current_task->state=eSuspended;longjmp(worker_return,1);
}
eTaskState eTaskGetState(TaskHandle_t task) {assert(task);return task->state;}

esp_err_t sensors_init(void) {return ESP_OK;}
void adc_set_trigger_callback(bool (*callback)(void *),void *context) {(void)callback;(void)context;}
esp_err_t adc_bus_init(void) {return ESP_OK;}
esp_err_t imu_bus_init(unsigned count) {(void)count;return ESP_OK;}
TaskHandle_t xTaskGetCurrentTaskHandle(void) {return NULL;}
esp_err_t battery_init(void) {return ESP_OK;}
int battery_mv(void) {return is("battery-low")&&stream_started?3200:3800;}
esp_err_t adc_configure(void) {return ESP_OK;}
esp_err_t imu_start(unsigned id) {(void)id;return ESP_OK;}
esp_err_t imu_stop(unsigned id) {imu_stops[id]++;return id==0&&is("imu-stop-failure")?ESP_FAIL:ESP_OK;}
esp_err_t imu_fifo(unsigned id,uint8_t *data,size_t cap,size_t *packets,bool *overflow) {
    (void)id;(void)data;(void)cap;*packets=0;*overflow=false;return ESP_OK;
}
esp_err_t emg_frame(int32_t codes[4],uint16_t *status,uint16_t *crc) {
    (void)codes;(void)status;(void)crc;return ESP_FAIL;
}
uint64_t adc_sample_timestamp(void) {return clock_us;}
esp_err_t adc_stream_start(void) {
    stream_started=true;synthetic_records(is("queue-overflow")?2200:260);
    if(is("worker-fault-before-join")) {
        set_fault(STOP_TIMING);atomic_store(&running,false);run_worker(&tasks[0]);
    }
    return ESP_OK;
}
void adc_stream_stop(void) {stream_stopped=true;}
esp_err_t esp_vfs_fat_info(const char *mount,uint64_t *total,uint64_t *free_bytes) {
    (void)mount;free_queries++;*total=1024ULL*1024*1024;
    *free_bytes=is("card-full")&&stream_started?0:*total;return ESP_OK;
}
esp_err_t esp_vfs_fat_sdmmc_mount(const char *m,const sdmmc_host_t *h,const sdmmc_slot_config_t *s,
    const esp_vfs_fat_sdmmc_mount_config_t *c,sdmmc_card_t **card) {
    (void)m;(void)h;(void)s;(void)c;(void)card;return ESP_OK;
}
int mock_open(const char *path,int flags,...) {
    assert(strstr(path,"trial_12345678.afolog"));assert(flags&O_EXCL);return 3;
}
ssize_t mock_write(int fd,const void *data,size_t size) {
    assert(fd==3&&!closed);write_calls++;
    bool body=disk_used>=AFO_HEADER_BYTES;
    if(is("short-writes-eintr")&&!interrupted){interrupted=true;errno=EINTR;return -1;}
    if(is("header-write-failure")|| (body&&(is("body-write-failure")|| (is("partial-write-failure")&&partial)))){
        errno=EIO;return -1;
    }
    if(body&&is("zero-byte-write"))return 0;
    if(body&&is("partial-write-failure")){size=size<145?size:145;partial=true;}
    if(is("short-writes-eintr")&&size>333)size=333;
    assert(disk_used+size<=sizeof(disk));memcpy(disk+disk_used,data,size);disk_used+=size;return (ssize_t)size;
}
int mock_fsync(int fd) {
    assert(fd==3&&!closed);sync_calls++;
    if((is("header-sync-failure")&&sync_calls==1)||
       (is("data-sync-failure")&&sync_calls==2)||
       (is("end-sync-failure")&&sync_calls==3))return -1;
    return 0;
}
int mock_close(int fd) {assert(fd==3&&!closed);close_calls++;closed=true;return is("close-failure")?-1:0;}
esp_err_t wifi_live_init(void) {return ESP_OK;}
void wifi_live_begin(const char *json) {
    assert(strlen(json)<=1280);snprintf(live_metadata,sizeof(live_metadata),"%s",json);
}
void wifi_live_offer(const afo_record_t *r) {
    if(r->type==REC_END)assert(closed); // No premature successful wireless verdict.
    assert(live_used+sizeof(*r)<=sizeof(live));memcpy(live+live_used,r,sizeof(*r));live_used+=sizeof(*r);
}

static void save(const char *folder,const char *name,const void *data,size_t size) {
    char path[1024];snprintf(path,sizeof(path),"%s/%s",folder,name);FILE *file=fopen(path,"wb");
    assert(file&&fwrite(data,1,size,file)==size&&fclose(file)==0);
}
int main(int argc,char **argv) {
    assert(argc==3);scenario=argv[1];afo_format_init();
    tasks[0].state=tasks[1].state=eDeleted;tasks[0].bit=1;tasks[1].bit=2;
    queue=xQueueCreate(RECORD_QUEUE_LENGTH,sizeof(afo_record_t));done=xEventGroupCreate();
    record_session();
    assert(!atomic_load(&running));assert(created==deleted);
    if(stream_started){assert(stream_stopped&&closed);assert(imu_stops[0]==1&&imu_stops[1]==1);}
    unsigned expected=STOP_NORMAL;
    if(is("worker-fault-before-join"))expected=STOP_TIMING;
    if(is("queue-overflow"))expected=STOP_QUEUE;
    if(is("imu-stop-failure"))expected=STOP_SENSOR;
    if(is("usb-during-recording"))expected=STOP_USB;
    if(is("battery-low"))expected=STOP_BATTERY;
    if(strstr(scenario,"write-failure")||strstr(scenario,"sync-failure")||is("zero-byte-write")||is("close-failure")||is("card-full"))expected=STOP_STORAGE;
    if(stream_started) {
        assert(live_used>=sizeof(afo_record_t));afo_record_t end;
        memcpy(&end,live+live_used-sizeof(end),sizeof(end));assert(end.type==REC_END&&end.flags==expected);
        assert(leds[LED_RECORD]==0&&leds[LED_ERROR]==(expected!=STOP_NORMAL));
        if(is("queue-overflow"))assert(queue_dropped==1);
    } else {assert(live_used==0&&leds[LED_ERROR]==1);}
    save(argv[2],"raw-disk.afolog",disk,disk_used);save(argv[2],"live-records.bin",live,live_used);
    save(argv[2],"metadata.json",live_metadata,strlen(live_metadata));
    char report[1024];int n=snprintf(report,sizeof(report),
      "{\"scenario\":\"%s\",\"stream_started\":%s,\"reason\":%u,\"disk_bytes\":%zu,\"live_bytes\":%zu,\"tasks_created\":%u,\"tasks_deleted\":%u,\"notifications\":%u,\"writes\":%u,\"syncs\":%u,\"closes\":%u,\"metadata_bytes\":%zu}\n",
      scenario,stream_started?"true":"false",expected,disk_used,live_used,created,deleted,notified,write_calls,sync_calls,close_calls,strlen(live_metadata));
    save(argv[2],"control.json",report,(size_t)n);printf("PASS %s\n",scenario);return 0;
}
