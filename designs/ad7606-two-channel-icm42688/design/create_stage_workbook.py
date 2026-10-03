from pathlib import Path
import csv,json,math
P=Path(__file__).resolve().parents[1]; D=P/'development'; D.mkdir(exist_ok=True)
rows=list(csv.DictReader((P/'docs/bench-checklist.csv').open()))
stages=[
(0,'Identify the exact build','None','None','Inventory only; no power. Photograph both sides of every module, connector and jumper with readable markings. Identify the protected battery and charger separately. List instruments, calibration dates and available dummy loads.','inventory.csv; photos of all module markings and both PCB faces; instrument list','No component substitutions or unidentified module pin positions. Missing equipment becomes a specific pending test, not an assumed pass.'),
(1,'Qualify power one rail at a time','Stage 0 reviewed','None','1A: digital regulator alone. 1B: 5 V regulator alone. 1C: 3 V analog regulator fed from the accepted digital rail. 1D: midpoint buffer. Test idle first, then dummy loads. Keep ESP32, ADC, IMUs and MyoWare disconnected. Use the selected regulator modules; do not breadboard switching IC loops.','Rail DMM readings; startup and load-step scope traces; supply current/limit; dummy-load resistance and rating; temperature versus time','Measure polarity before enabling. Begin with unloaded module current limit appropriate to its documented startup requirement; log the chosen setting. If limiting occurs, disable and diagnose rather than repeatedly increasing it. No universal safe current limit is assumed.'),
(2,'Controller and controls','Stage 1 accepted','diagnostic-controller','Add controller, button, LEDs and USB sense. Connect only according to the existing exact contact table. Check 20 boots/programming cycles, then USB sense attached/absent. Do not connect both external regulation and an unqualified DevKit USB power feed.','Complete serial log; binary SHA-256; photos; 20-cycle table; GPIO21 voltage both states; rail measurements under controller load','The diagnostic intentionally allows instrumented USB operation. It does not itself prove the recording interlock; repeat the actual recording inhibition test at stage 7.'),
(3,'ADC module and two DC inputs','Stage 2 accepted','diagnostic-adc','3A: qualify module power/straps with ESP32 signal leads disconnected. 3B: add shared CVA/CVB trigger, BUSY, reset and SPI. Keep unused analog inputs at their documented levels. Apply measured 1 V/2 V DC and swap them. Do not connect analog buffers yet.','Module continuity table and strap close-ups; VIO/AVCC/reference voltages; raw logic trace with RESET, CONVST, BUSY, CS, SCLK and DOUTA; serial windows; both measured DC voltages before/after swap','AD7606 has no register identity or frame CRC. Prove identity, range and channel order using known voltages. DB7 is DOUTA in serial mode; do not infer header orientation from the chip pin numbers.'),
(4,'First analog input','Stage 3 accepted','diagnostic-adc','Build only BB1 using MCP6002 and the exact placement/contact drawing. Keep ADC V2 at a known DC level. Check local decoupling, midpoint, then 1.5 V-biased 100 mVpp at 20, 100, 500 and 1000 Hz. Keep generator output within 0.1-2.9 V including turn-on transients.','RAW1 and V1 simultaneous scope traces; amplitude/phase at each frequency; DC offset; unplugged settling; generator output settings and termination; serial mean/RMS','Measure the voltage at the breadboard, not just the generator display: a 50-ohm setting into a high-impedance load can change delivered amplitude. Do not attach electrodes.'),
(5,'Second analog input and interaction','Stage 4 accepted','diagnostic-adc','Build BB2 and repeat every BB1 test. Swap test sources to prove identities. Drive one channel while the other is held at midpoint, then reverse. Measure idle, controller-active and later Wi-Fi-active noise separately.','Both response tables; 10-minute diagnostic error log; baseline RMS/PSD with bandwidth; driven and quiet channel amplitudes; cable-layout photos','Provisional crosstalk screen is below -40 dB relative to the driven channel. A noise floor can only establish an upper bound: report that bound rather than claiming an exact crosstalk value. Research noise targets depend on the smallest effect to detect.'),
(6,'Foot IMU, then shank IMU','Stage 5 accepted; ADC remains attached','diagnostic-imu-one, then diagnostic-imu-two','6A: foot MIKROE-4237 carrier at 3.3 V, SPI jumpers verified. 6B: add shank. Test each in six static orientations and rotate one at a time. Capture separate INT1 lines. These diagnostics also run the ADC; they are not standalone IMU-only images.','WHO/readback serial results; FIFO and interrupt counts over 60 s; six-face accelerometer means; stationary gyro means; axis photographs; raw IRQ/SPI timing capture','No shared sensor clock is assumed. Counter wraps and different startup counts are normal; equal row numbers do not identify simultaneous foot/shank samples.'),
(7,'Original SD recording','Stage 6 accepted','breadboard-sd-only-2ch','7A: short known-signal recording and conversion. 7B: 60-minute continuous run. 7C: absent/full-card and five interrupted-write trials on expendable media. Test recording USB inhibition with synthetic signals only. Stop and wait for recording LED off before removing media.','Unmodified .afolog files; converter command/version; metadata, quality report and CSV excerpts; stop reason; serial log; card make/capacity/filesystem; scope trace of continuous conversion cadence','Keep damaged originals; do not overwrite them with recovered files. END is not proof of successful final filesystem sync. Check close/sync faults and counters independently. Diagnostic printing pauses cannot be used as continuous-acquisition evidence.'),
(8,'Wi-Fi while SD records','Stage 7 accepted','breadboard-record-2ch','First repeat a short baseline without a receiver, then a 60-minute SD+Wi-Fi trial. Interrupt and reconnect laptop reception. Compare common record identities, codes and timestamps; never fill missing preview data silently.','Original SD file AND laptop raw archive; receiver log/quality; disconnect times; laptop OS/software version; both converted outputs; new rail/noise captures under wireless load','A smooth dashboard is not an acceptance test. Wireless loss must be visible, while independently checking that SD did not lose records.'),
(9,'Battery and full-load regression','Stage 8 accepted','breadboard-record-2ch','Remove both lab supply leads. Check protected pack polarity before connection. Log actual runtime for at least two hours, voltage/current/temperature and low-battery events; repeat 20 starts/stops. Firmware session limit is two hours: document restart if runtime testing continues.','Timestamped battery log; pack rating/age/protection details; start/stop table; resulting original files; peak-current and voltage-dip captures using the approved no-person bench arrangement','Battery protection does not provide patient isolation. Battery warning/stop thresholds are firmware decisions, not proof that the pack protection trips correctly. Do not bypass protection or intentionally overdischarge.'),
(10,'MyoWare integration and research readiness','Stage 9 accepted; research protocol review separate','breadboard-record-2ch','10A: verify VIN/GND/RAW routing and sensor integration with no person attached. 10B: approved supervised mounting protocol with all USB, chargers and instruments removed before electrodes attach. 10C: repeated placement, synchronized reference and labeled pilot tasks.','Pseudonymous trial manifest; placement/axis diagrams; calibration files; AFO/footwear/condition labels; event/reference timestamps; original recordings and quality; protocol approval reference, not identifiable consent documents','Engineering stage completion does not authorize participants. Match sensor electrode spacing to the study and document deviations from SENIAM. AFO pressure, cable traction and movement artifact can alter EMG. Keep participant identity outside the project repository.')]
plan={'schema_version':1,'build':'ad7606-two-channel-icm42688','firmware':'ad7606-2ch-1.6','physical_status':'NOT TESTED','stages':[]}
for n,title,dep,fw,action,evidence,caution in stages:
 checks=[r for r in rows if int(r['Stage'])==n]
 entry=dict(stage=n,title=title,prerequisite=dep,firmware=fw,actions=action,evidence=evidence.split('; '),caution=caution,checks=[{'id':r['Check'],'acceptance':r['Acceptance']} for r in checks])
 plan['stages'].append(entry)
 folder=D/f'{n:02d}';folder.mkdir(exist_ok=True)
 text=f'# {n:02d} - {title}\n\n**Prerequisite:** {dep}. **Firmware:** {fw}. **Status: NOT TESTED.**\n\n[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)\n\n## Add and test\n\n{action}\n\n## Acceptance checks\n\n'
 text+='\n'.join(f"- **{r['Check']}:** {r['Acceptance']}" for r in checks) or '- Confirm the exact configuration, parts and available instruments before powering anything.'
 text+=f'\n\n## Send for review\n\n'+ '\n'.join('- '+x for x in entry['evidence'])+f'\n\n{caution}\n\n## Continuous regression\n\nBefore power: inspect the changed wiring against the contact table and photograph it. After power: remeasure every connected rail at the load, verify no unexpected heat/current, and rerun the last accepted diagnostic. Repeat earlier affected tests whenever a supply, cable, firmware or grounding connection changes. Record failures and repairs; retain the previous accepted evidence.\n\n## If the gate fails\n\nStop acquisition and remove power before changing wiring. Disconnect only the last-added module and restore the last accepted configuration. Repeat its test. If it now fails, check the shared supply/ground and changed connections before replacing components. Never change multiple modules at once to chase a fault.\n\n## Results\n\nFill measurements.csv; retain raw instrument files alongside screenshots. Outcome starts NOT TESTED. Include units, uncertainty, instrument model/settings, source voltage/load, firmware hash and filenames. Mark unmet criteria FAIL; missing evidence PENDING. Submit the whole stage folder, including failures. A completeness check is not engineering approval.\n'
 (folder/'README.md').write_text(text)
 with (folder/'measurements.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['check_id','acceptance','measured_value','unit','uncertainty','instrument_settings','evidence_file','outcome','operator','date','review_notes'])
  for r in checks:w.writerow([r['Check'],r['Acceptance'],'','','','','','NOT TESTED','','',''])
 (folder/'submission.json').write_text(json.dumps({'stage':n,'build':plan['build'],'hardware_revision':'','firmware_sha256':'','operator':'','date':'','instrument_list':[],'changes_since_last_stage':'','evidence_files':[],'review_status':'NOT REVIEWED'},indent=2)+'\n')
(D/'stage-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
(D/'00/inventory.csv').write_text('item,manufacturer,part_number,revision,quantity,photo_front,photo_back,verified_pinout_source,notes\nESP32,Espressif,ESP32-S3-DevKitC-1 N8R8,,1,,,,\nADC,RoboticsBD,RBD-3184 AD7606,,1,,,,\nFoot IMU,MikroElektronika,MIKROE-4237,,1,,,,\nShank IMU,MikroElektronika,MIKROE-4237,,1,,,,\nMyoWare,Advancer Technologies,MyoWare 2.0 bare,,2,,,,\n')
(D/'README.md').write_text('''# Build, measure, review, then add one module

**Active build: AD7606 / two RAW EMG inputs / two ICM-42688-P carriers.** Project lead: Muttakin Rahman. The other five designs remain separate; do not borrow their pin maps or firmware.

Start with **00**, even if every component has already been purchased. No assembled recorder has passed these gates yet. Simulation and software evidence remain in the existing verification reports. This sequence adds reviewable physical evidence; it does not replace the exact wiring drawings.

## Your working loop

1. Read one stage card and collect only its parts. Use the exact contact table and stage-filtered viewer, not a generic illustration.
2. Disconnect battery, lab supply and USB, and disable signal-generator outputs before changing wiring. Add the stated circuit and inspect every changed connection. Photograph the result before energizing.
3. Test that module, then rerun the prior accepted checks affected by the addition. Keep the configuration fixed while collecting evidence.
4. Fill the results sheet and send the complete stage folder. Include raw traces/logs, not only a photograph of a successful display.
5. Resolve FAIL/PENDING items. Record the accepted hardware/firmware hashes and review date before moving forward.

Do not rename existing firmware or manufacturing files. Keep a private working copy of these stage folders; use one subfolder per attempt, for example `03/attempt-001/`. Preserve failed attempts and record the repair. Never commit identifiable participant information or credentials to the public repository.

## Sequence and evidence

'''+ '\n'.join(f'- [{n:02d}: {title}]({n:02d}/README.md) - {evidence}.' for n,title,dep,fw,action,evidence,caution in stages)+'''

## Three kinds of acceptance

**Engineering screen:** the listed electrical, timing and integrity limits. Some are provisional project targets, not manufacturer guarantees.

**Research acceptance:** study-specific minimum effect, EMG noise/artifact tolerance, synchronization uncertainty, placement repeatability and reference validity. Set these before collecting the study, not after inspecting favorable results.

**Human-use authorization:** institutional protocol and electrical-safety review. Bench completion alone does not provide this.

## The minimum useful message to send me

“Stage 03, attempt 002; this is the fixed-two AD7606/ICM breadboard. Firmware SHA: … . Changed: … . Applied stimulus: … . Expected: … . Measured: … with uncertainty … . Attached: full serial log, original logic capture, module photos and measurements.csv. Earlier stage regression: … .”

For an unexpected result, keep the exact failed configuration photographed. State whether it occurs cold/warm, USB attached/absent, Wi-Fi on/off, and with the last module removed. Do not send participant identifiers.

## Start here today

Send the completed stage-00 inventory and clear front/back module photographs, plus the instruments available. If nothing has been bought, enter “not acquired” and the proposed supplier/part number. That is useful evidence; it is not a failed test.

## Companion documents

- [Logic review and open gates](logic-review.md)
- [Research planning worksheet](research-planning.md)
- [Research session manifest](research-session-template.json)
- [Personal system explanation](../docs/understanding-the-recorder.md)
- [Exact physical contact tables](../docs/build-guide.html)
- [Existing laptop setup](../docs/laptop-setup.html)

The breadboard verifies module integration. Its regulator modules, DevKit and DIP buffers differ physically from the custom PCB; repeat bring-up on the PCB and qualify layout-dependent noise, heat and radio behavior separately.
''')
manifest={'schema_version':1,'participant_code':'','session_id':'','date_time_timezone':'','protocol_approval_reference':'','operator_code':'','build':plan['build'],'hardware_revision':'','firmware_sha256':'','original_file_sha256':'','synthetic':False,'leg_side':'','condition':{'afo_model':'','afo_setting':'','footwear':'','walking_speed_method':'','task':'','trial_order':'','rest_duration_s':None},'emg_channels':[{'port':'EMG1','muscle':'tibialis anterior','placement_landmarks':'','electrode_spacing_mm':None,'sensor_serial':'','normalization_method':'','calibration_file':''},{'port':'EMG2','muscle':'medial gastrocnemius','placement_landmarks':'','electrode_spacing_mm':None,'sensor_serial':'','normalization_method':'','calibration_file':''}],'imus':[{'id':'foot','mounting_axes':'','calibration_file':''},{'id':'shank','mounting_axes':'','calibration_file':''}],'synchronization':{'reference_device':'','event_method':'','offset_us':None,'uncertainty_us':None,'drift_test_file':''},'event_labels_file':'','quality_report_file':'','exclusion_rules_set_before_collection':'','adverse_events_or_artifacts':'','review_status':'NOT REVIEWED'}
(D/'research-session-template.json').write_text(json.dumps(manifest,indent=2)+'\n')
(D/'events-template.csv').write_text('session_id,event_id,event_type,reference_time_s,recorder_time_us,uncertainty_us,label_source,reviewer,notes\n')
# Split the existing authoritative tables without inventing new endpoints.
for filename,output in [('system-wiring.csv','new-wires.csv'),('probe-connections.csv','probe-contacts.csv'),('stage-bom.csv','fixture-parts.csv')]:
 with (P/'breadboard'/filename).open() as stream:
  reader=csv.DictReader(stream);fields=reader.fieldnames;source_rows=list(reader)
 for stage in range(11):
  selected=[row for row in source_rows if int(row['Stage'])==stage]
  with (D/f'{stage:02d}'/output).open('w',newline='') as stream:
   writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(selected)
for stage in range(11):
 p=D/f'{stage:02d}'/'README.md'
 with p.open('a') as stream:stream.write('\n## Stage files\n\n- [New wires](new-wires.csv): exact endpoints copied from the existing wiring table; keep earlier accepted wires. Power-isolation and qualification instructions above override connection order within a stage.\n- [Probe contacts](probe-contacts.csv): available exact probe locations. An empty table means use the instrument instructions above.\n- [Fixture parts](fixture-parts.csv): staged discrete fixture components from the existing BOM; this is not a complete procurement list for modules, tools or consumables.\n- [Measurements](measurements.csv) and [submission metadata](submission.json).\n')
with (D/'README.md').open('a') as stream:stream.write('\n## Optional evidence check\n\nRun `python3 development/check_submission.py PATH_TO_YOUR_STAGE_FOLDER` from the variant root. It checks missing fields, listed files and hashes. A ready result means ready for human review, never hardware approval. Use Python 3.9 or newer. Record dimensionless units as `1` and explain uncertainty for categorical observations rather than leaving cells empty.\n')

with (D/'01/README.md').open('a') as stream:stream.write("\n## Dummy-load examples\n\nUse R = V / I and P = V x I. Approximate examples: 3.3 V at 300 mA needs 11 ohms and dissipates 0.99 W (use at least a 2 W resistor); 5 V at 50 mA needs 100 ohms and dissipates 0.25 W (at least 0.5 W); 3 V at 50 mA needs 60 ohms and dissipates 0.15 W (at least 0.5 W). Measure actual resistance/current, keep hot loads away from plastic, and remain within regulator ratings. Switch between load points with power off unless using a qualified electronic load. Current limit and startup capture are recorded evidence, not fixed universal settings.\n")
