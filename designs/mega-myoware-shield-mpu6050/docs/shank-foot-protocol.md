# Shank + foot data collection and calibration protocol

For the ESP32 standalone recorder with two MPU-6050s on one leg (IMU A on the shank, IMU B on the foot), the MyoWare EMG, and the web app's **One leg: shank + foot** gait layout. Follow it the same way every session so recordings can be compared.

## What you need

- ESP32 with firmware `esp32-stream-1.1` (gyro ±1000 °/s), charged LiPo, the web app on a laptop served from `localhost` (Wi-Fi does not work from the https copy).
- Double-sided tape (toupee or electrode tape), a 3–5 cm elastic Velcro strap, and medical tape to hold cables.
- A goniometer, a tape measure, floor tape, and a phone that can film slow motion (optional, for checking events).

## 1. Before the person arrives (5 min)

1. Flash or confirm the firmware. On the serial monitor at 115200 the boot line must read `esp32-stream-1.1 ready. imu_mask=3 (IMU A: OK, IMU B: OK)`. If either IMU is missing, fix the wiring first.
2. Mark the walkway with floor tape: a **start line** and a **stop line exactly 10 m apart**, in a straight corridor with at least 1 m free beyond each line. Measure it with the tape measure, not by tiles.
3. Connect the app over Wi-Fi, press **Stream**, and check the rate reads about 250 samples per second with 0 lost.
4. In the gait panel set **Sensor layout: One leg: shank + foot**, **Shank sensor: IMU A (0x68)**, **Leg:** the leg wearing the sensors, **Walk distance: 10**, and type the person's name.

## 2. Put the sensors on (5 min)

The app finds each sensor's axes by itself, so the exact rotation of the boards does not matter. What matters is that **they do not move on the body**.

1. **Shank sensor (IMU A, 0x68).** On the outer (lateral) side of the shank, flat on the bone, about 3–5 cm above the outer ankle bone. If the AFO shell covers that spot, put it just above the AFO's top strap on the outer shank, on skin, not on the orthosis. Tape it, then wrap the elastic strap over it.
2. **Foot sensor (IMU B, 0x69).** On top of the shoe over the midfoot (on the laces, roughly over the 2nd–3rd metatarsal bases). Not on the toes and not on the ankle crease, which bend. Tape it flat and firm; tape the cable along the shoe so it cannot tug.
3. Use the same shoes and the same AFO for every trial in a condition. Write the shoe and AFO in the recording's notes.
4. Route both cables up the outside of the leg to the ESP32 on a waist belt, with a little slack at the knee and ankle and tape every 15–20 cm. Keep each I2C cable under about 1 m.
5. Ask the person to walk a few steps and confirm in the live charts that neither sensor shows sudden spikes from knocking or slipping.

## 3. Calibration (every time the sensors are put on, 2 min)

**a. Goniometer reading.** With the person standing upright, feet hip-width and parallel, weight on both feet, in the shoes and AFO used for the trials, measure the ankle angle of the instrumented leg (fibula line against the sole of the foot; 90° = 0°, dorsiflexion positive). Type it into **Standing ankle (°)**. Leave it at 0 if you only want angles relative to standing.

**b. Quiet stand at the start of every recording.** This is the static calibration. The app uses it for both gyro offsets and for each sensor's "upright". It needs both sensors completely still for at least 1 s; ask for **5 s** to be safe. If the app shows "No moment where both sensors were still", repeat the trial.

**c. Functional calibration.** None needed beyond walking. The flexion axis of each segment comes from its own gyro during the straight walk, which needs at least 6 strides on the instrumented leg.

## 4. Practice trial and check (2 min, first session and after any wiring change)

Do one practice walk exactly as in section 5 and open the recording.

1. The shank angular-velocity chart should show one tall positive peak per stride (mid-swing) with heel-strike and toe-off marks in the dips either side. If there are no strides, or the marks look wrong, **Shank sensor** is probably set to the foot IMU: switch it to the other one.
2. **Push-off plantarflexion** should be clearly negative (typically −10° to −25° with an articulated AFO or none; close to 0° with a rigid AFO). **Swing dorsiflexion** near 0° or above means the foot clears the floor; clearly negative values mean the toes stay down in swing (drop foot).
3. **Foot angle at initial contact** positive = heel-first contact, negative = toe-first or flat-foot contact.

The angle is only computed during walking (it is reset to gravity at every foot-flat), so a standing-only or ankle-pump recording shows no ankle curve. That is expected.

## 5. Walking trials

For each trial:

1. The person stands still with both feet behind the **start line**.
2. Press **Record**. Say "stand still" and count 5 seconds.
3. Say "walk at your normal speed to the end line and stop on it". Comfortable self-selected speed, no talking, arms free, looking ahead.
4. At the stop line, stand still for 3 s.
5. Press **Record** again to stop. Name it `Name_Condition_T#`, for example `Rafi_AFO_T1`.
6. Walk back to the start **without recording** (turns are not analysed and spoil the axis estimate).

Repeat until you have **at least 5 trials per condition**. A 10 m walk is about 8–12 strides of the instrumented leg (one stride = two steps), of which the first and last, where the person speeds up and slows down, are the least typical; 5 trials give 40 or more strides, enough for stable means and stride-time variability. Rest whenever needed.

**Conditions.** If the clinician allows it, record **with AFO** and **without AFO** (same shoes), and randomise which comes first. Optionally add a **fast** speed block ("as fast as you safely can, no running").

**Once per person:** count the steps for one 10 m trial (every step, left and right) and enter it under **Measure it**, or save one recording's Eq. 4 stride length to the person. This is the fallback stride length when no distance is entered.

**Video (optional, for checking events):** film one trial side-on at the instrumented leg in slow motion, with the phone still and the whole stride in frame. Clap once in front of the camera at the start so the video and recording can be lined up. Heel strike and toe-off in the video should land within about 1–2 frames at 120 fps of the app's marks.

## 6. Check every trial before moving on (30 s)

- No warnings in the gait panel, especially no gyro or accelerometer clipping and no "no still moment".
- At least 3 strides analysed.
- Ankle values similar from trial to trial in the same condition (for example push-off within about 3°). A steady shift across trials usually means a sensor has moved: re-tape it, redo calibration step 3a and repeat the trial.
- Foot-sensor stride length within about 10 % of the Eq. 4 stride length. A bigger gap usually means the foot sensor is loose.
- Stance about 55–65 % of the stride for typical walking. Children with CP may differ, but a sudden jump between trials of the same condition points to a detection problem.

Export a **backup** and the **gait CSV** of each recording at the end of the session.

## What one leg cannot give

Step time, true double support and left/right symmetry need the other leg. The panel shows double support as an estimate, 2 × (stance % − 50), which assumes the other leg moves the same way. Do not use it for hemiplegic gait. For real bilateral values, add one IMU on the other foot or shank.

## Sources behind the method

- Carcreff L. et al., Sensors 18 (2018) 394, PMC5855531: shank events were the most robust in GMFCS II–III; the "Feet" configuration (de-drifted integration between foot-flat instants) had the lowest stride-length error in most groups; shank-only stride length was "not appropriate".
- Seel T., Raisch J., Schauer T., Sensors 14 (2014) 6891, PMC4029684: joint angles from two IMUs on adjacent segments, flexion axis from the gyros, gyro angle corrected with the accelerometer; about 1–2° RMS for the ankle.
- Mariani B. et al., J Biomech 43 (2010) 2999: foot-worn IMU stride length by de-drifted integration.
- Quiguanas-López et al., Results in Engineering 29 (2026) 109173: the original both-shanks pipeline (Eqs. 1–4).
