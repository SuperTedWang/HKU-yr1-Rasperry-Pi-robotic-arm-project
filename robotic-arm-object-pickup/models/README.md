# ENGG1101 YOLO Block Detector

This project contains Python source code for training, exporting, and running a YOLOv8 block detector for a robotic-arm workflow.

The detector is designed to identify one target class:

```text
white_block
```

## Recommended Files to Upload

If you only want to upload source code and documentation to GitHub, upload these files:

```text
README.md
prepare_block_dataset.py
train_blocks.py
export_ncnn.py
detect_live.py
block_data.yaml
requirements-rpi.txt
RASPBERRY_PI_DEPLOY.md
DEPLOY_RPI_YOLO_INTEGRATION_EN.md
```

Optional source file for robotic-arm integration:

```text
RPI_YOLO_DEPLOY_FLAT_PACKAGE/yolo_center_grasp_bridge.py
```

Do not upload these unless you specifically want to publish the dataset or model artifacts:

```text
.venv/
__pycache__/
train/
val/
block_dataset/
block_dataset_white_block/
block_training_results/
dataset_qc/
*.zip
*.pt
*.cache
```

## Python Dependencies

For training and local inference:

```bash
pip install ultralytics opencv-python pyyaml pillow numpy
```

For Raspberry Pi deployment, use:

```bash
pip install -r requirements-rpi.txt
```

## Dataset Format

The training script expects a YOLO-format dataset configured by `block_data.yaml`:

```text
block_dataset_white_block/
  train/images/
  train/labels/
  val/images/
  val/labels/
  classes.txt
```

Each label file should use YOLO bounding-box format:

```text
class_id x_center y_center width height
```

All coordinates must be normalized between `0` and `1`.

## Check Dataset

Before training, validate the image and label files:

```bash
python train_blocks.py --check-only
```

## Train

CPU training:

```bash
python train_blocks.py --epochs 120 --imgsz 416 --batch 4 --device cpu
```

GPU training:

```bash
python train_blocks.py --epochs 120 --imgsz 416 --batch 4 --device 0
```

Training outputs are saved under:

```text
block_training_results/
```

## Live Detection

Run webcam detection with a trained `.pt` model:

```bash
python detect_live.py --model path/to/best.pt --source 0 --imgsz 416 --conf 0.25
```

Headless test:

```bash
python detect_live.py --model path/to/best.pt --source 0 --imgsz 416 --conf 0.25 --no-display --max-frames 100
```

## Export to NCNN for Raspberry Pi

NCNN is recommended for Raspberry Pi CPU inference:

```bash
python export_ncnn.py --weights path/to/best.pt --imgsz 416 --package
```

See `RASPBERRY_PI_DEPLOY.md` and `DEPLOY_RPI_YOLO_INTEGRATION_EN.md` for deployment and robotic-arm integration details.

## Robotic Arm Center Point

YOLO returns bounding boxes:

```text
x1, y1, x2, y2
```

The object center point is:

```python
center_x = int((x1 + x2) / 2)
center_y = int((y1 + y2) / 2)
```

Use this center point with your camera-to-robot calibration before calling the robotic-arm pick function.
