"""Compare exported M3-Platform and EEGLAB EEG preprocessing outputs."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def load_and_align(m3_path, reference_path):
    m3 = pd.read_csv(m3_path)
    reference = pd.read_csv(reference_path)
    m3_channels = [column for column in m3.columns if column != "Time_s"]
    reference_map = {
        column.lower(): column for column in reference.columns if column != "Time_s"
    }
    channel_pairs = [
        (channel, reference_map[channel.lower()])
        for channel in m3_channels
        if channel.lower() in reference_map
    ]
    if not channel_pairs:
        raise ValueError("No common EEG channel names were found.")
    n_samples = min(len(m3), len(reference))
    return m3.iloc[:n_samples], reference.iloc[:n_samples], channel_pairs


def compute_metrics(m3, reference, channel_pairs):
    rows = []
    for m3_channel, reference_channel in channel_pairs:
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
                "Channel": m3_channel,
                "Pearson_r": round(float(pearson_r), 6),
                "p_value": float(p_value),
                "RMSE_uV": round(float(rmse), 6),
                "NRMSE_pct": round(float(nrmse), 4),
                "Max_Abs_Error_uV": round(float(max_error), 6),
                "N_samples": len(m3_values),
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("No EEG channel contained at least 10 paired finite samples.")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Calculate the EEG agreement metrics reported for Table 3."
    )
    parser.add_argument("m3_csv", type=Path, help="M3-Platform exported CSV")
    parser.add_argument("reference_csv", type=Path, help="EEGLAB exported CSV")
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    m3, reference, channel_pairs = load_and_align(args.m3_csv, args.reference_csv)
    result = compute_metrics(m3, reference, channel_pairs)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output_dir / "eeg_comparison.csv", index=False)

    summary = {
        "n_channels": len(result),
        "pearson_r_mean": round(float(result["Pearson_r"].mean()), 6),
        "pearson_r_min": round(float(result["Pearson_r"].min()), 6),
        "pearson_r_max": round(float(result["Pearson_r"].max()), 6),
        "rmse_uv_mean": round(float(result["RMSE_uV"].mean()), 6),
        "rmse_uv_max": round(float(result["RMSE_uV"].max()), 6),
        "nrmse_pct_mean": round(float(result["NRMSE_pct"].mean()), 4),
    }
    (args.output_dir / "eeg_comparison_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
