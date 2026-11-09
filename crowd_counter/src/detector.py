"""YOLO11n person detection + ByteTrack tracking (via Ultralytics)."""
from dataclasses import dataclass

from ultralytics import YOLO

PERSON_CLASS_ID = 0  # COCO 'person'


@dataclass
class Detection:
    track_id: int
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float
    inside: bool = False

    def anchor_point(self, mode):
        cx = (self.x1 + self.x2) / 2
        cy = self.y2 if mode == "bottom" else (self.y1 + self.y2) / 2
        return cx, cy


class PersonTracker:
    def __init__(self, model_path, tracker_cfg, conf, iou, imgsz, device="auto"):
        self.model = YOLO(model_path)
        self.tracker_cfg = tracker_cfg
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.device = None if str(device).lower() == "auto" else device

    def track(self, frame):
        results = self.model.track(
            frame,
            persist=True,                 # keep track state between frames
            tracker=self.tracker_cfg,     # ByteTrack
            classes=[PERSON_CLASS_ID],    # people only
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False,
        )
        boxes = results[0].boxes
        if boxes is None or boxes.id is None:
            return []
        xyxy = boxes.xyxy.cpu().numpy().astype(int)
        ids = boxes.id.cpu().numpy().astype(int)
        confs = boxes.conf.cpu().numpy()
        return [
            Detection(int(i), int(b[0]), int(b[1]), int(b[2]), int(b[3]), float(c))
            for b, i, c in zip(xyxy, ids, confs)
        ]
