idf_component_register(SRCS "lifecycle.c" "../../../../firmware/main/format.c"
    INCLUDE_DIRS "../../../../firmware/main"
    REQUIRES esp_driver_gpio esp_driver_sdmmc esp_timer fatfs sdmmc)
target_compile_definitions(${COMPONENT_LIB} PRIVATE ENABLE_WIFI_LIVE=0)
