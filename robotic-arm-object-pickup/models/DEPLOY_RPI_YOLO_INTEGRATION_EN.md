# Raspberry Pi YOLO Deployment and Robotic Arm Integration

This guide is only for deployment. It assumes the model has already been trained on the same-day/same-camera block setup and that the robotic arm center-point/grasping code already exists.

## Goal

Deploy the trained YOLO block detector to a Raspberry Pi, run it from a camera frame, extract the detected block center point, and pass that center point into the existing robotic arm pick-and-place code.

For this project, the recommended deployment format is **NCNN**, because it runs lighter than native PyTorch `.pt` weights on Raspberry Pi CPU.

## 1. Files Needed on the Training Laptop

On the training laptop, the project should contain:

```text
ENGG1101_YOLO_Model_v1/
  block_training_results/white_block_realdata_yolov8n/weights/best.pt
  export_ncnn.py
  detect_live.py
  requirements-rpi.txt
  RASPBERRY_PI_DEPLOY.md
```

If the final trained model is stored somewhere else, use that path with `--weights` in the export command.

## 2. Export the Model to NCNN

Open PowerShell on the training laptop:

```powershell
cd C:\Users\29454\Desktop\ENGG1101_YOLO_Model_v1
.\.venv\Scripts\Activate.ps1
pip install "ultralytics[export]"
python export_ncnn.py --weights .\block_training_results\white_block_realdata_yolov8n\weights\best.pt --imgsz 416 --package
```

This creates a deployment folder:

```text
deploy_pi/
  best_ncnn_model/
  detect_live.py
  requirements-rpi.txt
  RASPBERRY_PI_DEPLOY.md
```

Important: copy the whole `best_ncnn_model` folder, not just one file inside it.

## 3. Copy the Deployment Folder to Raspberry Pi

Use `scp` from the training laptop:

```powershell
scp -r .\deploy_pi pi@<RASPBERRY_PI_IP>:~/block_detector
```

Example:

```powershell
scp -r .\deploy_pi pi@192.168.1.23:~/block_detector
```

Or copy `deploy_pi/` with a USB drive and rename it to `block_detector` on the Raspberry Pi.

## 4. Install Raspberry Pi Dependencies

SSH into the Raspberry Pi:

```bash
ssh pi@<RASPBERRY_PI_IP>
```

Then run:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv
cd ~/block_detector
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements-rpi.txt
```

The `--system-site-packages` flag allows the virtual environment to use the system OpenCV package installed by `apt`.

## 5. Check the Camera

Connect the USB camera or Raspberry Pi camera, then run:

```bash
ls /dev/video*
```

Usually the first camera is `/dev/video0`, which means `--source 0`.

If `0` does not work, try:

```bash
python detect_live.py --model best_ncnn_model --source 1 --imgsz 416 --conf 0.25 --no-display --max-frames 30
```

## 6. Test YOLO Detection on Raspberry Pi

With display:

```bash
cd ~/block_detector
source .venv/bin/activate
python detect_live.py --model best_ncnn_model --source 0 --imgsz 416 --conf 0.25
```

Headless SSH mode:

```bash
python detect_live.py --model best_ncnn_model --source 0 --imgsz 416 --conf 0.25 --no-display --max-frames 100
```

Save an annotated video for debugging:

```bash
python detect_live.py --model best_ncnn_model --source 0 --imgsz 416 --conf 0.25 --save --no-display --max-frames 300
```

## 7. Integration With Existing Center-Point and Grasping Code

YOLO returns bounding boxes. The center point of the detected block is:

```python
center_x = (x1 + x2) / 2
center_y = (y1 + y2) / 2
```

OpenCV image coordinates use:

```text
origin: top-left corner
x: increases to the right
y: increases downward
```

Use the same camera resolution that was used during calibration. If the robotic arm calibration was done at `640x480`, keep:

```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```

Minimal integration example:

```python
import cv2
from ultralytics import YOLO

model = YOLO("best_ncnn_model")
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

CONF = 0.25
IMGSZ = 416

while True:
    ok, frame = cap.read()
    if not ok:
        continue

    results = model.predict(frame, imgsz=IMGSZ, conf=CONF, verbose=False)
    boxes = results[0].boxes

    if boxes is None or len(boxes) == 0:
        continue

    # Use the highest-confidence detection.
    best_index = boxes.conf.argmax().item()
    x1, y1, x2, y2 = boxes.xyxy[best_index].cpu().numpy()
    confidence = float(boxes.conf[best_index].cpu().numpy())

    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)

    # Connect this part to your existing code:
    # robot_x, robot_y = pixel_to_robot(center_x, center_y)
    # arm.pick(robot_x, robot_y)
    print(center_x, center_y, confidence)
```

## 8. Recommended Safety Logic Before Grasping

Before calling the robotic arm pick function, add these checks:

```text
1. Only grasp if exactly one valid block is detected, or choose the highest-confidence block.
2. Require confidence >= 0.25 or 0.30.
3. Require the center point to stay stable for 3-5 frames.
4. Require the center point to be inside the calibrated robot workspace.
5. Stop the arm if no block is detected.
```

Example stability rule:

```python
# If the detected center changes by less than 10 pixels for 5 frames,
# treat the detection as stable enough for grasping.
```

## 9. Tuning for the Demo Environment

If there are false detections:

```bash
python detect_live.py --model best_ncnn_model --source 0 --imgsz 416 --conf 0.40
```

If the model misses the block:

```bash
python detect_live.py --model best_ncnn_model --source 0 --imgsz 416 --conf 0.15
```

If inference is too slow:

```bash
python detect_live.py --model best_ncnn_model --source 0 --imgsz 320 --width 320 --height 240 --conf 0.25
```

If the robotic arm coordinate mapping becomes inaccurate after changing camera settings, redo the camera-to-robot calibration using the new resolution.

## 10. Final Demo Checklist

Before the final run:

```text
[ ] Raspberry Pi camera opens correctly.
[ ] YOLO detects the block in the same lighting/setup.
[ ] The printed center_x, center_y are near the visual center of the block.
[ ] Camera resolution matches the calibration resolution.
[ ] The center point is converted into robot coordinates correctly.
[ ] The robot arm can perform one dry run without closing the gripper.
[ ] The robot arm can perform one slow-speed grasp test.
[ ] Confidence threshold is saved in the final script.
```

For a same-day controlled demo, this setup should be achievable as long as the camera position, lighting, background, and object appearance stay close to the training images.
