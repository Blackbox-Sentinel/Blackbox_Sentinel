"""
verify_real_capture_schema.py
------------------------------
ISOLATED M2 diagnostic script. Does NOT modify sentinel_pipeline.py,
capture.py, or any production file. Per the "keep deployment isolated
until validated" rule in the M2/M3 continuation docs, this runs
standalone and only proves whether REAL captured traffic (not the
synthetic _demo_loop() traffic) produces valid 45-feature v3 windows.
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "m3-ml-ledger" / "src"))

REPORT_PATH = REPO_ROOT / "m2_real_capture_schema_report.json"


def list_interfaces():
    from scapy.all import get_if_list
    ifaces = get_if_list()
    print("\nAvailable interfaces (pass one of these to --iface):")
    for i, name in enumerate(ifaces):
        print(f"  [{i}] {name}")
    return ifaces


def load_pipeline_pieces():
    try:
        from feature_pipeline_v2 import (
            capture_live_window,
            RollingFeatureState,
            model_feature_columns,
        )
    except ImportError:
        from ml.feature_pipeline_v2 import (
            capture_live_window,
            RollingFeatureState,
            model_feature_columns,
        )

    try:
        from predict_v3 import AnomalyScorer
    except ImportError as e:
        print(f"[FATAL] Could not import AnomalyScorer from predict_v3.py: {e}")
        sys.exit(1)

    return capture_live_window, RollingFeatureState, model_feature_columns, AnomalyScorer


def run_live(iface, num_windows, org_id):
    capture_live_window, RollingFeatureState, model_feature_columns, AnomalyScorer = load_pipeline_pieces()

    expected_cols = model_feature_columns(history_windows=5)
    print(f"[INFO] Expecting {len(expected_cols)} features per window.")

    history_state = RollingFeatureState(history_windows=5)
    scorer = AnomalyScorer(organization_id=org_id)

    results = []
    empty_windows = 0

    for i in range(num_windows):
        print(f"[CAPTURE] Window {i + 1}/{num_windows} on iface='{iface}' ...")
        try:
            feature_row = capture_live_window(
                timeout=1.0, iface=iface, history_state=history_state
            )
        except Exception as e:
            print(f"[ERROR] capture_live_window failed: {e}")
            results.append({"window": i, "error": str(e)})
            continue

        if not feature_row or feature_row.get("packets_per_sec", 0) == 0:
            empty_windows += 1

        actual_keys = set(feature_row.keys()) - {"timestamp", "window_start_epoch"}
        expected_keys = set(expected_cols)
        missing = expected_keys - actual_keys
        extra = actual_keys - expected_keys

        row_for_scorer = dict(feature_row)
        row_for_scorer["timestamp"] = row_for_scorer.get("timestamp", time.time())
        row_for_scorer["organization_id"] = org_id

        try:
            scored = scorer.ingest_feature_window(row_for_scorer)
        except Exception as e:
            print(f"[ERROR] ingest_feature_window failed: {e}")
            scored = {"error": str(e)}

        results.append({
            "window": i,
            "feature_count": len(actual_keys),
            "expected_count": len(expected_keys),
            "missing_features": sorted(missing),
            "extra_features": sorted(extra),
            "schema_ok": not missing and not extra,
            "scorer_result": scored,
        })

        print(
            f"  -> features={len(actual_keys)}/{len(expected_keys)} "
            f"schema_ok={not missing and not extra} "
            f"scored={scored.get('state', scored.get('error', '?'))}"
        )

    summary = {
        "mode": "live_capture",
        "iface": iface,
        "organization_id": org_id,
        "windows_requested": num_windows,
        "windows_captured": len(results),
        "empty_windows": empty_windows,
        "all_schema_ok": all(r.get("schema_ok") for r in results if "schema_ok" in r),
        "results": results,
    }

    REPORT_PATH.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\n[DONE] Report written to {REPORT_PATH}")
    print(f"[SUMMARY] all_schema_ok={summary['all_schema_ok']} empty_windows={empty_windows}")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Validate real M2 capture against M3's 45-feature v3 schema.")
    parser.add_argument("--list-interfaces", action="store_true")
    parser.add_argument("--iface", type=str, default=None)
    parser.add_argument("--windows", type=int, default=10)
    parser.add_argument("--org-id", type=str, default="organization_a")
    args = parser.parse_args()

    if args.list_interfaces:
        list_interfaces()
        return

    if not args.iface:
        print("[FATAL] Pass --iface (run --list-interfaces first to see options).")
        sys.exit(1)

    run_live(args.iface, args.windows, args.org_id)


if __name__ == "__main__":
    main()
