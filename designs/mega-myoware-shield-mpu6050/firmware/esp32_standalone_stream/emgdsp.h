// EMG oversampling and on-board RAW processing for the ESP32 streamer.
//
// The IMU stream runs at 250 Hz, but surface EMG (MyoWare RAW output) holds
// energy up to about 450 Hz. Sampled at 250 Hz it aliases: power above 125 Hz
// folds down onto the low frequencies the envelope is made of. So the ADC
// samples every EMG channel at 2 kHz on its own timer, and each 250 Hz data
// frame carries one value that sums up the 8 samples since the last frame:
//
//   avg mode (MyoWare OUTPUT switch on ENV, default): the mean of the samples.
//     The ENV output is already smooth, so averaging only lowers ADC noise.
//   arv mode (switch on RAW): each sample goes through a 4th-order Butterworth
//     high-pass at 20 Hz (removes the 1.65 V offset and motion artefact) and
//     a 2nd-order low-pass at 450 Hz, is full-wave rectified, and the frame
//     carries the mean of the rectified samples (average rectified value,
//     ARV). The 8-sample mean has zeros at 250, 500 and 750 Hz, so what is
//     left above the frame Nyquist is tiny, and the app then low-passes the
//     ARV at 6 Hz, zero-phase, into the linear envelope.
//
// Pure C++ (no Arduino calls) so the host test can run it.
#pragma once
#include <math.h>
#include <stdint.h>

namespace emgdsp {

const uint32_t FS_HZ = 2000;
const uint32_t TICK_US = 1000000UL / FS_HZ;

enum Proc : uint8_t { PROC_AVG = 0, PROC_ARV = 1 };

struct Biquad {
  float b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0, z1 = 0, z2 = 0;
  float step(float x) {
    float y = b0 * x + z1;
    z1 = b1 * x - a1 * y + z2;
    z2 = b2 * x - a2 * y;
    return y;
  }
  // State for a constant input x with steady output y (no start-up step).
  void prime(float x, float y) {
    z2 = b2 * x - a2 * y;
    z1 = b1 * x - a1 * y + z2;
  }
};

// Bilinear-transform sections with quality factor q.
inline Biquad highpass(float fc, float fs, float q) {
  float k = tanf((float)M_PI * fc / fs), n = 1.0f / (1.0f + k / q + k * k);
  Biquad b;
  b.b0 = n; b.b1 = -2.0f * n; b.b2 = n;
  b.a1 = 2.0f * (k * k - 1.0f) * n; b.a2 = (1.0f - k / q + k * k) * n;
  return b;
}
inline Biquad lowpass(float fc, float fs, float q) {
  float k = tanf((float)M_PI * fc / fs), n = 1.0f / (1.0f + k / q + k * k);
  Biquad b;
  b.b0 = k * k * n; b.b1 = 2.0f * b.b0; b.b2 = b.b0;
  b.a1 = 2.0f * (k * k - 1.0f) * n; b.a2 = (1.0f - k / q + k * k) * n;
  return b;
}

struct Channel {
  Biquad hp1, hp2, lp;
  bool primed = false;
  float acc = 0;
  uint16_t n = 0;
  float last = 0;  // last frame value, reused if a frame comes before any sample

  void reset() {
    // 4th-order Butterworth = two sections with q = 0.5412 and 1.3066.
    hp1 = highpass(20.0f, FS_HZ, 0.5412f);
    hp2 = highpass(20.0f, FS_HZ, 1.3066f);
    lp = lowpass(450.0f, FS_HZ, 0.7071f);
    primed = false;
    acc = 0;
    n = 0;
  }

  // One ADC sample (12-bit counts).
  void add(uint16_t raw, Proc proc) {
    float x = (float)raw;
    if (proc == PROC_ARV) {
      if (!primed) {
        hp1.prime(x, 0);
        hp2.prime(0, 0);
        lp.prime(0, 0);
        primed = true;
      }
      x = fabsf(lp.step(hp2.step(hp1.step(x))));
    }
    acc += x;
    n++;
  }

  // Frame value in 12-bit counts (mean since the last call).
  float take() {
    if (n) last = acc / n;
    acc = 0;
    n = 0;
    return last;
  }
};

// Frame counts (0..1023) and the volts per 1023 counts the app should use.
// avg: 12-bit mean / 4, full scale 3.3 V. arv: 12-bit units kept (4x finer),
// full scale 3.3 * 1023 / 4095 = 0.8244 V of rectified EMG.
inline uint16_t toCounts(float v12, Proc proc) {
  float c = proc == PROC_ARV ? v12 : v12 / 4.0f;
  if (c < 0) c = 0;
  if (c > 1023) c = 1023;
  return (uint16_t)(c + 0.5f);
}
inline const char* refVolts(Proc proc) { return proc == PROC_ARV ? "0.8244" : "3.3"; }
inline const char* name(Proc proc) { return proc == PROC_ARV ? "arv" : "avg"; }

}  // namespace emgdsp
