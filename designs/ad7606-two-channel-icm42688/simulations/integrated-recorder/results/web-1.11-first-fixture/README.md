# First 1.11 fixture attempts (superseded)

These runs used earlier builds of the simulation fixture; the current 1.11 matrix is in `../web-1.11/`.

- `normal`, `write-delay-50ms`, `usb-attached-during-recording` passed on fixture image `bb34b4d3…` (PSRAM budget fix, before the queue-stall change). Each folder's `tested-build.json` identifies its image. They are kept as evidence, not counted in the current matrix.
- `queue-stall-350ms-old-expectation/serial-partial.txt.gz`: the 1.6 expectation for this case was a queue-overflow stop (reason 2). On the 1.11 image the 2.44 s PSRAM queue absorbed the single 350 ms write stall:
  - result line: queue peak 2,936 of 20,480 records, 0 dropped;
  - because this case never pressed stop, the recording continued until the fixture's simulated PSRAM disk ran out of pages (174 allocated), which surfaced as a storage stop (reason 1).
  This is a fixture limit, not a firmware fault. The case now stops the recording like the nominal case and expects reason 0. Queue-overflow detection remains covered by the native recorder harness case `queue-overflow`. The transcript is partial (saved before the UDP export finished).
