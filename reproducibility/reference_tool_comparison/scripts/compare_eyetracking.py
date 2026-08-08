"""Compare exported M3-Platform and Tobii Pro Lab eye-tracking outputs."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score, f1_score


def load_tobii(path):
    data = pd.read_csv(path, sep="\t", encoding="utf-8-sig", low_memory=False)
    data = data[data["Sensor"] == "Eye Tracker"].copy().reset_index(drop=True)
    timestamp_max = data["Recording timestamp"].max()
    data["Timestamp_s"] = data["Recording timestamp"] / (
        1e6 if timestamp_max > 1e6 else 1e3
    )
    data["GazeX_px"] = pd.to_numeric(data["Gaze point X"], errors="coerce")
    data["GazeY_px"] = pd.to_numeric(data["Gaze point Y"], errors="coerce")
    data["Pupil_mm"] = pd.to_numeric(data["Pupil diameter filtered"], errors="coerce")
    data["EventType"] = data["Eye movement type"]
    data["EventIndex"] = pd.to_numeric(data["Eye movement type index"], errors="coerce")
    data["EventDuration_ms"] = pd.to_numeric(
        data["Eye movement event duration"], errors="coerce"
    )
    data["FixX_px"] = pd.to_numeric(data["Fixation point X"], errors="coerce")
    data["FixY_px"] = pd.to_numeric(data["Fixation point Y"], errors="coerce")

    fixation_rows = data[data["EventType"] == "Fixation"]
    fixations = fixation_rows.groupby("EventIndex").agg(
        Start_s=("Timestamp_s", "min"),
        End_s=("Timestamp_s", "max"),
        Duration_ms=("EventDuration_ms", "first"),
        X_px=("FixX_px", "first"),
        Y_px=("FixY_px", "first"),
    ).reset_index()
    fixations["Duration_s"] = fixations["Duration_ms"] / 1000
    gaze = data[["Timestamp_s", "GazeX_px", "GazeY_px", "Pupil_mm", "EventType"]]
    return gaze, fixations


def align_by_timestamp(m3, reference, tolerance_seconds):
    m3 = m3.sort_values("Timestamp_s").reset_index(drop=True)
    reference = reference.sort_values("Timestamp_s").reset_index(drop=True)
    merged = pd.merge_asof(
        m3,
        reference,
        on="Timestamp_s",
        direction="nearest",
        tolerance=tolerance_seconds,
        suffixes=("_m3", "_tobii"),
    )
    return merged.dropna(subset=["GazeX_px_m3", "GazeX_px_tobii"])


def signal_metrics(merged, m3_column, reference_column, name):
    m3_values = merged[m3_column].to_numpy(dtype=float)
    reference_values = merged[reference_column].to_numpy(dtype=float)
    valid = np.isfinite(m3_values) & np.isfinite(reference_values)
    m3_values = m3_values[valid]
    reference_values = reference_values[valid]
    if len(m3_values) < 10:
        raise ValueError(f"{name} contained fewer than 10 paired finite samples.")
    pearson_r, p_value = stats.pearsonr(m3_values, reference_values)
    errors = m3_values - reference_values
    return {
        "Signal": name,
        "N_samples": len(m3_values),
        "Pearson_r": round(float(pearson_r), 6),
        "p_value": float(p_value),
        "RMSE": round(float(np.sqrt(np.mean(errors ** 2))), 4),
        "MAE": round(float(np.mean(np.abs(errors))), 4),
        "Max_Error": round(float(np.max(np.abs(errors))), 4),
    }


def fixation_metrics(m3_fixations, reference_fixations, merged, threshold):
    result = {
        "Config": "matched",
        "M3_fixation_count": len(m3_fixations),
        "Tobii_fixation_count": len(reference_fixations),
        "M3_mean_duration_ms": round(float(m3_fixations["Duration_s"].mean() * 1000), 1),
        "Tobii_mean_duration_ms": round(float(reference_fixations["Duration_s"].mean() * 1000), 1),
        "M3_median_duration_ms": round(float(m3_fixations["Duration_s"].median() * 1000), 1),
        "Tobii_median_duration_ms": round(float(reference_fixations["Duration_s"].median() * 1000), 1),
    }
    velocity = merged["Velocity_deg_s"].to_numpy(dtype=float)
    reference_type = merged["EventType"].to_numpy()
    valid = np.isfinite(velocity) & np.isin(reference_type, ["Fixation", "Saccade"])
    m3_is_fixation = velocity[valid] < threshold
    reference_is_fixation = reference_type[valid] == "Fixation"
    result["Sample_agreement_pct"] = round(
        float(np.mean(m3_is_fixation == reference_is_fixation) * 100), 1
    )
    result["Cohen_kappa"] = round(
        float(cohen_kappa_score(reference_is_fixation, m3_is_fixation)), 4
    )
    result["Fixation_F1"] = round(
        float(f1_score(reference_is_fixation, m3_is_fixation)), 4
    )
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Calculate the eye-tracking agreement metrics reported for Table 3."
    )
    parser.add_argument("--m3-gaze", type=Path, required=True)
    parser.add_argument("--m3-fixations", type=Path, required=True)
    parser.add_argument("--tobii-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--timestamp-tolerance-ms", type=float, default=15.0)
    parser.add_argument("--velocity-threshold", type=float, default=30.0)
    args = parser.parse_args()

    m3_gaze = pd.read_csv(args.m3_gaze)
    m3_fixations = pd.read_csv(args.m3_fixations)
    reference_gaze, reference_fixations = load_tobii(args.tobii_tsv)
    merged = align_by_timestamp(
        m3_gaze, reference_gaze, args.timestamp_tolerance_ms / 1000
    )

    signals = pd.DataFrame(
        [
            signal_metrics(merged, "GazeX_px_m3", "GazeX_px_tobii", "GazeX_matched"),
            signal_metrics(merged, "GazeY_px_m3", "GazeY_px_tobii", "GazeY_matched"),
            signal_metrics(merged, "Pupil_mm_m3", "Pupil_mm_tobii", "Pupil_matched"),
        ]
    )
    fixations = pd.DataFrame(
        [
            fixation_metrics(
                m3_fixations,
                reference_fixations,
                merged,
                args.velocity_threshold,
            )
        ]
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    signals.to_csv(args.output_dir / "et_signal_comparison.csv", index=False)
    fixations.to_csv(args.output_dir / "et_fixation_comparison.csv", index=False)
    summary = {
        "signal_metrics": signals.to_dict(orient="records"),
        "fixation_metrics": fixations.to_dict(orient="records"),
    }
    (args.output_dir / "et_comparison_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
