"""ROI (Region of Interest) polygon: load/save, point test, interactive drawing."""
import json
from pathlib import Path

import cv2
import numpy as np


class ROI:
    """Polygon stored as normalized (0..1) points, so it works at any resolution."""

    def __init__(self, points):
        self.points = np.asarray(points, dtype=np.float32)
        if len(self.points) < 3:
            raise ValueError("ROI needs at least 3 points")

    @classmethod
    def load(cls, path, default_points):
        path = Path(path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return cls(json.load(f)["points"])
            except Exception as e:  # corrupted file -> fall back
                print(f"[WARN] Could not read {path} ({e}); using default ROI.")
        return cls(default_points)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"points": self.points.round(4).tolist()}, f, indent=2)

    def polygon_px(self, w, h):
        return (self.points * np.array([w, h], dtype=np.float32)).astype(np.int32)

    def contains(self, point, w, h):
        poly = self.polygon_px(w, h).reshape(-1, 1, 2)
        return cv2.pointPolygonTest(poly, (float(point[0]), float(point[1])), False) >= 0


def select_roi_interactive(frame, window_name):
    """Freeze a frame and let the user click polygon points.

    Left click = add point | Right click = undo | C = clear
    Enter = confirm (min 3 points) | Esc = cancel
    Returns a normalized ROI or None if cancelled.
    """
    h, w = frame.shape[:2]
    pts = []

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            pts.append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN and pts:
            pts.pop()

    cv2.setMouseCallback(window_name, on_mouse)
    result = None
    while True:
        canvas = frame.copy()
        if len(pts) >= 2:
            cv2.polylines(canvas, [np.array(pts, np.int32)], len(pts) >= 3, (0, 255, 255), 2)
        for p in pts:
            cv2.circle(canvas, p, 5, (0, 0, 255), -1)
        msg = "ROI: L-click add | R-click undo | C clear | ENTER confirm | ESC cancel"
        cv2.rectangle(canvas, (0, 0), (w, 34), (0, 0, 0), -1)
        cv2.putText(canvas, msg, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(20) & 0xFF
        if key in (13, 10):
            if len(pts) >= 3:
                result = ROI(np.array(pts, np.float32) / np.array([w, h], np.float32))
                break
        elif key == 27:
            break
        elif key in (ord("c"), ord("C")):
            pts.clear()

    cv2.setMouseCallback(window_name, lambda *a: None)
    return result
