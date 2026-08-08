"""Opt-in performance recording for operations started from the GUI.

Set ``M3_GUI_PERFORMANCE_DIR`` before starting M3-Platform to enable the
recorder.  When the variable is unset, decorated GUI slots behave normally.
One button click produces one record; the recorder never repeats an operation
or mutates application data on its own.
"""

from __future__ import annotations

import csv
import inspect
import json
import os
import platform
import statistics
import sys
import threading
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil


MIB = 1024 * 1024
RAW_FIELDS = [
    "timestamp",
    "session",
    "operation",
    "phase",
    "run",
    "included_in_summary",
    "duration_ms",
    "cpu_seconds",
    "average_cpu_percent",
    "logical_cpu_count",
    "baseline_rss_mib",
    "absolute_peak_rss_mib",
    "incremental_peak_rss_mib",
    "sample_interval_ms",
    "process_id",
    "status",
]
SUMMARY_METRICS = [
    "duration_ms",
    "baseline_rss_mib",
    "absolute_peak_rss_mib",
    "incremental_peak_rss_mib",
]
_WRITE_LOCK = threading.Lock()


def _process_tree_rss(process: psutil.Process) -> int:
    processes = [process]
    try:
        processes.extend(process.children(recursive=True))
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass

    total = 0
    for item in processes:
        try:
            total += item.memory_info().rss
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return total


