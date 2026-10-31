# Project credit and third-party notices

Project lead: Muttakin Rahman

This signature identifies the project lead. It does not assert ownership of manufacturer boards, datasheets, photographs, CAD models, software libraries or standard component footprints. It is not an engineering approval signature or a claim of sole manual authorship. Do not remove notices, logos, watermarks or licence terms from third-party material.

## Project-specific material

The recorder integration files, application firmware, connection tables, original explanatory drawings and build workflow are maintained for this project. There is no blanket licence grant here over embedded third-party work. PCB reference circuits and library footprints require their own provenance review; this notice is not a patent search, freedom-to-operate opinion or guarantee against infringement. Functional similarity alone does not establish that a PCB layout was copied or that it is cleared for commercial manufacture.

## Software

The browser renderer includes three.js and OrbitControls. The installed version's MIT licence and copyright notice are preserved in licenses/threejs-LICENSE.txt. No project signature replaces these credits. The bundled renderer is a compiled dependency, not wholly project-authored source.

The Mega + MyoWare web app's trained stride model (designs/mega-myoware-shield-mpu6050/web/hmm.js and web/models/roth-hmm.js) is a JavaScript port of the prediction code and the pre-trained model file (fallriskpd_at_lab_model.json) of gaitmap_mad 2.6.0, Copyright (C) 2022 MaD-Lab Erlangen (Machine Learning and Data Analytics Lab, FAU Erlangen-Nürnberg), from https://github.com/mad-lab-fau/gaitmap . gaitmap_mad is licensed under the GNU Affero General Public License v3.0 or later, so these two files are too. Their notice is in licenses/gaitmap-LICENSE.txt and the licence text in licenses/AGPL-3.0.txt. The model is from Roth et al., "Hidden Markov Model based stride segmentation on unsupervised free-living gait data in Parkinson's disease patients", J NeuroEng Rehabil 18, 93 (2021). Anyone who serves the web app to others must offer them its corresponding source; this public repository does that. The model's numbers are copied unchanged by host/tools/export_gaitmap_hmm.py; the authors did not review or endorse this port.

ESP-IDF and its bundled third-party components retain their own licences. The supplied binaries were built with the local ESP-IDF toolchain; consult its components' licences before public redistribution. Do not claim that the firmware image consists entirely of project-authored code. Python dependencies are installed separately and retain their respective terms.

## PCB symbols, footprints and models

KiCad's official libraries use CC BY-SA 4.0 with a design exception. The exception permits designs using library data without automatically requiring the whole design to adopt that licence. Redistribution of a library collection has different requirements. See https://www.kicad.org/libraries/license/ . Review any separately distributed library collection before publishing it.

The Adafruit SOT-23 adapter reference CAD is from https://github.com/adafruit/Adafruit-SMT-Breakout-PCBs . That repository's Attribution-ShareAlike 3.0 licence is retained in licenses/adafruit-breakout-license.txt. Our header maps are derived from its Eagle connectivity. Preserve Adafruit attribution and assess share-alike obligations for adaptations. This does not automatically establish the terms of other Adafruit repositories.

Adafruit microSD CAD, Pololu regulator STEP models, MIKROE module models/schematics, TI/ADI/Espressif/TDK/Microchip documents, and supplier photos remain third-party material. References and source URLs are retained in the package. A downloadable file is not proof of permission to redistribute it. Where an asset-specific licence has not been established, the provenance inventory marks redistribution as unconfirmed. These full project bundles are local engineering/reference copies, not cleared public-release packages.

Photos supplied by the project lead may contain retailer/manufacturer content and watermarks. We have not cropped or removed them to disguise their source. Do not claim the photographed commercial module as an original PCB design.

## Release boundary

Before posting a package publicly or commercially distributing it, resolve every unconfirmed asset entry, obtain permission where needed, or omit it and link to the original source. Preserve compatible licence texts and attribution. Do not delete factual validation limitations or turn simulation results into measured claims. Project signatures appear on the guide and documentation; manufacturer drawings and engineering sign-off fields are unchanged.
