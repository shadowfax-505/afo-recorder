#!/usr/bin/env python3
"""Audit existing integrated captures; this command performs no new MCU run."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics
import struct

P = Path(__file__).resolve().parent


def distribution(values):
    return {"min": min(values), "median": statistics.median(values), "max": max(values)} if values else None


def rate(times):
    return (len(times) - 1) * 1e6 / (times[-1] - times[0]) if len(times) > 1 and times[-1] > times[0] else None


def emg_timing(rows):
    errors = []
    times = [int(r["conversion_trigger_host_us"]) for r in rows]
    intervals = [b - a for a, b in zip(times, times[1:])]
    delays = [int(r["read_start_us"]) - t for r, t in zip(rows, times)]
    durations = [int(r["read_duration_us"]) for r in rows]
    slack = [times[i + 1] - int(r["read_start_us"]) - int(r["read_duration_us"]) for i, r in enumerate(rows[:-1])]
    if any(x <= 0 for x in intervals): errors.append("conversion timestamps do not increase")
    if any(x < 0 for x in delays): errors.append("ADC read begins before recorded conversion trigger")
    if any(x < 16 for x in durations): errors.append("read shorter than modeled 128 clocks at 8 MHz")
    if any(x <= 0 for x in slack): errors.append("ADC read overlaps the next accepted conversion")
    if any(int(r["active_mask"]) != 3 for r in rows): errors.append("active mask differs from two-channel design")
    for previous, current in zip(rows, rows[1:]):
        slots = int(current["elapsed_slots"])
        if slots != int(current["sequence"]) - int(previous["sequence"]):
            errors.append("sequence delta and elapsed slots disagree")
        if slots > 1 and not int(current["flags"]) & 1: errors.append("missing slots lack GAP flag")
    observed_rate = rate(times)
    if observed_rate is not None and not 7920 <= observed_rate <= 8080:
        errors.append("capture mean EMG trigger rate differs from 8 kHz by more than 1 percent")
    return {"samples": len(rows), "first_trigger_us": times[0] if times else None,
            "last_trigger_us": times[-1] if times else None, "observed_trigger_rate_hz": observed_rate,
            "trigger_interval_us": distribution(intervals), "trigger_to_read_start_us": distribution(delays),
            "read_duration_us": distribution(durations), "read_end_to_next_trigger_us": distribution(slack),
            "pass": not errors, "errors": sorted(set(errors))}


def imu_timing(rows):
    errors = []
    times = [int(r["host_time_estimate_us"]) for r in rows]
    raw = [int(r["sensor_timestamp_raw"]) for r in rows]
    deltas = [(b - a) & 65535 for a, b in zip(raw, raw[1:])]
    estimate_deltas = [b - a for a, b in zip(times, times[1:])]
    read_delay = [int(r["read_end_us"]) - t for r, t in zip(rows, times)]
    anchor_age = [int(r["read_start_us"]) - int(r["irq_anchor_us"]) for r in rows]
    for r, t in zip(rows, times):
        if int(r["read_end_us"]) < int(r["read_start_us"]): errors.append("FIFO read window regresses")
        if t > int(r["read_end_us"]): errors.append("sample estimate is later than the FIFO read completion in this fixed-clock model")
        if not int(r["flags"]) & 2: errors.append("uncalibrated reconstructed timestamp lacks uncertainty flag")
    for d, dt, current in zip(deltas, estimate_deltas, rows[1:]):
        if d == 0 or d > 10000: errors.append("sensor interval duplicates or exceeds configured helper limit")
        if d != dt: errors.append("host estimate does not follow the raw modulo-16-bit counter delta")
        if d > 7500 and not int(current["flags"]) & 1: errors.append("missing sensor interval lacks GAP flag")
    observed_rate = rate(times)
    if observed_rate is not None and not 198 <= observed_rate <= 202:
        errors.append("capture mean sensor-counter rate differs from modeled 200 Hz by more than 1 percent")
    return {"samples": len(rows), "first_estimate_us": times[0] if times else None,
            "last_estimate_us": times[-1] if times else None,
            "sensor_counter_rate_hz": observed_rate, "raw_counter_delta_us": distribution(deltas),
            "estimate_to_read_end_us": distribution(read_delay), "irq_anchor_age_at_read_us": distribution(anchor_age),
            "first_estimate_minus_first_anchor_us": times[0] - int(rows[0]["irq_anchor_us"]) if rows else None,
            "timing_uncertain_samples": sum(bool(int(r["flags"]) & 2) for r in rows),
            "counter_rollovers": sum(b < a for a, b in zip(raw, raw[1:])),
            "pass": not errors, "errors": sorted(set(errors))}


def audit_capture(folder):
    result = {"case": folder.name, "scope": "post-processing of existing saved capture", "streams": {}, "sha256": {}}
    for name in ("emg", "foot", "shank"):
        path = folder / "converted" / (name + ".csv")
        if not path.exists(): continue
        result["sha256"][str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open() as file: rows = list(csv.DictReader(file))
        result["streams"][name] = emg_timing(rows) if name == "emg" else imu_timing(rows)
    raw = folder / "recorder-output.raw"
    if raw.exists():
        content = raw.read_bytes()
        result["sha256"][raw.name] = hashlib.sha256(content).hexdigest()
        length = struct.unpack_from("<I", content, 12)[0]
        result["production_metadata_bytes"] = length
        result["wifi_metadata_capacity_bytes"] = 1280
        result["wifi_metadata_remaining_bytes"] = 1280 - length
    foot, shank = result["streams"].get("foot"), result["streams"].get("shank")
    if foot and shank and foot["samples"] and shank["samples"]:
        offset = shank["first_estimate_us"] - foot["first_estimate_us"]
        result["startup"] = {"first_shank_minus_first_foot_estimate_us": offset,
                "foot_minus_shank_sample_count": foot["samples"] - shank["samples"],
                "explanation": "Production imu_start calls run sequentially and each waits 50 ms before enabling FIFO; unequal startup counts are not automatically sample loss.",
                "synchronization_measured": False,
                "offset_limit": "Each time origin depends on its own first IRQ/FIFO observation. This is an estimated startup offset, not measured foot-shank synchronization; independent clock drift and initial anchor error remain uncalibrated."}
        emg = result["streams"].get("emg")
        if emg and emg["samples"]:
            result["startup"]["foot_first_estimate_minus_first_emg_trigger_us"] = foot["first_estimate_us"] - emg["first_trigger_us"]
            result["startup"]["shank_first_estimate_minus_first_emg_trigger_us"] = shank["first_estimate_us"] - emg["first_trigger_us"]
    observed = [s for s in result["streams"].values() if s["samples"]]
    result["available_stream_timing_checks_pass"] = all(s["pass"] for s in observed) if observed else None
    result["full_case_execution_pass"] = None
    result["qualification_note"] = "Timing checks neither upgrade incomplete/quota-blocked executions nor establish physical timing. Empty or absent streams have no rate evidence."
    return result


def audit_stuck_busy_trace(path):
    """Read fixed Wokwi channel mapping; production performs two reset-time priming reads."""
    text = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text()
    if "$timescale 1ns $end" not in text: raise ValueError("requires 1 ns Wokwi VCD")
    mapping, state, now = {}, {}, 0
    triggers, widths, transactions = [], [], []
    current, pulse_start, trace_end = None, None, 0
    for line in text.splitlines():
        match = re.match(r"\$var\s+\S+\s+1\s+(\S+)\s+D([0-7])\b", line)
        if match: mapping[match[1]] = int(match[2]); continue
        if line.startswith("#"): now = int(line[1:]); trace_end = now; continue
        if len(line) < 2 or line[0] not in "01" or line[1:] not in mapping: continue
        ch, value = mapping[line[1:]], int(line[0])
        old = state.get(ch); state[ch] = value
        if old is None or old == value: continue
        if ch == 0:
            if value: triggers.append(now); pulse_start = now
            elif pulse_start is not None: widths.append(now - pulse_start); pulse_start = None
        if ch == 2:
            if not value: current = {"start_ns": now, "before_first_conversion": not triggers, "rising_clocks": 0, "falling_clocks": 0}
            elif current is not None:
                current["end_ns"] = now; transactions.append(current); current = None
        if ch == 3 and current is not None:
            current["rising_clocks" if value else "falling_clocks"] += 1
    priming = [x for x in transactions if x["before_first_conversion"]]
    acquisition = [x for x in transactions if not x["before_first_conversion"]]
    errors = []
    if set(mapping.values()) != set(range(8)): errors.append("missing analyzer channels")
    if len(priming) != 2 or any(x["rising_clocks"] != 128 or x["falling_clocks"] != 128 for x in priming):
        errors.append("expected two complete 128-clock reset-time priming reads")
    if len(triggers) != 1 or state.get(1) != 1: errors.append("expected one trigger and BUSY latched high")
    if acquisition or current is not None: errors.append("ADC serial read occurred after stuck conversion")
    if not widths or min(widths) < 25: errors.append("conversion pulse shorter than 25 ns")
    return {"case": "adc-stuck-busy", "scope": "post-processing of previously captured VCD", "hardware_measured": False,
            "trace_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "priming_reads": len(priming),
            "priming_transactions": priming, "conversion_triggers": len(triggers), "conversion_pulse_width_ns": widths,
            "post_trigger_adc_reads": len(acquisition), "busy_final_level": state.get(1), "trace_end_ns": trace_end,
            "reset_not_observed": True,
            "limits": "RESET is not an analyzer channel; reset-time classification uses the known initialization path and reads before first CONVST. This trace checks model logic, not module voltage or physical timing.",
            "pass": not errors, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=P / "results/current")
    parser.add_argument("--out", type=Path, default=P / "results/current/timing-audit.json")
    args = parser.parse_args()
    summary = {"hardware_measured": False, "new_firmware_execution": False, "full_integrated_matrix_pass": False,
               "limits": ["Results apply only to captured, fixed-clock behavioral-model data.",
                          "Sensor-counter rate is not physical clock accuracy or calibrated synchronization.",
                          "Read-window causality checks do not calibrate the initial IRQ/FIFO origin."],
               "captures": [audit_capture(p) for p in sorted(args.results.iterdir()) if (p / "converted").is_dir()]}
    trace = args.results / "adc-stuck-busy/logic.vcd.gz"
    if trace.exists(): summary["stuck_busy_trace"] = audit_stuck_busy_trace(trace)
    checks = [c["available_stream_timing_checks_pass"] for c in summary["captures"] if c["available_stream_timing_checks_pass"] is not None]
    summary["captured_timing_checks_pass"] = all(checks) and (summary.get("stuck_busy_trace", {}).get("pass", True))
    args.out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"captured_timing_checks_pass": summary["captured_timing_checks_pass"], "captures": len(summary["captures"]),
                      "new_firmware_execution": False, "stuck_busy_trace_pass": summary.get("stuck_busy_trace", {}).get("pass"),
                      "report": str(args.out)}, indent=2))
    return 0 if summary["captured_timing_checks_pass"] else 1


if __name__ == "__main__": raise SystemExit(main())
