# Understanding my muscle and motion recorder

Muttakin Rahman | AD7606, two MyoWare 2.0 sensors, two ICM-42688-P IMUs

A personal briefing for explaining the project to a supervisor. Version: 4 October 2026.

## 1. The question the instrument helps answer

An ankle-foot orthosis changes how the lower leg and foot are supported during movement. To study that interaction, I want to observe muscle activity alongside movement. My recorder measures two surface EMG channels and motion at the foot and shank. An initial placement is tibialis anterior and medial gastrocnemius, subject to the study protocol and clearance around the AFO.

This is a research acquisition platform. It does not diagnose a neurological disorder or measure nerve conduction. It can support neuromuscular research when the experiment has appropriate tasks, participants, labels, calibration and independent reference measurements.

My current achievement is a designed and virtually tested system with firmware, file decoding and staged assembly instructions. An assembled unit has not yet been measured. I should state that distinction plainly when presenting the project.

## 2. Follow one signal through the system

Muscle activity -> skin electrodes -> MyoWare RAW output -> protected, biased and buffered filter -> AD7606 -> ESP32 -> original microSD file -> computer conversion and research analysis.

The electrodes sense a voltage difference associated with activity beneath them. MyoWare amplifies and conditions that signal. RAW is already a sensor output; it is not the unamplified voltage at the skin. RECT and ENV are different outputs, and substituting either changes the meaning of the recording.

The external analog circuit provides a defined level when a sensor is unplugged and reduces higher-frequency content. It uses two buffered RC sections per channel. Buffers reduce interaction between filter sections and the ADC load. A nominal 1.5 V midpoint is a bias level, not evidence of muscle contraction.

The AD7606 converts voltages into signed integer codes. Both active muscle channels are sampled on the same conversion trigger. Although the chip has eight inputs and all eight words are read, this hardware exports exactly two muscle channels. Unused inputs are not extra measurements.

## 3. Why the voltage numbers matter

The ADC is set to +/-5 V. The code-to-voltage equation is V = code x 5 / 32768. A code of approximately 9830 represents approximately 1.5 V. The nominal conversion step is 152.588 microvolts at the ADC input.

The analog circuitry runs from approximately 3 V, so its safe input range is much narrower than the ADC's advertised bipolar range. I must not apply -5 V or +5 V to the MyoWare buffer simply because the ADC accepts those voltages. Initial synthetic testing stays within 0.1-2.9 V.

The converter's input_midpoint_mv = 0 means no reconstruction offset is subtracted when producing RAW-output volts. It does not mean the physical circuit has zero bias. Removing a baseline for analysis is a later, documented operation. Electrode-referred microvolts require a justified gain/calibration model; I cannot relabel RAW-output volts as muscle microvolts.

## 4. What the two IMUs add

Each ICM-42688-P measures acceleration on three axes and angular velocity on three axes. One module follows the foot and one follows the shank. Their fixed mounting orientation and sensor-to-segment calibration are necessary to interpret the axes anatomically.

Acceleration includes gravity. Gyroscope bias can accumulate into orientation drift. Subtracting two uncalibrated orientation estimates does not automatically produce a correct ankle angle. A reference such as validated motion capture or an appropriate instrumented angle measurement is needed to evaluate that estimate.

The two IMUs have independent clocks. Their FIFO packets preserve ordering and sensor counters. ESP32 interrupt and read times help place those samples on the recorder timeline. These host times are estimates. A difference in startup sample counts is not necessarily missing data, and matching row 100 in two CSV files does not establish simultaneity.

## 5. Sampling and timing in plain language

The target is 8,000 simultaneous EMG frames per second, one every 125 microseconds. Each IMU targets 200 samples per second, one every 5 milliseconds. These rates describe how often measurements occur; they do not by themselves describe accuracy.

The ESP32 triggers conversion, observes BUSY, reads the ADC words and attaches timing/counter information. If BUSY or a read is late, the system must report a fault instead of presenting stale data as a new muscle sample. AD7606 has no chip frame CRC: the saved record CRC protects the stored representation, not the analog event.

Filters introduce amplitude changes and delay. Independent clocks can drift. For muscle-onset versus gait-event research I need an uncertainty budget covering the analog chain, sample timing, IMU timing and the event reference. A common, measured synchronization event is stronger evidence than assuming both recordings began together.

## 6. Why SD and Wi-Fi have different jobs

microSD is the original recording path. A queue separates acquisition from storage so short write delays do not immediately stop sampling. Its capacity is finite: 2,048 records is about 0.244 seconds at nominal combined rates if the queue starts empty. Real card stalls must be tested.

