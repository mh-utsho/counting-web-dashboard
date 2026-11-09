"""Drawing: ROI, boxes, HUD, alert banner."""
import time

import cv2
import numpy as np

GREEN = (0, 200, 0)
RED = (0, 0, 255)
ORANGE = (0, 165, 255)
GRAY = (160, 160, 160)
WHITE = (255, 255, 255)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def _text(img, s, org, scale=0.6, color=WHITE, thick=1):
    cv2.putText(img, s, org, FONT, scale, color, thick, cv2.LINE_AA)


def draw_frame(frame, dets, roi, state, count, unique_total, threshold, fps, anchor, show_ids=True):
    h, w = frame.shape[:2]
    poly = roi.polygon_px(w, h)
    roi_color = RED if state.active else GREEN

    # ROI fill + outline
    overlay = frame.copy()
    cv2.fillPoly(overlay, [poly], roi_color)
    cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
    cv2.polylines(frame, [poly], True, roi_color, 2)

    # Detections
    for d in dets:
        color = roi_color if d.inside else GRAY
        cv2.rectangle(frame, (d.x1, d.y1), (d.x2, d.y2), color, 2)
        ax, ay = d.anchor_point(anchor)
        cv2.circle(frame, (int(ax), int(ay)), 4, color, -1)
        if show_ids:
            _text(frame, f"ID {d.track_id}", (d.x1, max(d.y1 - 6, 14)), 0.5, color, 1)

    # HUD panel
    cv2.rectangle(frame, (8, 8), (310, 138), (0, 0, 0), -1)
    _text(frame, f"In ROI    : {count}", (18, 34), 0.7, WHITE, 2)
    _text(frame, f"Threshold : {threshold}", (18, 60), 0.6)
    _text(frame, f"Unique IDs: {unique_total}", (18, 84), 0.6)
    _text(frame, f"FPS       : {fps:.1f}", (18, 108), 0.6)
    status, scol = ("ALERT", RED) if state.active else (("WARNING", ORANGE) if state.pending else ("NORMAL", GREEN))
    _text(frame, f"Status    : {status}", (18, 130), 0.6, scol, 2)

    # Timer bar while waiting for the 2-second confirmation
    if state.pending:
        frac = min(state.elapsed / state.duration, 1.0)
        cv2.rectangle(frame, (320, 14), (520, 34), (0, 0, 0), -1)
        cv2.rectangle(frame, (322, 16), (322 + int(196 * frac), 32), ORANGE, -1)
        _text(frame, f"{state.elapsed:.1f}/{state.duration:.1f}s", (528, 31), 0.55, ORANGE, 1)

    # Alert banner + blinking border
    if state.active:
        if int(time.time() * 2) % 2 == 0:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), RED, 10)
        text = f"CROWD ALERT!  {count} people (limit {threshold})"
        (tw, th), _ = cv2.getTextSize(text, FONT, 0.9, 2)
        x = (w - tw) // 2
        cv2.rectangle(frame, (x - 15, h - 70), (x + tw + 15, h - 20), (0, 0, 0), -1)
        _text(frame, text, (x, h - 36), 0.9, RED, 2)

    _text(frame, "q:quit  r:ROI  +/-:threshold  s:screenshot", (10, h - 8), 0.45, GRAY, 1)
    return frame
