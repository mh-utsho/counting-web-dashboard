# CrowdWatch — Web People Counting & Crowd Alerts

A web dashboard built on the existing `crowd_counter` pipeline. It reuses YOLO11 person detection, ByteTrack tracking IDs, ROI counting and the original time-based alert state machine.

## Features
- FastAPI controls for starting/stopping the camera and changing the threshold.
- WebSocket `/ws/live` pushes annotated frames, live metrics and alert events.
- React Overview page shows the camera feed with instant alerts beside it.
- Separate `/alerts` page is a dedicated alert-only view that can be reused by another dashboard.
- No face recognition. ByteTrack IDs are temporary tracking identifiers for counting only.

## Architecture

```text
Webcam/video -> OpenCV -> YOLO11 -> ByteTrack -> ROI count
                                               |
                             count > threshold for duration
                                               |
                                        CrowdAlert
                                               |
                                            FastAPI
                                     REST + WebSocket
                                               |
                                           React UI
                                    /                 \
                              Overview              /alerts
                          camera + alerts           alert feed
```

## Project structure
```text
backend/app/main.py       FastAPI REST + WebSocket
backend/app/engine.py     Adapter for existing CV modules
frontend/src/App.jsx      Overview and alert pages
frontend/src/styles.css   Responsive UI
crowd_counter/            Original YOLO/ByteTrack pipeline
```

## Install (Ubuntu/Linux)

Backend:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
python -m pip install fastapi "uvicorn[standard]" ultralytics opencv-python
python -m pip install "fastapi[standard]"

python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install ultralytics lapx matplotlib pillow

--->backend/app python -m pip install opencv-python


if needed
{
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
}


```

Frontend in another terminal:
```bash
cd frontend
npm install
```

## Run

Backend:
```bash
cd backend/app
source .venv/bin/activate
fastapi dev main.py

{
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

```

Frontend:
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. Overview is `/`; the standalone Alert Center is `/alerts`; API documentation is `http://localhost:8000/docs`.

Click **Start** on the Overview page. Source `0` means the default webcam connected to the machine running FastAPI. A video file path must be accessible to that backend machine. On first run, Ultralytics may download the configured YOLO model if it is not already present.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/status` | Current metrics and camera status |
| GET | `/api/alerts` | Recent alert history |
| POST | `/api/camera/start` | Start; JSON `{"source":"0","threshold":3}` |
| POST | `/api/camera/stop` | Stop processing |
| PUT | `/api/settings/threshold` | Update; JSON `{"threshold":5}` |
| WS | `/ws/live` | Initial snapshot, frames, metrics and alert events |

The WebSocket sends a `snapshot` when a client connects. Each `frame` message includes the annotated JPEG (base64), current count, threshold and status. When a new alert begins, the same message includes a non-null `alert` object.

## Connect another dashboard to alerts

- Load recent events with `GET /api/alerts`.
- Subscribe to `/ws/live`.
- On each WebSocket `frame` message, check whether `alert` is non-null and display it.
- The dedicated React route `/alerts` demonstrates an alert-only page independent of the camera layout.

## Alert rule

The original rule is preserved: people count must be **greater than** the threshold continuously for `alert_duration` seconds. Default settings are in `crowd_counter/config.yaml`. Change the threshold from the Overview page.

## Production notes

- Alert history is currently in memory and is cleared when FastAPI restarts.
- This version supports one camera-processing loop in one FastAPI process. Do not run multiple Uvicorn workers against the same webcam.
- Before a multi-camera or multi-server deployment, add a camera registry, persistent alert storage (e.g. PostgreSQL), authentication/authorization, HTTPS/WSS and a shared event broker (e.g. Redis).
- The backend must run on a machine that can access the webcam or video file.
