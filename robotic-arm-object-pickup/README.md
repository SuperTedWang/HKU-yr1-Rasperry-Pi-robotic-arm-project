# Robotic Arm Object Pickup

Vision-guided robotic arm project for detecting an object, aligning the arm, and sending a grab command through a serial link.

This project was developed as a first-year engineering project. The original plan was to use a YOLO model for object detection and inverse kinematics for path planning. During testing, YOLO accuracy was not reliable enough for the available camera setup and training data, so the final workflow moved toward an OpenCV-based detection pipeline for simpler and more controllable object tracking.

## Features

- Camera-based object detection and tracking
- Robotic arm scanning state machine
- Serial communication with the arm controller
- Alignment commands using image-space error values
- Grab command once the object is centered and stable
- YOLO experiment script and OpenCV color-tracking script

## System Architecture

```text
Camera
  -> Vision detection
  -> Image error calculation
  -> Control state machine
  -> Serial commands
  -> ESP32 / Raspberry Pi / arm controller
  -> Robotic arm movement and gripper action
```

## Repository Structure

```text
robotic-arm-object-pickup/
├─ README.md
├─ requirements.txt
├─ .gitignore
├─ .gitattributes
├─ src/
│  ├─ yolo_tracking_control.py
│  └─ opencv_color_tracking_control.py
├─ models/
│  └─ README.md
├─ docs/
│  ├─ github-upload-guide.zh.md
│  ├─ release-checklist.zh.md
│  └─ serial-protocol.md
├─ hardware/
│  └─ README.md
└─ media/
   └─ README.md
```

## Hardware

Document your final hardware setup in `hardware/README.md`. A typical setup includes:

- Robotic arm frame
- Servo motors or stepper motors
- Gripper
- Camera
- ESP32 / Arduino / Raspberry Pi controller
- External power supply

## Software Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running the OpenCV Version

Use this version if the target object can be separated by color or simple visual features. Tune the HSV range for your object and lighting.

```bash
python src/opencv_color_tracking_control.py \
  --serial-port /dev/ttyUSB0 \
  --camera-index 0 \
  --lower-hsv 35,60,60 \
  --upper-hsv 85,255,255
```

On Windows, replace the serial port with something like `COM3`:

```powershell
python src\opencv_color_tracking_control.py --serial-port COM3 --camera-index 0
```

## Running the YOLO Experiment

Place the YOLO model weights under `models/ENGG1101_YOLO_MODEL_v1/`, then run:

```bash
python src/yolo_tracking_control.py \
  --model models/ENGG1101_YOLO_MODEL_v1/my_model.pt \
  --serial-port /dev/ttyUSB0 \
  --camera-index 0
```

## Model Files

GitHub blocks normal files larger than 100 MB. If the YOLO `.pt` file is large, use Git LFS:

```bash
git lfs install
git lfs track "*.pt"
git add .gitattributes models/
```

If Git LFS is not available, upload the model file as a GitHub Release asset and describe where to download it in `models/README.md`.

## Serial Commands

The vision program communicates with the arm controller using simple text commands:

- `RESET`: reset the arm before starting
- `SCAN`: start scanning for an object
- `ERR_X:<value>,ERR_Y:<value>`: send image-space alignment error
- `GRAB`: grab the object once it is centered
- `SCAN_END`: sent by the controller when the scan finishes without finding an object

More detail is available in `docs/serial-protocol.md`.

## Known Limitations

- YOLO performance depends heavily on training data quality, camera angle, and lighting.
- HSV color tracking is easier to tune but less general than object detection.
- The current controller sends image error values rather than full 3D coordinates.
- Inverse kinematics path planning was part of the original design direction but is not included in the current provided code.

## Contributors

Add the project team members here after getting permission from everyone.

## License

No open-source license has been selected yet. Before making the repository public, agree with all team members whether to use MIT, Apache-2.0, GPL, or keep all rights reserved.
