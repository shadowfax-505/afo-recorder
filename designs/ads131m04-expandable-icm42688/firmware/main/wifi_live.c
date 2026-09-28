// Optional best-effort unicast telemetry. No socket work runs in acquisition tasks.
#include "wifi_live.h"
#include "board.h"
#include <string.h>
#include <stdatomic.h>
#include <fcntl.h>
#include <unistd.h>
#include "esp_wifi.h"
#include "esp_wifi_default.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "lwip/sockets.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#define META_MAX 1280
#define BATCH 16
static const char *TAG="afo_wifi";
typedef struct { uint32_t session; afo_record_t record; } item_t;
typedef struct __attribute__((packed)) {
    char magic[4]; uint8_t version,kind; uint16_t count;
    uint32_t boot,session,sequence,dropped;
    uint16_t length,reserved;
    // CRC is stored at offset 28, followed by payload at offset 32.
} prefix_t;
_Static_assert(sizeof(prefix_t)==28,"wire header prefix");
static QueueHandle_t live_queue;
static SemaphoreHandle_t meta_lock;
static atomic_bool subscribed;
static atomic_uint session_id,dropped;
static char metadata[META_MAX+1]="{\"state\":\"idle\"}";
static uint32_t boot_id,packet_seq;
static int live_socket=-1;

