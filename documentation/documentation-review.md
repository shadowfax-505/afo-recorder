# Documentation review — 29 September 2026

Project lead: Muttakin Rahman

## Changes

- Rewrote the repository README around purpose, configuration choice, reading order, repository structure, validation language, safety, and attribution.
- Added a project-manual index and package-specific documentation entry points.
- Added a responsive web manual covering configuration selection, architecture, all ten build gates, firmware and data commands, evidence, safety, and repository navigation.
- Added a documentation route from all 18 build, assembly, and PCB pages.
- Added contribution guidance and a project changelog.
- Preserved the separation between automated checks, simulations, pending hardware work, and user-entered measured results.

## Verification

- Checked 353 local references across the project home, web manual, and 18 viewer pages; no broken local reference was found.
- Checked links in 24 project-level and package-entry Markdown files; no broken local link was found.
- Inspected desktop and 390-pixel mobile layouts. The mobile manual has no horizontal page overflow, and its contents menu opens and closes correctly.
- Confirmed the manual is reachable from a detailed assembly view.
- Observed no browser console errors while exercising the manual and assembly-to-documentation route.
- Re-ran the physical-wiring data validator: all six variants retain zero disconnected named nets, shorts, or duplicate holes. This remains a data check; `hardware_tests` is false for every variant.

No schematic, PCB, firmware, or recording-format behavior changed in this documentation release. No new physical result is claimed.