Wi-Fi is a best-effort laptop preview. The laptop can miss records even when the SD file is intact. Conversely, a good-looking live graph does not prove the SD file was saved correctly. I keep and compare both original archives when testing wireless operation.

At nominal rates, 64-byte records require about 1.94 GB per hour before additional records and metadata. The firmware session limit is two hours. I use a comfortably larger card and verify free space, stop reason and file closure rather than relying only on a filename appearing.

## 7. What I can interpret after conversion

The original binary file preserves identities, counters, timestamps, metadata and integrity checks. The computer produces EMG and separate foot/shank CSV data, metadata and a quality report. I keep the binary file unchanged and hash it before analysis.

First I check: correct hardware and channel count, units, expected duration, missing counters, CRC errors, clipping, timing flags, stop reason and end-of-file recovery status. Only then do I calculate physiological features.

Possible study outputs include normalized EMG amplitude, activation timing, coactivation and segment-motion measures. Every feature needs a stated method: filter settings, window length, normalization reference, event labels and exclusions. Comparing amplitudes between sessions without controlling placement, skin contact and normalization can confuse measurement changes with physiological changes.

The research-session template links trial conditions, muscles, sensor axes, calibration and event references to the original file. Participant names and identifiable consent documents belong in the institution's protected records, not this public repository.

## 8. How I will build it without debugging everything at once

I start with inventory and module pin verification, then power rails one at a time. Next come the controller, ADC with known DC inputs, first analog channel, second channel, foot IMU, shank IMU, SD, Wi-Fi, battery and finally sensor integration under an approved protocol.

After each addition I remeasure the connected rails and rerun earlier affected diagnostics. If a new module breaks a previous test, I power down, remove that addition and restore the last accepted configuration. I keep failed logs and the repair record.

For each stage I supply readable wiring photos, exact part markings, firmware hash, applied input, measured output with units/uncertainty, raw instrument capture and the result sheet. This allows a reviewer to distinguish a wiring problem, scaling problem, timing problem and interpretation problem.

The IMU diagnostic currently runs the ADC as well, so the ADC stays connected at that stage. Diagnostic acquisition pauses for printing; uninterrupted recording is tested with the recording image. Breadboard SD CMD is GPIO47, while the custom PCB uses GPIO38: I must choose the correct build.

## 9. How the research design protects the conclusion

For an AFO comparison I define a primary outcome before collection, such as normalized TA activity during a reference-defined swing phase. I record the AFO condition, footwear, walking speed, side, task order and rest. I define acceptable signal quality and exclusions before seeing which condition appears better.

Placement and cable fixation matter because movement and AFO pressure can alter the signal. SENIAM provides anatomical placement guidance; the sensor's actual electrode geometry and any departures must be documented. Surface EMG contains contributions affected by tissue, electrode contact and nearby muscles, so two channels cannot describe every lower-leg muscle.

A neurology-related study needs the appropriate clinical collaborators, participant protocol and outcome definition. This instrument supplies observations; clinical interpretation requires more evidence than the electronics alone. It does not measure brain activity, nerve conduction velocity, force or ankle torque directly.

## 10. A short explanation for my supervisor

“I am developing a portable recorder for studying muscle activity and lower-leg movement, especially during AFO use. Two MyoWare sensors provide surface EMG, and two IMUs track foot and shank motion. An AD7606 samples the muscle channels simultaneously; an ESP32 timestamps and records the data to microSD while offering a wireless preview. I preserve raw data and quality information so analysis is reproducible. The design has software and simulation evidence, and I have organized physical validation into small stages. The next milestone is measured electrical and timing performance, followed by a properly calibrated and approved research pilot.”

If asked whether it works: explain which tests passed and which remain unmeasured. If asked what is novel: separate the instrument implementation from the research question; standard components alone do not establish novelty. If asked what the next step is: present the first unaccepted stage and its required evidence.

## Reading and evidence

- AD7606 datasheet: https://www.analog.com/media/en/technical-documentation/data-sheets/AD7606_7606-6_7606-4.pdf
- MyoWare advanced guide: https://cdn.sparkfun.com/assets/learn_tutorials/1/9/5/6/MyoWare_v2_AdvancedGuide-Updated.pdf
- Selected IMU carrier: https://www.mikroe.com/6dof-imu-14-click
- SENIAM placement and fixation: https://seniam.org/lowerleg_location.htm and https://seniam.org/fixation.htm
- Project circuit audit, integrated verification and the development stage folders provide the exact build-specific evidence and limitations.
