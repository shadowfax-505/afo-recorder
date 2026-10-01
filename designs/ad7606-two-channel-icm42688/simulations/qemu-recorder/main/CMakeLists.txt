set(RECORDER "../../../firmware/main")
idf_component_register(SRCS "fixture.c" "model.c" "${RECORDER}/adc_ad7606.c"
    "${RECORDER}/sensors.c" "${RECORDER}/format.c" "${RECORDER}/wifi_live.c"
    INCLUDE_DIRS "${RECORDER}"
    REQUIRES esp_driver_gpio esp_driver_spi esp_driver_gptimer esp_driver_sdmmc
        esp_timer esp_adc fatfs sdmmc esp_wifi esp_netif esp_event nvs_flash lwip mbedtls)
target_compile_definitions(${COMPONENT_LIB} PRIVATE AFO_BREADBOARD=1
    HARDWARE_VARIANT="breadboard" ENABLE_WIFI_LIVE=1 AFO_ADC_TRACE=1)
target_link_options(${COMPONENT_LIB} INTERFACE
    "-Wl,--wrap=adc_calc_hw_calibration_code"
    "-Wl,--wrap=esp_vfs_fat_sdmmc_mount" "-Wl,--wrap=battery_init"
    "-Wl,--wrap=battery_mv" "-Wl,--wrap=gpio_get_level"
    "-Wl,--wrap=wifi_live_init" "-Wl,--wrap=open" "-Wl,--wrap=write"
    "-Wl,--wrap=fsync" "-Wl,--wrap=close" "-Wl,--wrap=imu_fifo" "-Wl,--wrap=emg_frame")

target_link_options(${COMPONENT_LIB} INTERFACE
    "-Wl,--wrap=gpio_set_level"
    "-Wl,--wrap=gpio_isr_handler_add"
    "-Wl,--wrap=gpio_intr_enable"
    "-Wl,--wrap=gpio_intr_disable"
    "-Wl,--wrap=spi_bus_initialize"
    "-Wl,--wrap=spi_bus_add_device"
    "-Wl,--wrap=spi_device_polling_transmit"
    "-Wl,--wrap=esp_netif_create_default_wifi_ap"
    "-Wl,--wrap=esp_wifi_init"
    "-Wl,--wrap=esp_wifi_set_storage"
    "-Wl,--wrap=esp_wifi_set_mode"
    "-Wl,--wrap=esp_wifi_set_config"
    "-Wl,--wrap=esp_wifi_start"
)

