# Build, measure, review, then add one module

**Active build: AD7606 / two RAW EMG inputs / two ICM-42688-P carriers.** Project lead: Muttakin Rahman. The other five designs remain separate; do not borrow their pin maps or firmware.

Start with **00**, even if every component has already been purchased. No assembled recorder has passed these gates yet. Simulation and software evidence remain in the existing verification reports. This sequence adds reviewable physical evidence; it does not replace the exact wiring drawings.

## Your working loop

1. Read one stage card and collect only its parts. Use the exact contact table and stage-filtered viewer, not a generic illustration.
2. Disconnect battery, lab supply and USB, and disable signal-generator outputs before changing wiring. Add the stated circuit and inspect every changed connection. Photograph the result before energizing.
3. Test that module, then rerun the prior accepted checks affected by the addition. Keep the configuration fixed while collecting evidence.
4. Fill the results sheet and send the complete stage folder. Include raw traces/logs, not only a photograph of a successful display.
5. Resolve FAIL/PENDING items. Record the accepted hardware/firmware hashes and review date before moving forward.

Do not rename existing firmware or manufacturing files. Keep a private working copy of these stage folders; use one subfolder per attempt, for example `03/attempt-001/`. Preserve failed attempts and record the repair. Never commit identifiable participant information or credentials to the public repository.

## Sequence and evidence

- [00: Identify the exact build](00/README.md) - inventory.csv; photos of all module markings and both PCB faces; instrument list.
- [01: Qualify power one rail at a time](01/README.md) - Rail DMM readings; startup and load-step scope traces; supply current/limit; dummy-load resistance and rating; temperature versus time.
- [02: Controller and controls](02/README.md) - Complete serial log; binary SHA-256; photos; 20-cycle table; GPIO21 voltage both states; usb-pu resistance; rail measurements under controller load.
- [03: ADC module and two DC inputs](03/README.md) - Module continuity table and strap close-ups; VIO/AVCC/reference voltages; raw logic trace with RESET, CONVST, BUSY, CS, SCLK and DOUTA; serial windows; both measured DC voltages before/after swap.
- [04: First analog input](04/README.md) - RAW1 and V1 simultaneous scope traces; amplitude/phase at each frequency; DC offset; unplugged settling; generator output settings and termination; serial mean/RMS.
- [05: Second analog input and interaction](05/README.md) - Both response tables; 10-minute diagnostic error log; baseline RMS/PSD with bandwidth; driven and quiet channel amplitudes; cable-layout photos.
- [06: Foot IMU, then shank IMU](06/README.md) - WHO/readback serial results; FIFO and interrupt counts over 60 s; IMU lines with interval_us, tick_step_mean and host_us_per_tick; six-face accelerometer means; stationary gyro means; axis photographs; raw IRQ/SPI timing capture.
- [07: Original SD recording](07/README.md) - Unmodified .afolog files; converter command/version; metadata, quality report and CSV excerpts; stop reason; final status queue_high_water; quality.json imu_clock; serial log; card make/model/capacity/speed class/filesystem; scope trace of continuous conversion cadence.
- [08: Wi-Fi while SD records](08/README.md) - Original SD file AND laptop raw archive; receiver log/quality; disconnect times; laptop OS/software version; both converted outputs; new rail/noise captures under wireless load.
- [09: Battery and full-load regression](09/README.md) - Timestamped battery log; pack rating/age/protection details; start/stop table; resulting original files; peak-current and voltage-dip captures using the approved no-person bench arrangement.
- [10: MyoWare integration and research readiness](10/README.md) - Pseudonymous trial manifest; placement/axis diagrams; calibration files; AFO/footwear/condition labels; event/reference timestamps; original recordings and quality; protocol approval reference, not identifiable consent documents.

## Three kinds of acceptance

**Engineering screen:** the listed electrical, timing and integrity limits. Some are provisional project targets, not manufacturer guarantees.

**Research acceptance:** study-specific minimum effect, EMG noise/artifact tolerance, synchronization uncertainty, placement repeatability and reference validity. Set these before collecting the study, not after inspecting favorable results.

**Human-use authorization:** institutional protocol and electrical-safety review. Bench completion alone does not provide this.

## The minimum useful message to send me

“Stage 03, attempt 002; this is the fixed-two AD7606/ICM breadboard. Firmware SHA: … . Changed: … . Applied stimulus: … . Expected: … . Measured: … with uncertainty … . Attached: full serial log, original logic capture, module photos and measurements.csv. Earlier stage regression: … .”

For an unexpected result, keep the exact failed configuration photographed. State whether it occurs cold/warm, USB attached/absent, Wi-Fi on/off, and with the last module removed. Do not send participant identifiers.

## Start here today

Send the completed stage-00 inventory and clear front/back module photographs, plus the instruments available. If nothing has been bought, enter “not acquired” and the proposed supplier/part number. That is useful evidence; it is not a failed test.

## Companion documents

- [Logic review and open gates](logic-review.md)
- [Research planning worksheet](research-planning.md)
- [Research session manifest](research-session-template.json)
- [Personal system explanation](../docs/understanding-the-recorder.md)
- [Exact physical contact tables](../docs/build-guide.html)
- [Existing laptop setup](../docs/laptop-setup.html)

The breadboard verifies module integration. Its regulator modules, DevKit and DIP buffers differ physically from the custom PCB; repeat bring-up on the PCB and qualify layout-dependent noise, heat and radio behavior separately.

## Optional evidence check

Run `python3 development/check_submission.py PATH_TO_YOUR_STAGE_FOLDER` from the variant root. It checks missing fields, listed files and hashes. A ready result means ready for human review, never hardware approval. Use Python 3.9 or newer. Record dimensionless units as `1` and explain uncertainty for categorical observations rather than leaving cells empty.
