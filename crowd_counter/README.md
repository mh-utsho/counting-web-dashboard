# 👥 People Counting & Crowd Threshold Alert

Detect people from a laptop webcam (or a video file) with **YOLO11n**, track them with **ByteTrack**, count how many are inside a **Region of Interest (ROI)**, and raise a **CROWD ALERT** when the count stays **above a threshold for 2 seconds**.

## Features
- YOLO11n person detection (COCO `person` class only) + ByteTrack (persistent ID per person)
- Polygon ROI, drawn with the mouse at runtime and saved to `roi.json`
- Live count inside the ROI plus total unique IDs seen in the ROI
- Alert fires when `count > threshold` continuously for 2 seconds (time-based, independent of FPS)
- Orange progress bar (WARNING) while waiting for the 2 seconds, then red blinking border and banner (ALERT)
- Short clear delay when the crowd drops, to prevent flickering
- Change the threshold live (`+` / `-`) and save screenshots (`s`)

## Folder structure
```
crowd_counter/
├── main.py              # entry point (main loop)
├── config.yaml          # all settings in one place
├── requirements.txt
├── setup_ubuntu.sh      # one-command Ubuntu setup
├── roi.json             # (auto-created) saved ROI after you draw one
├── trackers/
│   └── bytetrack.yaml   # ByteTrack tuning
├── src/
│   ├── config.py        # config loading + defaults
│   ├── detector.py      # YOLO11n + ByteTrack wrapper
│   ├── roi.py           # ROI polygon, point-in-polygon, mouse drawing
│   ├── alert.py         # threshold + 2-second state machine
│   └── visualizer.py    # boxes, ROI, HUD, alert banner
└── output/              # screenshots are saved here
```

## Ubuntu setup
```bash
cd crowd_counter
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh
```
Or manually:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libgl1 libglib2.0-0 v4l-utils
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
> No GPU? To keep the download small, run this **before** `pip install -r requirements.txt`:
> `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`

## How to run
```bash
source .venv/bin/activate
python main.py                          # webcam, settings from config.yaml
python main.py --source 1               # a different camera
python main.py --source test.mp4        # a video file
python main.py --threshold 5 --duration 2
python main.py --conf 0.45
python main.py --reset-roi              # delete the saved ROI, go back to default
```
On first run `yolo11n.pt` is downloaded automatically (internet required). Run from the project folder.

### Keyboard shortcuts
| Key | Action |
|-----|--------|
| `q` / `Esc` | Quit |
| `r` | Draw a new ROI |
| `+` / `-` | Raise / lower the threshold (live) |
| `s` | Save a screenshot to `output/` |

## Setting the threshold
The rule is `count > threshold`, i.e. "more than N people in the ROI".

1. **Permanently:** edit `threshold: 3` in `config.yaml`.
2. **For one run:** `python main.py --threshold 5`
3. **While running:** press `+` / `-` (does not modify the config file).

To change the 2-second delay, edit `alert_duration: 2.0` (or use `--duration 3`).
To change how long the alert lingers after the crowd drops, edit `clear_delay: 0.5`.

**Testing tip:** if you are alone in front of the webcam, use `--threshold 0`. The alert will fire as soon as you stay in the ROI for 2 seconds.

## Changing the ROI
**Method 1 – with the mouse (easiest):** press `r` while running. The frame freezes:
- **Left click** = add a point, **Right click** = undo last point, `c` = clear all
- **Enter** = confirm (at least 3 points), **Esc** = cancel

The ROI is saved immediately to `roi.json` and is reused on the next run.

**Method 2 – by hand:** edit `default_roi` in `config.yaml` (or `points` in `roi.json`). Values are normalized `[x, y]` between `0.0` and `1.0`, so they stay valid at any resolution.
```yaml
default_roi:
  - [0.10, 0.10]   # top-left
  - [0.90, 0.10]   # top-right
  - [0.90, 0.90]   # bottom-right
  - [0.10, 0.90]   # bottom-left
```
> If `roi.json` exists it takes priority. To return to the default, use `--reset-roi` or delete the file.

**Which point decides "inside the ROI":** `anchor: center` (middle of the box, best for webcams) or `anchor: bottom` (bottom-center, near the feet, best for CCTV / elevated cameras).

## Performance tips
- Slow CPU: set `imgsz: 480` or `416`, and `frame_width/height: 640/480`
- Too many false detections: raise `conf` (0.45–0.5). Missing people: lower it (0.25–0.3)
- IDs changing too often: increase `track_buffer` in `trackers/bytetrack.yaml` (e.g. 60)
- Have a GPU: set `device: 0`

## Troubleshooting
| Problem | Fix |
|---------|-----|
| `Could not open video source` | Run `v4l2-ctl --list-devices` to find the index; try `--source 1`; close other apps using the camera (Zoom, Cheese) |
| `Permission denied /dev/video0` | `sudo usermod -aG video $USER`, then log out and back in |
| Window does not open (Wayland / SSH) | Run in a local desktop session; over SSH use `ssh -X` |
| `libGL.so.1` error | `sudo apt install -y libgl1 libglib2.0-0` |
| `lap`-related error | `pip install lapx` |

## Pipeline
```
Webcam → YOLO11n (person) → ByteTrack (IDs) → ROI check → count
      → count > threshold for 2 s continuously → CROWD ALERT
```
