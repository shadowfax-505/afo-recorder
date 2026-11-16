# Raw 2 kHz EMG and coherence: bench checks before any walking data

ESP32 firmware 1.3 can stream every 2 kHz ADC sample, unprocessed, next to the
250 Hz frames. The web app records it, exports it and computes coherence
between two channels. Coherence between two sites on the tibialis anterior
(15–55 Hz, swing phase) is the planned neural outcome of the AFO study, so
this page lists what has to be true of the hardware before a coherence number
means anything. None of these checks has been run yet.

Coherence only says that two signals share a rhythm. Four things other than
common drive from the brain produce it: cross-talk between the electrode
pairs, mains hum picked up by both, noise shared through the ADC reference or
the supply, and a common movement artefact. The checks below are ordered so
that each one rules out one of them.

## How to record raw EMG

1. Flash `firmware/esp32_standalone_stream` (1.3 or later). Set each MyoWare **OUTPUT**
   switch to **RAW**. Power the shield from the ESP32 **3V3** pin, so the
   resting level sits near 1.65 V, inside the ADC's usable range.
2. Connect over **Wi-Fi**. USB at 115200 baud is too slow for the raw stream.
3. Switch on the EMG jacks in use, then tick **Raw 2 kHz EMG**. The line next
   to it shows samples per second (should read about 2000) and samples lost.
4. Record. The recording page then shows **Raw EMG CSV** and the coherence
   panel. "Whole recording" suits the bench checks; "Swing" needs gait events.

The board's status page (`http://afo-mega.local/`) and the `status` command on
USB show ADC ticks, late ticks, the longest tick and ring overruns.

## Check 0: is the signal really RAW?

Scope the shield jack tip (or record raw and look at the Raw EMG CSV). RAW is
a signal that swings both ways around about half the supply and looks like
noise bursts during a contraction. ENV is a slow positive hump from near 0 V.
If the jack carries ENV, coherence is impossible: the sensor's 3.6 Hz
envelope filter has already removed the 15–55 Hz content.

Pass: resting level 1.4–1.9 V (about 1740–2360 counts), bursts symmetric
around it.

## Check 1: does 2 kHz hold with Wi-Fi on?

Enable the channels you will use (two first, then six), tick Raw 2 kHz EMG,
stream for 5 minutes with the app connected.

Pass: about 2000 samples per second, lost samples under 0.1 %, late ticks
under 0.1 % of ticks, no ring overruns. If six channels fail and two pass,
record two (the TA pair) and say so in the methods.

## Check 2: noise floor

Short the electrode inputs of each sensor (snap the three electrode studs
together with a wire or a wet gauze pad), or put the electrodes on a relaxed
muscle. Record 60 s, "Whole recording".

Read "Signal size after filtering" in the panel. Input-referred noise in
microvolts = counts × 3300 / 4095 / 200 × 1000 (gain 200 on RAW, from the
MyoWare guide). Research systems are near 1–5 µV RMS. Write the number down;
it sets the smallest EMG you can report.

## Check 3: do the electronics alone make coherence?

Same recording as check 2, two sensors, inputs shorted, Wi-Fi on.

Pass: mean 15–55 Hz coherence not above the chance limit, bins above the
limit close to the number expected by chance, no peak at 0 ms in the lag
plot. A peak at mains (50 Hz) means hum reaches both channels: move away from
mains cables, run on battery only, keep sensor leads short and twisted.

If this fails with shorted inputs, the shared path is the supply or the ADC.
Coherence on this board is then not usable, and the external ADC designs in
this repository are the next step.

## Check 4: two people

One sensor on person A's tibialis anterior, the other on person B's, both
walking or both holding dorsiflexion. Their nervous systems share nothing, so
any coherence is electrical or mechanical.

Pass: as check 3.

## Check 5: cross-talk on one muscle

Both sensors on one tibialis anterior, at least 10 cm apart along the muscle.
Hold a steady, light dorsiflexion for 60 s.

Expect, if the measure works: coherence above the limit somewhere in
15–35 Hz, not at all frequencies, with a lag-plot peak a few ms wide.
Cross-talk looks different: coherence at nearly all frequencies up to
several hundred Hz and a needle-sharp peak at exactly 0 ms. If you see that,
move the sensors further apart and repeat.

## Check 6: movement artefact

Walk with both sensors on the shin over bone (no muscle underneath) or on a
relaxed muscle with the cables taped as for a real trial. Analyse "Whole
strides".

Pass: as check 3. Stride-locked cable swing shows as coherence at the lowest
frequencies; the 20 Hz high-pass should remove it.

## What the panel computes

Each channel is high-pass filtered at 20 Hz (zero phase), rectified, cut into
256 ms segments inside the chosen windows, tapered and transformed. Coherence
is |Sxy|² / (Sxx · Syy) from the averaged spectra. The 95 % chance limit is
1 − 0.05^(1/(L−1)) for L segments. Segments with a lost sample are dropped.
Bins within two bins of the mains frequency are left out of the band summary
unless you choose "Keep all bins". The channels are read one after another by
the ESP32's ADC, a few tens of microseconds apart; that shifts phase a
little and does not change coherence magnitude.

Aim for 100 or more segments: about 100 strides for swing, since a swing
phase holds one 256 ms segment. The reference study (Zipser-Mohammadzada et al.
2023) used 3-minute walks, two sites at least 10 cm apart, 2 kHz sampling and
the 15–55 Hz band.
