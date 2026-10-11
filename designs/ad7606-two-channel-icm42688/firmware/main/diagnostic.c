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
// Sums of consecutive FIFO timestamp increments, to compare sensor ticks with host time.
static uint64_t imu_tick_sum[2];
static uint32_t imu_tick_steps[2];
// Sums of valid axis samples for window means (stage 7 bench verdicts).
static int64_t imu_axis_sum[2][6];
static uint32_t imu_valid[2];
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
    (void)arg;uint8_t buf[2048];bool have_tick[2]={false,false};uint16_t previous_tick[2]={0};
    while(1){
        for(unsigned i=0;i<AFO_IMU_COUNT;i++){
            size_t packets=0;bool overflow=false;
            esp_err_t e=imu_fifo(i,buf,sizeof(buf),&packets,&overflow);
            if(e!=ESP_OK||overflow)fail("IMU FIFO/read",e!=ESP_OK?e:ESP_ERR_INVALID_SIZE);
            for(size_t k=0;k<packets;k++)if((buf[k*16]&0xfc)!=0x68)fail("IMU FIFO header",ESP_ERR_INVALID_RESPONSE);
            uint64_t step_sum=0;uint32_t steps=0;
            for(size_t k=0;k<packets;k++){
                uint16_t tick=(buf[k*16+14]<<8)|buf[k*16+15];
                if(have_tick[i]){step_sum+=(uint16_t)(tick-previous_tick[i]);steps++;}
                previous_tick[i]=tick;have_tick[i]=true;
            }
            int64_t axis_sum[6]={0};uint32_t valid=0;
            for(size_t k=0;k<packets;k++){
                const uint8_t *q=buf+k*16;bool ok=true;
                for(unsigned j=1;j<13;j+=2)if(q[j]==0x80&&q[j+1]==0)ok=false;
                if(!ok)continue;
                for(unsigned axis=0;axis<6;axis++)axis_sum[axis]+=(int16_t)((q[1+2*axis]<<8)|q[2+2*axis]);
                valid++;
            }
            portENTER_CRITICAL(&lock);imu_packets[i]+=packets;imu_tick_sum[i]+=step_sum;imu_tick_steps[i]+=steps;
            imu_valid[i]+=valid;for(unsigned axis=0;axis<6;axis++)imu_axis_sum[i][axis]+=axis_sum[axis];
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
// Stage 7: IMU carriers only (no ADC). Prints per-second windows and, after
// 60 windows, a SUMMARY with PASS/FAIL against the datasheet tolerances:
// 200 Hz +/-2% (DS-000347 Table 4: internal clock +/-1.5% at 25 C, +/-2% over
// temperature), interrupts matching packets, FIFO tick step 4687.5 +/-0.5%
// (32/30 us ticks, section 12.7), 1.0667 us per tick +/-2%,
// stationary |a| 1.00 +/-0.10 g and gyro bias under 5 deg/s per axis.
static void imu_bench(void){
    esp_err_t e=imu_bus_init(AFO_IMU_COUNT);
    if(e!=ESP_OK){printf("VERDICT,identity_and_readback,FAIL,%s (check 3.3 V, GND, JP2-JP4 at 1-2, CS/SCK/MISO/MOSI wiring)\n",esp_err_to_name(e));fail("IMU init/identity/readback",e);}
    printf("VERDICT,identity_and_readback,PASS,WHO_AM_I 0x47 and all configuration writes read back for %d sensor(s)\n",AFO_IMU_COUNT);
    ESP_ERROR_CHECK(gpio_install_isr_service(0));
    for(unsigned i=0;i<AFO_IMU_COUNT;i++){
        unsigned pin=i?SHANK_INT:FOOT_INT;
        gpio_config_t in={.pin_bit_mask=1ULL<<pin,.mode=GPIO_MODE_INPUT,.intr_type=GPIO_INTR_POSEDGE};
        ESP_ERROR_CHECK(gpio_config(&in));ESP_ERROR_CHECK(gpio_isr_handler_add(pin,imu_irq,(void *)(uintptr_t)i));
        e=imu_start(i);if(e!=ESP_OK)fail("IMU start",e);
    }
    if(xTaskCreatePinnedToCore(imu_reader,"diagnostic_imu",8192,NULL,10,NULL,0)!=pdPASS)fail("IMU task",ESP_ERR_NO_MEM);
    vTaskDelay(pdMS_TO_TICKS(200)); // let both FIFOs and interrupt streams settle
    uint32_t base_irq[2],base_packets[2],base_steps[2],base_valid[2];uint64_t base_ticks[2];int64_t base_axis[2][6];
    portENTER_CRITICAL(&lock);
    for(unsigned i=0;i<2;i++){base_irq[i]=imu_edges[i];base_packets[i]=imu_packets[i];base_steps[i]=imu_tick_steps[i];
        base_ticks[i]=imu_tick_sum[i];base_valid[i]=imu_valid[i];for(unsigned a=0;a<6;a++)base_axis[i][a]=imu_axis_sum[i][a];}
    portEXIT_CRITICAL(&lock);
    int64_t start=esp_timer_get_time();
    for(unsigned window=1;;window++){
        vTaskDelay(pdMS_TO_TICKS(1000));
        int64_t interval=esp_timer_get_time()-start;
        for(unsigned i=0;i<AFO_IMU_COUNT;i++){
            portENTER_CRITICAL(&lock);
            uint32_t irq=imu_edges[i]-base_irq[i],packets=imu_packets[i]-base_packets[i],steps=imu_tick_steps[i]-base_steps[i],valid=imu_valid[i]-base_valid[i];
            uint64_t ticks=imu_tick_sum[i]-base_ticks[i];double mean[6];
            for(unsigned a=0;a<6;a++)mean[a]=valid?(double)(imu_axis_sum[i][a]-base_axis[i][a])/valid:0;
            portEXIT_CRITICAL(&lock);
            double rate=packets*1e6/interval,step=steps?(double)ticks/steps:0,per_tick=(packets&&step>0)?interval/(packets*step):0;
            double ax=mean[0]/2048,ay=mean[1]/2048,az=mean[2]/2048,g=sqrt(ax*ax+ay*ay+az*az);
            double gx=mean[3]/16.384,gy=mean[4]/16.384,gz=mean[5]/16.384;
            printf("BENCH,%s,window=%u,elapsed_s=%.1f,rate_hz=%.2f,interrupts=%"PRIu32",packets=%"PRIu32",tick_step_mean=%.2f,host_us_per_tick=%.5f,ax_g=%.3f,ay_g=%.3f,az_g=%.3f,|a|_g=%.3f,gx_dps=%.2f,gy_dps=%.2f,gz_dps=%.2f\n",
                i?"shank":"foot",window,interval/1e6,rate,irq,packets,step,per_tick,ax,ay,az,g,gx,gy,gz);
            if(window==60){
                const char *v;
                v=fabs(rate/200-1)<=0.02?"PASS":"FAIL";printf("VERDICT,%s,rate_200Hz,%s,%.2f Hz\n",i?"shank":"foot",v,rate);
                v=(irq>packets?irq-packets:packets-irq)<=5?"PASS":"FAIL";printf("VERDICT,%s,interrupts_match_packets,%s,%"PRIu32" vs %"PRIu32"\n",i?"shank":"foot",v,irq,packets);
                v=fabs(step/4687.5-1)<=0.005?"PASS":fabs(step/5000-1)<=0.005?"FAIL (1 us ticks: set IMU_TICK_US_NUM/DEN to 1/1 in imu_timing.h)":"FAIL";
                printf("VERDICT,%s,tick_step_4687.5,%s,%.2f\n",i?"shank":"foot",v,step);
                v=fabs(per_tick/(32.0/30)-1)<=0.02?"PASS":"FAIL";printf("VERDICT,%s,host_us_per_tick_1.0667,%s,%.5f\n",i?"shank":"foot",v,per_tick);
                v=fabs(g-1)<=0.10?"PASS":"FAIL";printf("VERDICT,%s,stationary_gravity_1g,%s,%.3f g (keep the carrier still)\n",i?"shank":"foot",v,g);
                v=(fabs(gx)<5&&fabs(gy)<5&&fabs(gz)<5)?"PASS":"FAIL";printf("VERDICT,%s,gyro_bias_below_5dps,%s,%.2f/%.2f/%.2f\n",i?"shank":"foot",v,gx,gy,gz);
            }
        }
        if(window==60)printf("SUMMARY_COMPLETE; record these lines with the board photos. Rotate each carrier to check axis signs.\n");
    }
}
void app_main(void){
    gpio_config_t out={.pin_bit_mask=(1ULL<<LED_RECORD)|(1ULL<<LED_ERROR)|(1ULL<<LED_BATTERY),.mode=GPIO_MODE_OUTPUT};
    ESP_ERROR_CHECK(gpio_config(&out));
    gpio_config_t in={.pin_bit_mask=(1ULL<<BUTTON_PIN)|(1ULL<<USB_PRESENT_PIN),.mode=GPIO_MODE_INPUT,.pull_up_en=GPIO_PULLUP_ENABLE};
    ESP_ERROR_CHECK(gpio_config(&in));
    printf("BENCH ONLY; NO ELECTRODES. firmware=%s stage=%d hardware=%s channels=%d\n",AFO_FIRMWARE_ID,AFO_DIAGNOSTIC_STAGE,HARDWARE_VARIANT,EMG_CHANNEL_COUNT);
    if(AFO_DIAGNOSTIC_STAGE==2){
        unsigned tick=0;
        while(1){gpio_set_level(LED_RECORD,tick&1);gpio_set_level(LED_ERROR,(tick>>1)&1);gpio_set_level(LED_BATTERY,(tick>>2)&1);
            printf("CONTROLLER,tick=%u,button=%d,usb_attached=%d\n",tick++,!gpio_get_level(BUTTON_PIN),!gpio_get_level(USB_PRESENT_PIN));vTaskDelay(pdMS_TO_TICKS(500));}
    }
    if(AFO_DIAGNOSTIC_STAGE==7){imu_bench();}
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
        uint32_t prior_irq[2],prior_packets[2],prior_steps[2];uint64_t prior_tick_sum[2];
        // IMU counts continue during printing, so they use their own host interval.
        int64_t imu_window_start=esp_timer_get_time();
        portENTER_CRITICAL(&lock);
        for(unsigned i=0;i<2;i++){prior_irq[i]=imu_edges[i];prior_packets[i]=imu_packets[i];
            prior_steps[i]=imu_tick_steps[i];prior_tick_sum[i]=imu_tick_sum[i];}
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
            uint32_t steps=imu_tick_steps[i]-prior_steps[i];uint64_t tick_sum=imu_tick_sum[i]-prior_tick_sum[i];
            for(unsigned a=0;a<6;a++)axes[a]=imu_last[i][a];
            unsigned ticks=imu_ticks[i];portEXIT_CRITICAL(&lock);
            int64_t imu_interval=esp_timer_get_time()-imu_window_start;
            // Expected tick_step_mean is about 4687.5 at 200 Hz: ICM-42688 "1 us" ticks
            // last 32/30 us (DS-000347 section 12.7). host_us_per_tick about 1.0667.
            double step_mean=steps?(double)tick_sum/steps:0;
            double host_per_tick=(packets&&step_mean>0)?(double)imu_interval/(packets*step_mean):0;
            printf("IMU,%u,interval_us=%"PRId64",packets=%"PRIu32",interrupts=%"PRIu32",ax_raw=%d,ay_raw=%d,az_raw=%d,gx_raw=%d,gy_raw=%d,gz_raw=%d,timestamp_raw=%u,tick_steps=%"PRIu32",tick_step_mean=%.2f,host_us_per_tick=%.5f\n",
                i,imu_interval,packets,irq_n,axes[0],axes[1],axes[2],axes[3],axes[4],axes[5],ticks,steps,step_mean,host_per_tick);
            if(!irq_n||!packets)fail("IMU missing interrupts/data",ESP_ERR_TIMEOUT);
        }
        printf("WINDOW_COMPLETE; codes require comparison with applied test voltages\n");
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
