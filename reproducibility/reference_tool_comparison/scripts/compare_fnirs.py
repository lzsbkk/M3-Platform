"""Compare exported M3-Platform and Homer3 fNIRS preprocessing outputs."""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def normalize_channel_name(name):
    return re.sub(r"\s+", " ", name.strip()).lower()


def load_and_align(m3_path, reference_path):
    m3 = pd.read_csv(m3_path)
    reference = pd.read_csv(reference_path)
    m3_channels = [column for column in m3.columns if column != "Time_s"]
    reference_channels = [column for column in reference.columns if column != "Time_s"]
    reference_map = {normalize_channel_name(column): column for column in reference_channels}
    channel_pairs = []
    for m3_channel in m3_channels:
        normalized = normalize_channel_name(m3_channel)
        if normalized in reference_map:
            channel_pairs.append((m3_channel, reference_map[normalized], normalized))
    if not channel_pairs:
        raise ValueError("No common fNIRS channel names were found.")
    n_samples = min(len(m3), len(reference))
    return m3.iloc[:n_samples], reference.iloc[:n_samples], channel_pairs


def compute_metrics(m3_path, reference_path, stage):
    m3, reference, channel_pairs = load_and_align(m3_path, reference_path)
    rows = []
    for m3_channel, reference_channel, normalized in channel_pairs:
        m3_values = m3[m3_channel].to_numpy(dtype=float)
        reference_values = reference[reference_channel].to_numpy(dtype=float)
        valid = np.isfinite(m3_values) & np.isfinite(reference_values)
        m3_values = m3_values[valid]
        reference_values = reference_values[valid]
        if len(m3_values) < 10:
            continue

        pearson_r, p_value = stats.pearsonr(m3_values, reference_values)
        rmse = np.sqrt(np.mean((m3_values - reference_values) ** 2))
        max_error = np.max(np.abs(m3_values - reference_values))
        scale = np.max(np.abs(np.concatenate([m3_values, reference_values])))
        nrmse = 100 * rmse / scale if scale > 0 else 0.0
        rows.append(
            {
                "Channel": normalized,
                "Type": "HbO" if "hbo" in normalized else "HbR",
                "Stage": stage,
                "Pearson_r": round(float(pearson_r), 6),
                "p_value": float(p_value),
                "RMSE_uMol": round(float(rmse), 6),
                "NRMSE_pct": round(float(nrmse), 4),
                "Max_Abs_Error_uMol": round(float(max_error), 6),
                "N_samples": len(m3_values),
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError(f"No {stage} channel contained at least 10 paired finite samples.")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Calculate the fNIRS agreement metrics reported for Table 3."
    )
    parser.add_argument("--m3-pre", type=Path, required=True)
    parser.add_argument("--reference-pre", type=Path, required=True)
    parser.add_argument("--m3-post", type=Path, required=True)
    parser.add_argument("--reference-post", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    pre = compute_metrics(args.m3_pre, args.reference_pre, "Pre-Bandpass")
    post = compute_metrics(args.m3_post, args.reference_post, "Post-Bandpass")
    result = pd.concat([pre, post], ignore_index=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output_dir / "fnirs_comparison.csv", index=False)

    summary = {}
    for stage, prefix in [("Pre-Bandpass", "pre_bandpass"), ("Post-Bandpass", "post_bandpass")]:
        subset = result[result["Stage"] == stage]
        summary[f"{prefix}_r_mean"] = round(float(subset["Pearson_r"].mean()), 4)
        summary[f"{prefix}_rmse_mean"] = round(float(subset["RMSE_uMol"].mean()), 4)
        for signal_type in ("HbO", "HbR"):
            typed = subset[subset["Type"] == signal_type]
            summary[f"{prefix}_{signal_type.lower()}_r_mean"] = round(
                float(typed["Pearson_r"].mean()), 4
            )
            summary[f"{prefix}_{signal_type.lower()}_rmse_mean"] = round(
                float(typed["RMSE_uMol"].mean()), 4
            )
    (args.output_dir / "fnirs_comparison_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
