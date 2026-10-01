// Simulator-only peripheral substitutes. Never flash this image onto a recorder.
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include "model.h"
#include "board.h"
#include "driver/spi_master.h"
#include "driver/gptimer.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"
#include "hal/adc_types.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "../../integrated-recorder/chips/stimulus.h"

static unsigned selector,adc_fault,imu_fault;
static atomic_bool gpio_levels[49],interrupt_enabled[49];
static gpio_isr_t interrupt_handler[49];
static void *interrupt_arg[49];
static uint64_t busy_until;
static unsigned conversions,converted_sequence;
static uint16_t adc_output[8];
typedef struct {uint8_t regs[128],fifo[2048];unsigned used;uint16_t ticks;uint64_t next,started;} imu_model_t;
static imu_model_t devices[2];
static portMUX_TYPE model_lock=portMUX_INITIALIZER_UNLOCKED;

// ESP-IDF calibrates its internal ADC in a constructor, even though this fixture
// replaces battery measurements. QEMU cannot perform that analog conversion.
void __wrap_adc_calc_hw_calibration_code(adc_unit_t unit,adc_atten_t atten) {(void)unit;(void)atten;}


int qemu_model_gpio_get_level(gpio_num_t pin) {
    const unsigned selectors[4]={3,14,46,48};
    for(unsigned i=0;i<4;i++)if(pin==selectors[i])return (selector>>i)&1;
    if(pin==ADC_DRDY) {
        if(adc_fault==1)return 1;
        if(adc_fault==4||adc_fault==5)return 0;
        return (uint64_t)esp_timer_get_time()<busy_until;
    }
    return pin<49?gpio_levels[pin]:0;
}

esp_err_t __real_gpio_set_level(gpio_num_t pin,uint32_t value);
esp_err_t __wrap_gpio_set_level(gpio_num_t pin,uint32_t value) {
    // Anchor the modeled edge at completion of the SDK GPIO transaction. The
    // unsupported QEMU GPIO matrix cannot deliver an external pin-change event.
    esp_err_t result=__real_gpio_set_level(pin,value);
    if(result!=ESP_OK)return result;
    if(pin<49)gpio_levels[pin]=value;
    if(pin==ADC_RESET&&value) {memset(adc_output,0,sizeof(adc_output));conversions=0;busy_until=0;}
    if(pin==ADC_CONVST&&value) {
        if(adc_fault!=5) {
            converted_sequence=conversions++;
            busy_until=esp_timer_get_time()+(adc_fault==2?250:4);
            adc_output[0]=selector==14?(uint16_t)emg_stimulus[0][converted_sequence%STIMULUS_SAMPLES]:6554;
            adc_output[1]=selector==14?(uint16_t)emg_stimulus[1][converted_sequence%STIMULUS_SAMPLES]:13107;
        }
    }
    return result;
}

esp_err_t __real_gpio_isr_handler_add(gpio_num_t pin,gpio_isr_t handler,void *arg);
esp_err_t __wrap_gpio_isr_handler_add(gpio_num_t pin,gpio_isr_t handler,void *arg) {
    assert(pin<49);interrupt_handler[pin]=handler;interrupt_arg[pin]=arg;
    return __real_gpio_isr_handler_add(pin,handler,arg);
}
esp_err_t __real_gpio_intr_enable(gpio_num_t pin);
esp_err_t __real_gpio_intr_disable(gpio_num_t pin);
esp_err_t __wrap_gpio_intr_enable(gpio_num_t pin) {assert(pin<49);interrupt_enabled[pin]=true;return __real_gpio_intr_enable(pin);}
esp_err_t __wrap_gpio_intr_disable(gpio_num_t pin) {assert(pin<49);interrupt_enabled[pin]=false;return __real_gpio_intr_disable(pin);}

static bool model_tick(gptimer_handle_t timer,const gptimer_alarm_event_data_t *event,void *arg) {
    (void)timer;(void)event;(void)arg;
    uint64_t now=esp_timer_get_time();
    for(unsigned id=0;id<2;id++) {
        unsigned produced=0;portENTER_CRITICAL_ISR(&model_lock);
        imu_model_t *m=&devices[id];
        while(m->next&&m->next<=now&&m->regs[0x16]==0x40) {
            uint8_t packet[16]={0x68,0,0,0,0,8,0};
            m->ticks+=5000;packet[2]=id+1;packet[14]=m->ticks>>8;packet[15]=m->ticks;
            if(m->used+16<=sizeof(m->fifo)){memcpy(m->fifo+m->used,packet,16);m->used+=16;}
            else m->regs[0x2d]|=2;
            m->next+=5000;produced++;
        }
        if(imu_fault==2&&id==0&&m->started&&now>m->started+500000)m->regs[0x2d]|=2;
        portEXIT_CRITICAL_ISR(&model_lock);
        unsigned pin=id?SHANK_INT:FOOT_INT;
        if(produced&&interrupt_enabled[pin]&&interrupt_handler[pin]&&!(imu_fault==3&&id==0))interrupt_handler[pin](interrupt_arg[pin]);
    }
    return false;
}

