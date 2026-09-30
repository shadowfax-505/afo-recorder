set(RECORDER "../../../firmware/main")
idf_component_register(SRCS "integration.c" "${RECORDER}/adc_ad7606.c"
    "${RECORDER}/sensors.c" "${RECORDER}/format.c" "${RECORDER}/wifi_live.c"
    INCLUDE_DIRS "${RECORDER}"
    REQUIRES esp_driver_gpio esp_driver_spi esp_driver_gptimer esp_driver_sdmmc
        esp_timer esp_adc fatfs sdmmc esp_wifi esp_netif esp_event nvs_flash lwip mbedtls)
target_compile_definitions(${COMPONENT_LIB} PRIVATE AFO_BREADBOARD=1
    HARDWARE_VARIANT="breadboard" ENABLE_WIFI_LIVE=1 AFO_ADC_TRACE=1)
target_link_options(${COMPONENT_LIB} INTERFACE
    "-Wl,--wrap=esp_vfs_fat_sdmmc_mount" "-Wl,--wrap=battery_init"
    "-Wl,--wrap=battery_mv" "-Wl,--wrap=gpio_get_level"
    "-Wl,--wrap=wifi_live_init" "-Wl,--wrap=open" "-Wl,--wrap=write"
    "-Wl,--wrap=fsync" "-Wl,--wrap=close" "-Wl,--wrap=imu_fifo" "-Wl,--wrap=emg_frame")
