"""Config loading with safe defaults."""
from pathlib import Path
import yaml

DEFAULTS = {
    "source": 0,
    "frame_width": 1280,
    "frame_height": 720,
    "model": "yolo11n.pt",
    "device": "auto",
    "imgsz": 640,
    "conf": 0.35,
    "iou": 0.5,
    "tracker": "trackers/bytetrack.yaml",
    "anchor": "center",
    "threshold": 3,
    "alert_duration": 2.0,
    "clear_delay": 0.5,
    "roi_file": "roi.json",
    "default_roi": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]],
    "window_name": "Crowd Counter",
    "show_ids": True,
    "output_dir": "output",
}


def load_config(path):
    cfg = dict(DEFAULTS)
    path = Path(path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
        cfg.update(user)
    else:
        print(f"[WARN] {path} not found, using default config.")
    if cfg["anchor"] not in ("center", "bottom"):
        raise ValueError("config: anchor must be 'center' or 'bottom'")
    return cfg