esp_err_t __wrap_spi_bus_initialize(spi_host_device_t host,const spi_bus_config_t *bus,spi_dma_chan_t dma) {
    if(host==SPI2_HOST)assert(dma==SPI_DMA_DISABLED&&bus->miso_io_num==13&&bus->mosi_io_num==-1&&bus->sclk_io_num==12);
    else assert(host==SPI3_HOST&&dma==SPI_DMA_CH_AUTO&&bus->mosi_io_num==4&&bus->miso_io_num==5&&bus->sclk_io_num==6);
    return ESP_OK;
}
esp_err_t __wrap_spi_bus_add_device(spi_host_device_t host,const spi_device_interface_config_t *cfg,spi_device_handle_t *handle) {
    if(host==SPI2_HOST){assert(cfg->mode==2&&cfg->clock_speed_hz==8000000&&cfg->spics_io_num==10);*handle=(void*)1;}
    else {assert(cfg->mode==0&&cfg->clock_speed_hz==1000000);assert(cfg->spics_io_num==7||cfg->spics_io_num==15);*handle=(void*)(uintptr_t)(cfg->spics_io_num==7?2:3);}
    return ESP_OK;
}
esp_err_t __wrap_spi_device_polling_transmit(spi_device_handle_t handle,spi_transaction_t *tx) {
    if(handle==(void*)1) {
        assert(tx->length==128);uint8_t *rx=tx->rx_buffer;assert(rx);
        for(unsigned i=0;i<8;i++){uint16_t code=adc_fault==3?0xffff:adc_output[i];rx[2*i]=code>>8;rx[2*i+1]=code;}
        esp_rom_delay_us(16);return ESP_OK;
    }
    unsigned id=(unsigned)(uintptr_t)handle-2;assert(id<2);
    const uint8_t *data=tx->flags&SPI_TRANS_USE_TXDATA?tx->tx_data:tx->tx_buffer;
    unsigned reg=data[0]&127,n=tx->length/8;assert(n<=2049);
    portENTER_CRITICAL(&model_lock);imu_model_t *m=&devices[id];
    if(data[0]&128) {
        uint8_t *rx=tx->rx_buffer;assert(rx);rx[0]=0;
        if(reg==0x30){assert(n-1<=m->used);memcpy(rx+1,m->fifo,n-1);memmove(m->fifo,m->fifo+n-1,m->used-n+1);m->used-=n-1;}
        else for(unsigned i=1;i<n;i++){unsigned r=(reg+i-1)&127;rx[i]=r==0x2e?m->used>>8:r==0x2f?m->used:m->regs[r];if(imu_fault==1&&id==1&&r==0x75)rx[i]=0;if(r==0x2d)m->regs[r]=0;}
    } else {
        assert(n==2);
        if(reg==0x11&&(data[1]&1)){memset(m,0,sizeof(*m));m->regs[0x75]=0x47;}
        else {m->regs[reg]=data[1];if(reg==0x4b&&(data[1]&2))m->used=0;if(reg==0x16){m->started=data[1]==0x40?esp_timer_get_time():0;m->next=m->started?m->started+5000:0;}}
    }
    portEXIT_CRITICAL(&model_lock);esp_rom_delay_us(n*8);return ESP_OK;
}

// QEMU has no Wi-Fi device. Only SDK radio calls are substituted; production
// packet queues, metadata, batching, sockets and lwIP loopback remain executable.
esp_netif_t *__wrap_esp_netif_create_default_wifi_ap(void) {esp_netif_config_t c=ESP_NETIF_DEFAULT_WIFI_AP();return esp_netif_new(&c);}
esp_err_t __wrap_esp_wifi_init(const wifi_init_config_t *c){assert(c);return ESP_OK;}
esp_err_t __wrap_esp_wifi_set_storage(wifi_storage_t value){assert(value==WIFI_STORAGE_RAM);return ESP_OK;}
esp_err_t __wrap_esp_wifi_set_mode(wifi_mode_t value){assert(value==WIFI_MODE_AP);return ESP_OK;}
esp_err_t __wrap_esp_wifi_set_config(wifi_interface_t iface,wifi_config_t *c){assert(iface==WIFI_IF_AP&&c->ap.authmode==WIFI_AUTH_WPA2_PSK&&c->ap.channel==6);return ESP_OK;}
esp_err_t __wrap_esp_wifi_start(void){return ESP_OK;}

void qemu_model_configure(unsigned value,unsigned adc,unsigned imu) {
    assert(value<16&&adc<=5&&imu<=3);selector=value;adc_fault=adc;imu_fault=imu;
    for(unsigned i=0;i<2;i++)devices[i].regs[0x75]=0x47;
    gptimer_handle_t timer;gptimer_config_t config={.clk_src=GPTIMER_CLK_SRC_DEFAULT,.direction=GPTIMER_COUNT_UP,.resolution_hz=1000000};
    ESP_ERROR_CHECK(gptimer_new_timer(&config,&timer));
    gptimer_event_callbacks_t callbacks={.on_alarm=model_tick};ESP_ERROR_CHECK(gptimer_register_event_callbacks(timer,&callbacks,NULL));
    gptimer_alarm_config_t alarm={.alarm_count=5000,.reload_count=0,.flags.auto_reload_on_alarm=true};
    ESP_ERROR_CHECK(gptimer_set_alarm_action(timer,&alarm));ESP_ERROR_CHECK(gptimer_enable(timer));ESP_ERROR_CHECK(gptimer_start(timer));
}

void app_main(void) {
    printf("QEMU_CONFIG_REQUEST\n");fflush(stdout);
    char line[32];unsigned length=0;int c;
    while(length+1<sizeof(line)) {c=getchar();if(c<0){clearerr(stdin);vTaskDelay(pdMS_TO_TICKS(1));continue;}if(c=='\n'||c=='\r')break;line[length++]=c;}
    line[length]=0;unsigned value,adc,imu;assert(sscanf(line,"%u %u %u",&value,&adc,&imu)==3);
    printf("QEMU_SUBSTITUTIONS,radio=SDK_stubs,SPI=behavioral_C,IMU_IRQ=timer_ISR,SDMMC=sparse_PSRAM,physical=false\n");
    qemu_model_configure(value,adc,imu);qemu_fixture_main();
}
