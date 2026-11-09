"""Web adapter for the existing YOLO11 + ByteTrack crowd counter."""
import base64, sys, time
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[2]
COUNTER = ROOT / "crowd_counter"
sys.path.insert(0, str(COUNTER))
from src.alert import CrowdAlert
from src.config import load_config
from src.detector import PersonTracker
from src.roi import ROI
from src.visualizer import draw_frame

class CounterEngine:
    def __init__(self, source="0", threshold=None):
        self.cfg = load_config(COUNTER / "config.yaml")
        if threshold is not None:
            self.cfg["threshold"] = threshold
        model_path = Path(self.cfg["model"])
        if not model_path.is_absolute():
            model_path = COUNTER / model_path
        tracker_path = COUNTER / self.cfg["tracker"]
        self.tracker = PersonTracker(str(model_path), str(tracker_path),
            self.cfg["conf"], self.cfg["iou"], self.cfg["imgsz"], self.cfg["device"])
        self.roi = ROI.load(COUNTER / self.cfg["roi_file"], self.cfg["default_roi"])
        self.alert = CrowdAlert(self.cfg["threshold"], self.cfg["alert_duration"], self.cfg["clear_delay"])
        self.unique, self.was_active, self.fps = set(), False, 0.0
        source = int(source) if str(source).isdigit() else source
        self.cap = cv2.VideoCapture(source, cv2.CAP_V4L2) if isinstance(source, int) else cv2.VideoCapture(str(source))
        if isinstance(source, int):
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg["frame_width"])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg["frame_height"])
        if not self.cap.isOpened():
            self.cap.release()
            raise RuntimeError(f"Cannot open camera/video source: {source}")
        self.last = time.monotonic()

    def set_threshold(self, value):
        self.alert.threshold = max(0, int(value))

    def close(self):
        self.cap.release()

    def next(self):
        ok, frame = self.cap.read()
        if not ok:
            return None
        h, w = frame.shape[:2]
        dets = self.tracker.track(frame)
        for d in dets:
            d.inside = self.roi.contains(d.anchor_point(self.cfg["anchor"]), w, h)
            if d.inside:
                self.unique.add(d.track_id)
        count = sum(d.inside for d in dets)
        state = self.alert.update(count)
        now = time.monotonic()
        instant = 1 / max(now - self.last, 1e-6)
        self.fps = instant if not self.fps else .9 * self.fps + .1 * instant
        self.last = now
        new_alert = state.active and not self.was_active
        cleared = self.was_active and not state.active
        self.was_active = state.active
        draw_frame(frame, dets, self.roi, state, count, len(self.unique),
                   self.alert.threshold, self.fps, self.cfg["anchor"], self.cfg["show_ids"])
        ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 78])
        if not ok:
            return None
        return {"type": "frame", "image": base64.b64encode(jpg).decode("ascii"),
                "count": count, "unique_total": len(self.unique), "threshold": self.alert.threshold,
                "status": "ALERT" if state.active else "WARNING" if state.pending else "NORMAL",
                "fps": round(self.fps, 1), "timestamp": time.time(),
                "new_alert": new_alert, "cleared": cleared}
