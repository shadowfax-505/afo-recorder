/*
  AD7606 two-channel recorder - complete system
  Project lead: Muttakin Rahman

  The complete scene is saved in this project. The recorder is an ESP-IDF
  application, not this placeholder Arduino sketch.

  1. Download and extract the Wokwi bundle:
     https://shadowfax-505.github.io/afo-recorder/designs/ad7606-two-channel-icm42688/docs/whole-system.html
  2. Focus this editor and press F1.
  3. Choose "Upload Firmware and Start Simulation...".
  4. Select integrated-recorder/firmware/merged.bin from the bundle.
  5. Boot must identify ESP-IDF v5.4.2 and ELF SHA prefix aabb34031.
  6. Simulation menu: Full screen, then Fit.

  Expected: INTEGRATED_COMPLETE,case=0 and both EXPORT_END markers.
  Re-upload the custom image after reopening the project.

  ADC and IMU digital models execute the protocol. Other green context
  blocks illustrate power, analog inputs, SDMMC and laptop connections.
  RAM storage and UDP loopback substitute physical SD and Wi-Fi transport.
  This is simulation evidence. No assembled recorder has been measured.
*/
