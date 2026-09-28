# Build workflow review — 28 September 2026

Project lead: Muttakin Rahman

## Changes

- All six versions have a guided build: gather, connect, test and record results for each stage.
- Stage 1 is the default. A separate complete-setup preview remains available.
- Empty auxiliary boards no longer appear as selectable boards before their first step.
- Each stage lists new components, insertion holes, wires, acceptance targets and troubleshooting.
- Assembly checkboxes and measured test results are separate. Results are user-entered, stored in the browser and exportable; no physical pass is assigned automatically.
- Corrected an omitted microSD ground connection at JP1.2 in all six breadboard plans. Manufacturer Eagle CAD confirms this ground terminal. The independent wiring checker now requires all five SDIO contacts and supply/ground presence for core modules. Prior connected-net checks alone could not detect an omitted module terminal.
- Added project credit, third-party notices, source inventory and available dependency licences. No manufacturer watermarks, copyright notices or test limitations were removed. No unnecessary AI boilerplate was found in the scanned editable project text. Machine build paths and historical evidence are retained where changing them would damage provenance or binaries.

## Verification

Browser checks covered ten stages across all six versions, 3D stage links, board selection, result save/reload, JSON export and mobile rendering. Updated physical wiring checks pass. Original archived ICM packages remain unchanged. Firmware source, binaries and PCB/manufacturing circuitry were not modified; physical tests remain unperformed. No new firmware compile or PCB DRC is claimed for this interface-only and breadboard-wiring revision.

## Attribution boundary

Signature: Project lead: Muttakin Rahman. It does not replace manufacturer attribution or certify sole authorship of third-party material. Full bundles contain reference assets with unconfirmed redistribution terms; consult THIRD_PARTY_NOTICES.md and provenance.json before public release. This is a provenance review, not legal clearance or a patent search.