def _read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _percentile_summary(values: List[float]) -> Dict[str, float]:
    quartiles = (
        statistics.quantiles(values, n=4, method="inclusive")
        if len(values) > 1
        else [values[0]] * 3
    )
    return {
        "median": statistics.median(values),
        "q1": quartiles[0],
        "q3": quartiles[2],
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


class GuiPerformanceRecorder:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_path = self.output_dir / "gui_raw_results.csv"
        self.summary_path = self.output_dir / "gui_summary_results.csv"
        self.sample_interval_ms = float(os.getenv("M3_GUI_PERFORMANCE_SAMPLE_MS", "2"))
        self.baseline_seconds = float(os.getenv("M3_GUI_PERFORMANCE_BASELINE_SECONDS", "0.5"))
        self.warmup_runs = int(os.getenv("M3_GUI_PERFORMANCE_WARMUPS", "1"))
        self.measured_runs = int(os.getenv("M3_GUI_PERFORMANCE_RUNS", "20"))
        self.session = os.getenv("M3_GUI_PERFORMANCE_SESSION", "default")
        self.process = psutil.Process(os.getpid())
        self._write_environment()

    def _write_environment(self) -> None:
        path = self.output_dir / "gui_environment.json"
        if path.exists():
            return
        payload = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S %z"),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "psutil_version": psutil.__version__,
            "logical_cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "total_memory_mib": psutil.virtual_memory().total / MIB,
            "sample_interval_ms": self.sample_interval_ms,
            "baseline_seconds": self.baseline_seconds,
            "warmup_runs": self.warmup_runs,
            "measured_runs": self.measured_runs,
            "measurement_scope": "M3-Platform application process tree",
            "trigger": "decorated slot entered through its GUI button signal",
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _phase_and_run(self, operation: str) -> Tuple[str, int, bool]:
        rows = [
            row
            for row in _read_rows(self.raw_path)
            if row["session"] == self.session
            and row["operation"] == operation
            and row["status"] == "returned"
        ]
        if len(rows) < self.warmup_runs:
            return "warmup", len(rows) + 1, False
        measured_index = len(rows) - self.warmup_runs + 1
        included = measured_index <= self.measured_runs
        return ("measured" if included else "extra"), measured_index, included

    def _baseline_rss(self) -> int:
        samples = []
        deadline = time.monotonic() + self.baseline_seconds
        interval = self.sample_interval_ms / 1000
        while time.monotonic() < deadline:
            samples.append(_process_tree_rss(self.process))
            time.sleep(interval)
        return int(statistics.median(samples)) if samples else _process_tree_rss(self.process)

    def measure(self, operation: str, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        with _WRITE_LOCK:
            phase, run_number, included = self._phase_and_run(operation)

        baseline_rss = self._baseline_rss()
        interval = self.sample_interval_ms / 1000
        stop_sampling = threading.Event()
        peak_rss = [baseline_rss]

        def sample_memory() -> None:
            while not stop_sampling.is_set():
                peak_rss[0] = max(peak_rss[0], _process_tree_rss(self.process))
                stop_sampling.wait(interval)

        sampler = threading.Thread(target=sample_memory, name="m3-rss-sampler", daemon=True)
        cpu_before = self.process.cpu_times()
        sampler.start()
        start_ns = time.perf_counter_ns()
        status = "returned"
        try:
            return function(*args, **kwargs)
        except Exception:
            status = "raised"
            raise
        finally:
            end_ns = time.perf_counter_ns()
            stop_sampling.set()
            sampler.join(timeout=max(1.0, interval * 10))
            peak_rss[0] = max(peak_rss[0], _process_tree_rss(self.process))
            cpu_after = self.process.cpu_times()
            duration_seconds = (end_ns - start_ns) / 1_000_000_000
            cpu_seconds = (cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system)
            logical_cpus = os.cpu_count() or 1
            row = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S %z"),
                "session": self.session,
                "operation": operation,
                "phase": phase,
                "run": run_number,
                "included_in_summary": included,
                "duration_ms": duration_seconds * 1000,
                "cpu_seconds": cpu_seconds,
                "average_cpu_percent": (
                    cpu_seconds / (duration_seconds * logical_cpus) * 100
                    if duration_seconds > 0
                    else 0.0
                ),
                "logical_cpu_count": logical_cpus,
                "baseline_rss_mib": baseline_rss / MIB,
                "absolute_peak_rss_mib": peak_rss[0] / MIB,
                "incremental_peak_rss_mib": max(0.0, (peak_rss[0] - baseline_rss) / MIB),
                "sample_interval_ms": self.sample_interval_ms,
                "process_id": os.getpid(),
                "status": status,
            }
            self._append(row)
            print(
                f"[GUI performance] {operation}: {phase} {run_number}, "
                f"{row['duration_ms']:.2f} ms, peak RSS {row['absolute_peak_rss_mib']:.2f} MiB"
            )

    def _append(self, row: Dict[str, Any]) -> None:
        with _WRITE_LOCK:
            exists = self.raw_path.exists()
            encoding = "utf-8" if exists else "utf-8-sig"
            with self.raw_path.open("a", newline="", encoding=encoding) as handle:
                writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS)
                if not exists:
                    writer.writeheader()
                writer.writerow(row)
            self._write_summary(_read_rows(self.raw_path))

    def _write_summary(self, rows: List[Dict[str, str]]) -> None:
        included = [
            row
            for row in rows
            if row["session"] == self.session
            and row["included_in_summary"].lower() == "true"
            and row["status"] == "returned"
        ]
        operations = list(dict.fromkeys(row["operation"] for row in included))
        fields = ["session", "operation", "n"]
        for metric in SUMMARY_METRICS:
            fields.extend(f"{metric}_{name}" for name in ("median", "q1", "q3", "min", "max", "mean", "sd"))

        with self.summary_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for operation in operations:
                group = [row for row in included if row["operation"] == operation]
                summary: Dict[str, Any] = {
                    "session": self.session,
                    "operation": operation,
                    "n": len(group),
                }
                for metric in SUMMARY_METRICS:
                    values = [float(row[metric]) for row in group]
                    for name, value in _percentile_summary(values).items():
                        summary[f"{metric}_{name}"] = value
                writer.writerow(summary)


class PerformanceMonitor:
    """Record one real GUI-slot execution when GUI performance mode is enabled."""

    def __init__(self, operation: Optional[str] = None):
        self.operation = operation

    def __call__(self, function: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            output_dir = os.getenv("M3_GUI_PERFORMANCE_DIR")
            if not output_dir:
                return function(*args, **kwargs)
            call_args = args
            try:
                inspect.signature(function).bind(*call_args, **kwargs)
            except TypeError:
                if call_args and isinstance(call_args[-1], bool):
                    call_args = call_args[:-1]
                    inspect.signature(function).bind(*call_args, **kwargs)
                else:
                    raise
            operation = self.operation or function.__name__
            recorder = GuiPerformanceRecorder(Path(output_dir).expanduser().resolve())
            return recorder.measure(operation, function, *call_args, **kwargs)

        return wrapped
