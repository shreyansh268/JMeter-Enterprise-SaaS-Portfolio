#!/usr/bin/env python3
"""
JMeter SLO Assertion Script
Author: Shreyansh Sharma | QE Expert Portfolio
Purpose: Parse JTL results and assert p99 + error rate SLOs
         Fails the CI build if thresholds are breached
"""

import csv
import sys
import statistics
import argparse
from pathlib import Path
from collections import defaultdict


def parse_jtl(jtl_path: str) -> tuple[list[int], list[int], dict]:
    """Parse JMeter JTL CSV file into elapsed times and error counts."""
    elapsed_all = []
    errors_all = []
    per_sampler = defaultdict(lambda: {"elapsed": [], "errors": 0})

    with open(jtl_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            elapsed = int(row['elapsed'])
            success = row['success'].strip().lower() == 'true'
            label = row['label']

            elapsed_all.append(elapsed)
            per_sampler[label]["elapsed"].append(elapsed)

            if not success:
                errors_all.append(elapsed)
                per_sampler[label]["errors"] += 1

    return elapsed_all, errors_all, per_sampler


def percentile(data: list[int], pct: float) -> int:
    """Calculate nth percentile from a sorted list."""
    if not data:
        return 0
    s = sorted(data)
    idx = int(len(s) * pct / 100)
    return s[min(idx, len(s) - 1)]


def format_ms(ms: int) -> str:
    return f"{ms}ms"


def main():
    parser = argparse.ArgumentParser(description="Assert JMeter SLO thresholds")
    parser.add_argument("--jtl",        required=True,  help="Path to results.jtl")
    parser.add_argument("--p99-slo",    type=int, default=800,  help="p99 SLO in ms")
    parser.add_argument("--error-slo",  type=float, default=0.01, help="Error rate SLO (0.01 = 1%)")
    parser.add_argument("--run-label",  default="Load Test Run", help="Label for report output")
    args = parser.parse_args()

    if not Path(args.jtl).exists():
        print(f"ERROR: JTL file not found: {args.jtl}")
        sys.exit(1)

    elapsed_all, errors_all, per_sampler = parse_jtl(args.jtl)

    if not elapsed_all:
        print("ERROR: No results found in JTL file")
        sys.exit(1)

    total      = len(elapsed_all)
    error_count = len(errors_all)
    error_rate  = error_count / total if total else 0

    p50_all = percentile(elapsed_all, 50)
    p90_all = percentile(elapsed_all, 90)
    p95_all = percentile(elapsed_all, 95)
    p99_all = percentile(elapsed_all, 99)
    avg_all = int(statistics.mean(elapsed_all))

    print(f"\n{'═' * 60}")
    print(f"  JMeter SLO Assertion — {args.run_label}")
    print(f"{'═' * 60}")
    print(f"  Total requests : {total:,}")
    print(f"  Errors         : {error_count:,}  ({error_rate:.2%})")
    print(f"  Average        : {format_ms(avg_all)}")
    print(f"  p50            : {format_ms(p50_all)}")
    print(f"  p90            : {format_ms(p90_all)}")
    print(f"  p95            : {format_ms(p95_all)}")
    print(f"  p99            : {format_ms(p99_all)}")
    print(f"{'─' * 60}")
    print(f"  SLO: p99 < {args.p99_slo}ms | error rate < {args.error_slo:.0%}")
    print(f"{'─' * 60}")

    # Per-sampler breakdown
    print(f"\n  Per-Sampler Breakdown:")
    print(f"  {'Sampler':<35} {'p99':>8} {'Errors':>8} {'Status':>8}")
    print(f"  {'─' * 35} {'─' * 8} {'─' * 8} {'─' * 8}")

    sampler_failures = []
    for label, data in sorted(per_sampler.items()):
        s_p99 = percentile(data["elapsed"], 99)
        s_total = len(data["elapsed"]) + data["errors"]
        s_err_rate = data["errors"] / s_total if s_total else 0
        status = "✅ PASS" if s_p99 < args.p99_slo and s_err_rate < args.error_slo else "❌ FAIL"
        if "FAIL" in status:
            sampler_failures.append(label)
        print(f"  {label:<35} {format_ms(s_p99):>8} {s_err_rate:>7.2%} {status:>8}")

    print(f"\n{'═' * 60}")

    # Gate assertions
    failures = []

    if p99_all >= args.p99_slo:
        failures.append(
            f"p99 SLO BREACH: {format_ms(p99_all)} >= {format_ms(args.p99_slo)} limit"
        )

    if error_rate >= args.error_slo:
        failures.append(
            f"Error rate SLO BREACH: {error_rate:.2%} >= {args.error_slo:.0%} limit"
        )

    if failures:
        print(f"\n  ❌ GATE FAILED — build blocked")
        for f in failures:
            print(f"     → {f}")
        if sampler_failures:
            print(f"     → Failing samplers: {', '.join(sampler_failures)}")
        print(f"{'═' * 60}\n")
        sys.exit(1)
    else:
        print(f"\n  ✅ ALL SLOs PASSED — safe to deploy")
        print(f"{'═' * 60}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