static void send_packet(int sock,const struct sockaddr_in *peer,uint8_t kind,
        uint32_t session,const void *payload,uint16_t length,uint16_t count) {
    uint8_t packet[32+META_MAX];
    prefix_t p={.magic={'A','F','W','1'},.version=1,.kind=kind,.count=count,
        .boot=boot_id,.session=session,.sequence=++packet_seq,.dropped=atomic_load(&dropped),.length=length};
    memcpy(packet,&p,28);memcpy(packet+28,payload,length);
    uint32_t crc=afo_crc32(packet,28+length);
    memmove(packet+32,packet+28,length);memcpy(packet+28,&crc,4);
    // Failed or blocked UDP sends are discarded; packet sequence exposes their loss.
    sendto(sock,packet,32+length,0,(const struct sockaddr*)peer,sizeof(*peer));
}
static void live_task(void *arg) {
    (void)arg;
    const int sock=live_socket;
    struct sockaddr_in peer={0};int64_t hello_at=0,meta_at=0;item_t pending;bool has_pending=false;uint32_t sent_sid=0;
    for(;;) {
        char hello[32];struct sockaddr_in source;socklen_t slen=sizeof(source);
        int n=recvfrom(sock,hello,sizeof(hello),0,(struct sockaddr*)&source,&slen);
        int64_t now=esp_timer_get_time();
        if(n==9&&!memcmp(hello,"AFO-LIVE1",9)) {
            // One laptop subscriber. Another may take over only after the lease expires.
            if(!atomic_load(&subscribed)||source.sin_addr.s_addr==peer.sin_addr.s_addr) {
                peer=source;hello_at=now;atomic_store(&subscribed,true);meta_at=0;
            }
        }
        if(now-hello_at>3000000)atomic_store(&subscribed,false);
        if(!atomic_load(&subscribed)) {has_pending=false;vTaskDelay(pdMS_TO_TICKS(20));continue;}
        if(now-meta_at>=1000000||meta_at==0||sent_sid!=atomic_load(&session_id)) {
            char copy[META_MAX+1];uint32_t sid;
            xSemaphoreTake(meta_lock,portMAX_DELAY);strcpy(copy,metadata);sid=atomic_load(&session_id);xSemaphoreGive(meta_lock);
            send_packet(sock,&peer,1,sid,copy,(uint16_t)strlen(copy),0);meta_at=now;sent_sid=sid;
        }
        item_t item;
        if(has_pending){item=pending;has_pending=false;}
        else if(xQueueReceive(live_queue,&item,pdMS_TO_TICKS(2))!=pdTRUE)continue;
        uint32_t sid=item.session; afo_record_t records[BATCH];records[0]=item.record;unsigned count=1;
        while(count<BATCH&&xQueueReceive(live_queue,&item,0)==pdTRUE) {
            if(item.session!=sid){pending=item;has_pending=true;break;}
            records[count++]=item.record;
        }
        send_packet(sock,&peer,2,sid,records,count*sizeof(afo_record_t),count);
    }
}
esp_err_t wifi_live_init(void) {
    if(!ENABLE_WIFI_LIVE)return ESP_OK;
    if(strlen(WIFI_LIVE_PASSWORD)<8||strlen(WIFI_LIVE_PASSWORD)>63||strlen(WIFI_LIVE_SSID)>32)return ESP_ERR_INVALID_ARG;
    esp_netif_t *ap=NULL;
    bool driver_ready=false,started=false,own_loop=false;
    esp_err_t err=nvs_flash_init();
    // Keep existing NVS contents intact. Shared TCP/IP/NVS services remain initialized.
    if(err!=ESP_OK)return err;
    if((err=esp_netif_init())!=ESP_OK)return err;
    err=esp_event_loop_create_default();
    if(err==ESP_OK)own_loop=true;
    else if(err!=ESP_ERR_INVALID_STATE)return err;
    ap=esp_netif_create_default_wifi_ap();
    if(!ap){err=ESP_ERR_NO_MEM;goto failed;}
    wifi_init_config_t init=WIFI_INIT_CONFIG_DEFAULT();
    if((err=esp_wifi_init(&init))!=ESP_OK)goto failed;
    driver_ready=true;
    if((err=esp_wifi_set_storage(WIFI_STORAGE_RAM))!=ESP_OK)goto failed;
    wifi_config_t cfg={0};
    memcpy(cfg.ap.ssid,WIFI_LIVE_SSID,strlen(WIFI_LIVE_SSID));cfg.ap.ssid_len=strlen(WIFI_LIVE_SSID);
    memcpy(cfg.ap.password,WIFI_LIVE_PASSWORD,strlen(WIFI_LIVE_PASSWORD));
    cfg.ap.channel=6;cfg.ap.max_connection=1;cfg.ap.authmode=WIFI_AUTH_WPA2_PSK;
    if((err=esp_wifi_set_mode(WIFI_MODE_AP))!=ESP_OK)goto failed;
    if((err=esp_wifi_set_config(WIFI_IF_AP,&cfg))!=ESP_OK)goto failed;
    if((err=esp_wifi_start())!=ESP_OK)goto failed;
    started=true;
    live_queue=xQueueCreate(64,sizeof(item_t));meta_lock=xSemaphoreCreateMutex();
    if(!live_queue||!meta_lock){err=ESP_ERR_NO_MEM;goto failed;}
    live_socket=socket(AF_INET,SOCK_DGRAM,IPPROTO_IP);
    struct sockaddr_in local={.sin_family=AF_INET,.sin_port=htons(WIFI_LIVE_PORT),.sin_addr.s_addr=htonl(INADDR_ANY)};
    if(live_socket<0||bind(live_socket,(struct sockaddr*)&local,sizeof(local))<0||fcntl(live_socket,F_SETFL,O_NONBLOCK)<0) {
        err=ESP_FAIL;goto failed;
    }
    boot_id=esp_random();
    if(xTaskCreatePinnedToCore(live_task,"wifi_live",8192,NULL,1,NULL,0)!=pdPASS){err=ESP_ERR_NO_MEM;goto failed;}
    ESP_LOGI(TAG,"Laptop AP: %s; UDP subscriber port %d; best-effort preview",WIFI_LIVE_SSID,WIFI_LIVE_PORT);
    return ESP_OK;
failed:
    // No telemetry task exists on these paths, so its resources can be released safely.
    atomic_store(&subscribed,false);
    if(live_socket>=0){close(live_socket);live_socket=-1;}
    if(live_queue){vQueueDelete(live_queue);live_queue=NULL;}
    if(meta_lock){vSemaphoreDelete(meta_lock);meta_lock=NULL;}
    if(started)esp_wifi_stop();
    if(driver_ready)esp_wifi_deinit();
    if(ap)esp_netif_destroy_default_wifi(ap);
    if(own_loop)esp_event_loop_delete_default();
    return err;
}

void wifi_live_begin(const char *json) {
    if(!live_queue||!meta_lock)return;
    if(strlen(json)>META_MAX) {ESP_LOGE(TAG,"Metadata too long; live session disabled");atomic_store(&session_id,0);return;}
    xSemaphoreTake(meta_lock,portMAX_DELAY);
    strcpy(metadata,json);uint32_t sid=esp_random();atomic_store(&session_id,sid?sid:1);
    xQueueReset(live_queue);xSemaphoreGive(meta_lock);
}
void wifi_live_offer(const afo_record_t *r) {
    if(!live_queue||!atomic_load(&subscribed))return;
    uint32_t sid=atomic_load(&session_id);if(!sid)return;
    item_t item={.session=sid,.record=*r};
    if(xQueueSend(live_queue,&item,0)!=pdTRUE)atomic_fetch_add(&dropped,1);
}
