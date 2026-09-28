set(AFO_DIAGNOSTIC_STAGE "0" CACHE STRING "0=recorder; 2=controller; 3=ADC; 4/5=analog; 6=IMU")
set(AFO_IMU_COUNT "2" CACHE STRING "IMUs for diagnostic stage 6")
set(AFO_HARDWARE "pcb" CACHE STRING "pcb or breadboard")
if(NOT AFO_DIAGNOSTIC_STAGE MATCHES "^(0|2|3|4|5|6)$")
 message(FATAL_ERROR "Diagnostic stage must be 0,2,3,4,5,6")
endif()
if(NOT AFO_IMU_COUNT MATCHES "^(1|2)$")
 message(FATAL_ERROR "AFO_IMU_COUNT must be 1 or 2")
endif()
if(NOT AFO_HARDWARE MATCHES "^(pcb|breadboard)$")
 message(FATAL_ERROR "Unknown hardware variant")
endif()
if(AFO_DIAGNOSTIC_STAGE STREQUAL "0")
 set(AFO_ENTRY main.c)
else()
 set(AFO_ENTRY diagnostic.c)
endif()
idf_component_register(SRCS "ads_crc.c" "adc_ads131m04.c" "adc_ad7606.c" ${AFO_ENTRY} "sensors.c" "format.c" "wifi_live.c"
    INCLUDE_DIRS "."
    REQUIRES esp_driver_gpio esp_driver_i2c esp_driver_spi esp_driver_gptimer esp_driver_sdmmc
             esp_timer esp_adc fatfs sdmmc esp_wifi esp_netif esp_event nvs_flash lwip)

if(NOT DEFINED EMG_CHANNEL_COUNT)
  set(EMG_CHANNEL_COUNT 2)
endif()
if(NOT EMG_CHANNEL_COUNT MATCHES "^(2|4)$")
  message(FATAL_ERROR "EMG_CHANNEL_COUNT must be 2 or 4")
endif()
target_compile_definitions(${COMPONENT_LIB} PRIVATE EMG_CHANNEL_COUNT=${EMG_CHANNEL_COUNT})

target_compile_definitions(${COMPONENT_LIB} PRIVATE AFO_DIAGNOSTIC_STAGE=${AFO_DIAGNOSTIC_STAGE} AFO_IMU_COUNT=${AFO_IMU_COUNT} HARDWARE_VARIANT="${AFO_HARDWARE}")

set(AFO_WIFI "1" CACHE STRING "Enable best-effort Wi-Fi in recorder")
if(NOT AFO_WIFI MATCHES "^(0|1)$")
 message(FATAL_ERROR "AFO_WIFI must be 0 or 1")
endif()
target_compile_definitions(${COMPONENT_LIB} PRIVATE ENABLE_WIFI_LIVE=${AFO_WIFI})

# DevKit V1.1 uses GPIO38 for its RGB LED. The PCB has no such load.
if(AFO_HARDWARE STREQUAL "breadboard")
 target_compile_definitions(${COMPONENT_LIB} PRIVATE AFO_BREADBOARD=1)
else()
 target_compile_definitions(${COMPONENT_LIB} PRIVATE AFO_BREADBOARD=0)
endif()
