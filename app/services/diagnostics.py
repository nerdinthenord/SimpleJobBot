from collections import deque
from datetime import datetime
from pathlib import Path
import os
from typing import Dict, Any

OUTPUT_ROOT = Path("job-packages")
ERROR_BUFFER = deque(maxlen=20)


def init_diagnostics():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def record_error(exc: Exception):
    ERROR_BUFFER.appendleft(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "message": str(exc),
        }
    )


def get_recent_errors():
    return list(ERROR_BUFFER)


def get_output_stats() -> Dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    job_dirs = [p for p in OUTPUT_ROOT.iterdir() if p.is_dir()]
    total_jobs = len(job_dirs)

    total_bytes = 0
    for root, dirs, files in os.walk(OUTPUT_ROOT):
        for name in files:
            try:
                total_bytes += (Path(root) / name).stat().st_size
            except FileNotFoundError:
                continue

    return {
        "total_jobs": total_jobs,
        "total_bytes": total_bytes,
    }


def get_dashboard_stats() -> Dict[str, Any]:
    return {
        "errors": get_recent_errors(),
        "output": get_output_stats(),
    }
