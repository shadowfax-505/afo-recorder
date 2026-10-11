# Website publication

Project lead: Muttakin Rahman

The project lead authorized publication of the full packages on 28 September 2026 and reported that their lawyer reviewed the redistribution terms. Original copyright notices, licences, source references and asset provenance records are retained. Earlier review-status records are historical; this publication note records the user-reported review, not an independent legal assessment.

The full detailed viewer models are included. All six complete ZIP packages are hosted as GitHub Release assets. Local caches are excluded from Git.

GitHub Pages serves the static project interface, documentation and models. ESP32 data reception still uses the local laptop receiver; GitHub Pages does not receive a nearby ESP32 radio stream. Build checklists and entered results remain in each browser's local storage.

Hardware validation remains pending. Publication does not certify the design for manufacture or human use.

## Documentation update — 29 September 2026

The public site now includes a dedicated project manual with configuration selection, architecture, staged assembly, firmware and data commands, validation evidence, safety boundaries and repository navigation. All six build, assembly and PCB views link back to the manual. The repository README and documentation index use the same evidence labels: verified in software, simulated, pending hardware and passed—measured.

## Integrated verification preview — 1 October 2026

The [v0.1.5 engineering preview](https://github.com/shadowfax-505/afo-recorder/releases/tag/v0.1.5) updates only the fixed two-channel AD7606 / ICM package. All eighteen current v1.6 integrated cases pass Wokwi web execution with complete exports and actual converter/live-decoder checks. Current laptop socket/API/browser/archive tests retain wireless losses explicitly. The unqualified QEMU timing experiment and earlier v1.5 partial/failed CLI outcomes remain visible. The other five packages retain their earlier assets. The [integrated report](../designs/ad7606-two-channel-icm42688/docs/integrated-verification.html) separates this evidence from unperformed physical validation.

Package SHA-256: `1cbb9ee3dba3b0ebd01f78c82b4ddc191e69ca6655c73b040032beb58d1b3c6e`.

## Current packages — 11 October 2026

The [v0.1.6 engineering preview](https://github.com/shadowfax-505/afo-recorder/releases/tag/v0.1.6) replaces the download links for all six packages. The fixed two-channel AD7606 / ICM package carries laboratory firmware `ad7606-2ch-1.10`: its ICM-42688-P setup matches the official TDK datasheet (DS-000347 rev 1.6) and a register-level sensor model, and two IMU-only bench builds give PASS/FAIL verdicts once real carriers are connected. The other five packages carry the ported recorder fixes (`dual-1.3` / `mpu6050-1.3`). All firmware is cross-compiled and software-tested only; the v1.6 Wokwi results are not repeated for these images, and nothing has been measured on hardware. Earlier releases remain available unchanged. SHA-256 values for the six ZIPs are listed in the release's `release-checksums.json`.
