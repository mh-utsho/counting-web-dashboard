#!/usr/bin/env bash
# Ubuntu setup: system packages + virtualenv + Python dependencies
set -e

sudo apt update
sudo apt install -y python3 python3-venv python3-pip libgl1 libglib2.0-0 v4l-utils

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# No GPU (CPU only)? Uncomment the next line to install the smaller CPU-only PyTorch:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt

echo ""
echo "Setup complete. Now run:"
echo "  source .venv/bin/activate && python main.py"
