#!/usr/bin/env python3
"""People counting + crowd threshold alert (YOLO11n + ByteTrack + ROI)."""
import argparse
import os
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)  # model download & relative paths are always resolved from the project root
sys.path.insert(0, str(ROOT))

from src.alert import CrowdAlert              # noqa: E402
from src.config import load_config            # noqa: E402
from src.detector import PersonTracker        # noqa: E402
from src.roi import ROI, select_roi_interactive  # noqa: E402
from src.visualizer import draw_frame         # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(description="People counting & crowd alert")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--source", help="camera index (e.g. 0) or video file path")
    p.add_argument("--threshold", type=int, help="override threshold from config")
    p.add_argument("--duration", type=float, help="alert duration (sec) override")
    p.add_argument("--conf", type=float, help="detection confidence override")
    p.add_argument("--reset-roi", action="store_true", help="delete the saved ROI and go back to the default")
    return p.parse_args()


def open_source(source, width, height):
    if isinstance(source, str) and source.isdigit():
        source = int(source)
    if isinstance(source, int):
        cap = cv2.VideoCapture(source, cv2.CAP_V4L2)  # Linux webcam
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    else:
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        sys.exit(f"[ERROR] Could not open video source: {source}\n"
                 "        Run 'v4l2-ctl --list-devices' to find the camera index, "
                 "or check whether another program is using the camera.")
    return cap


def main():
    args = parse_args()
    cfg = load_config(args.config)
    if args.source is not None:
        cfg["source"] = args.source
    if args.threshold is not None:
        cfg["threshold"] = args.threshold
    if args.duration is not None:
        cfg["alert_duration"] = args.duration
    if args.conf is not None:
        cfg["conf"] = args.conf

    roi_path = Path(cfg["roi_file"])
    if args.reset_roi and roi_path.exists():
        roi_path.unlink()
        print(f"[INFO] Deleted {roi_path}.")
    roi = ROI.load(roi_path, cfg["default_roi"])

    print("[INFO] Loading model (yolo11n.pt is downloaded on first run)...")
    tracker = PersonTracker(cfg["model"], cfg["tracker"], cfg["conf"], cfg["iou"],
                            cfg["imgsz"], cfg["device"])
    alert = CrowdAlert(cfg["threshold"], cfg["alert_duration"], cfg["clear_delay"])
    cap = open_source(cfg["source"], cfg["frame_width"], cfg["frame_height"])

    win = cfg["window_name"]
    cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)
    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(exist_ok=True)

    unique_ids = set()
    fps, last_t, was_active = 0.0, time.monotonic(), False
    frame = None

    print("[INFO] Started. q = quit | r = draw ROI | +/- = threshold | s = screenshot")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[INFO] No frame received (end of video or camera problem).")
            break
        h, w = frame.shape[:2]

        dets = tracker.track(frame)
        for d in dets:
            d.inside = roi.contains(d.anchor_point(cfg["anchor"]), w, h)
            if d.inside:
                unique_ids.add(d.track_id)
        count = sum(d.inside for d in dets)

        state = alert.update(count)
        if state.active != was_active:
            stamp = time.strftime("%H:%M:%S")
            print(f"[{stamp}] {'CROWD ALERT started' if state.active else 'Alert cleared'} "
                  f"(count={count}, threshold={alert.threshold})")
            was_active = state.active

        now = time.monotonic()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - last_t, 1e-6)) if fps else 1.0 / max(now - last_t, 1e-6)
        last_t = now

        draw_frame(frame, dets, roi, state, count, len(unique_ids),
                   alert.threshold, fps, cfg["anchor"], cfg["show_ids"])
        cv2.imshow(win, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord("r"):
            new_roi = select_roi_interactive(frame.copy(), win)
            if new_roi is not None:
                roi = new_roi
                roi.save(roi_path)
                unique_ids.clear()
                print(f"[INFO] New ROI saved: {roi_path}")
        elif key in (ord("+"), ord("=")):
            alert.threshold += 1
        elif key in (ord("-"), ord("_")):
            alert.threshold = max(0, alert.threshold - 1)
        elif key == ord("s"):
            fn = out_dir / f"shot_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(str(fn), frame)
            print(f"[INFO] Screenshot: {fn}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
