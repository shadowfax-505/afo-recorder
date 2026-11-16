# Footswitches: checking the IMU gait events against a reference

The gait events (heel strike, toe-off) come from rules on the shank's angular
velocity that were developed on people who land on the heel. In drop foot the
foot often lands flat or toes-first, and that is where such a rule is most
likely to be wrong. Every EMG number that is timed by the gait cycle (swing
tibialis anterior amplitude, swing-phase coherence) inherits that error. So
before the IMU events are trusted on patients, they need a reference that is
recorded on the same clock.

Two force-sensing resistors (FSR) under the foot give that reference without
a motion-capture lab. The web app (ESP32 firmware 1.4, 16 Nov 2026) reads them
from two spare jacks and reports how far the IMU events are from them.
Nothing on this page has been run on hardware yet.

## What you need

- 2 force-sensing resistors, round, about 13 to 18 mm (for example Interlink
  FSR 402 or a similar part).
- 2 resistors of 10 kΩ.
- Thin flexible wire, tape or a thin insole to hold the sensors.

## Wiring (one divider per switch)

```
ESP32 3V3 ──── FSR ────┬──── signal to a spare analog input
                       │
                     10 kΩ
                       │
ESP32 GND ─────────────┘
```

Unloaded, the signal sits near 0 V; with weight on the sensor it rises towards
3.3 V. Use the signal pin of a shield jack that has no muscle sensor on it.
The jacks map to the ESP32 pins A0 = GPIO34, A1 = GPIO35, A2 = GPIO32,
A3 = GPIO33, A4 = GPIO36, A5 = GPIO39, all on ADC1, so they work with Wi-Fi on.

- Feed the divider from **3V3 only**. 5 V on an ESP32 input can damage it.
- 10 kΩ is a starting value. If the loaded level stays low (light person, soft
  shoe), try 22 kΩ or 47 kΩ; if it is already high with the foot in the air
  (the shoe squeezes the sensor), try 4.7 kΩ. The app sets its threshold from
  the range it sees, so the exact value is not critical.
- If you wire the FSR on the ground side instead, the signal falls when
  pressed. Tick **Pressing lowers the signal** in the app.

## Where the sensors go

- **Heel**: centre of the heel pad, under the calcaneus.
- **Forefoot**: under the head of the first metatarsal (the ball of the big
  toe). Under the big toe itself also works and opens a little later.

Tape them to the skin or to a thin insole, on the leg that carries the IMUs.
With an AFO, put them between the foot and the footplate for the AFO trials
and at the same spots on the bare foot or insole for the trials without it,
and note which was used. The plate spreads the load, so expect the levels to
differ between the two conditions; the app's threshold adapts to each
recording.

## In the app

1. In the gait panel, section **Footswitch check of the gait events**, choose
   the jack of the heel switch and of the forefoot switch. The app enables
   those jacks and, on firmware 1.4, tells the board to leave them unprocessed
   in every EMG mode (command `f<mask>`). They are left out of the muscle
   table.
2. Stand still for 3 s with weight on the foot, then walk. Record.
3. Open the recording. The table shows, for heel strike and toe-off: the
   number of pairs, the mean difference ± SD (IMU − footswitch, so positive
   means the IMU is late), the 95 % limits of agreement, the mean, median and
   largest absolute difference, switch events the IMU missed and IMU events
   with no switch event nearby, the same for stance and stride time, and how
   the foot landed (heel first, flat, toes first) with the heel strike
   difference for each kind.
4. **Export footswitch CSV** gives one row per stride with both sets of event
   times.

How the reference is made ([`web/footswitch.js`](../web/footswitch.js)):
a switch counts as closed when its signal is above 25 % of its own range in
that recording, with 5 % hysteresis; closures and openings shorter than 30 ms
are ignored; edge times are interpolated between samples. Contact is the first
switch to close, toe-off the last to open. Heel and forefoot within 20 ms of
each other count as a flat contact. An IMU event and a switch event are paired
when they are within 150 ms.

## What to check first (no patient needed)

1. **Static**: stand, lift the heel, lift the forefoot, lift the foot. Each
   switch should move by several hundred counts and return. If one hardly
   moves, the app says so.
2. **Slow heel-toe walk**, healthy person, 20 or more strides: all contacts
   should read "Heel first", with no missed events.
3. **Deliberate toe walking and flat-foot walking**, 20 strides each: the
   contact type should change accordingly. This is the case that matters for
   drop foot, and the heel strike difference for these contacts is the number
   to look at.
4. **Against video** (240 frames per second phone video of the foot, a visible
   LED or a stamp at the start for alignment): on about 20 contacts, compare
   the switch times with the video frames. That tells how late the FSR itself
   is.

## How to read the numbers

- A constant difference (small SD) is harmless: it can be reported and
  removed. A large SD or missed events are not.
- An FSR needs some force before it closes and only sees the spot it sits
  under, so it is a practical reference, not a force plate. Published
  comparisons usually find footswitch events within a few tens of
  milliseconds of force-plate events; that figure is from memory and has not
  been checked for this build. Step 4 above measures it for this setup.
- Report the threshold (25 % of range) and the pairing window (150 ms) with
  any agreement figures.
- With a heel switch alone there is no reference for toe-off, and with a
  forefoot switch alone heel strike is only fair for toes-first contacts. The
  app says so and leaves those columns empty.

The demo has footswitches on jacks A4 and A5 that close 15 ms before the
demo's IMU heel strike and open 25 ms after its toe-off, so the panel can be
tried without hardware. `host/tests/footswitch.test.mjs` checks the arithmetic
on signals with known offsets; it does not show how a real FSR behaves.
