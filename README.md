# Vision-Guided Robotic Arm for Object Pickup

A first-year engineering team project at **The University of Hong Kong (HKU)** that integrates computer vision with a physical robotic arm for autonomous target detection, visual alignment, and object pickup.

The project explored two perception approaches:

1. a custom **YOLOv8 object detector**, and
2. an **OpenCV HSV-based color segmentation pipeline**.

The final system used camera feedback to estimate the target position in image space, calculate alignment errors, and send control commands to the robotic arm until the object was sufficiently centered for grasping.

---

## Project Overview

The objective of this project was to build a robotic arm system capable of:

* searching for a target object,
* detecting and locating the object using a camera,
* aligning the robotic arm with the target through visual feedback,
* and executing a grasp once the alignment became stable.

Rather than treating perception and robot control as separate tasks, the project focused on integrating them into a complete **perception-to-action pipeline**.

The final implementation performs **2D image-space feedback control**. It does not perform full 3D object pose estimation or learned robotic control.

---

## System Architecture

The overall system follows the pipeline:

```text
USB Camera
    ↓
Raspberry Pi
    ↓
Python Vision Pipeline
(YOLOv8 / OpenCV)
    ↓
Target Position Estimation
    ↓
Image-Space Error Calculation
    ↓
Rule-Based Control State Machine
    ↓
Serial Communication
    ↓
ESP32 / Robot Controller
    ↓
Servo Actuation
    ↓
Robotic Arm + Gripper
```

The camera continuously observes the workspace.

The vision program identifies the target and calculates the horizontal and vertical displacement between the target center and the center of the camera frame.

These errors are then converted into control commands and transmitted to the robot controller through serial communication.

---

## Perception Pipeline

### 1. YOLOv8 Object Detection

The first approach used a custom YOLOv8 detector trained to recognize the target block.

The pipeline was:

```text
Camera Frame
    ↓
YOLOv8 Inference
    ↓
Bounding Box Detection
    ↓
Target Center
    ↓
Image-Space Error
```

For each valid detection, the center of the bounding box was calculated as:

$$
x_c = \frac{x_1 + x_2}{2}
$$

$$
y_c = \frac{y_1 + y_2}{2}
$$

The displacement between the detected target and the center of the image was then calculated:

$$
e_x = x_c - x_{image}
$$

$$
e_y = y_c - y_{image}
$$

These errors were used as feedback for robotic-arm alignment.

---

## YOLO Dataset and Training

A single-class dataset was prepared for the target object.

The dataset preparation pipeline included:

* collecting images of the target block,
* generating or reviewing bounding-box annotations,
* splitting images into training and validation sets,
* generating a YOLO-compatible dataset configuration,
* and training a YOLOv8 model.

HSV-based image processing was also explored as an annotation aid during dataset preparation.

### Limitations of the YOLO approach

Although the YOLO detector was able to recognize the target object, its performance during the final real-world setup was not sufficiently robust under the available:

* training data,
* lighting conditions,
* camera viewpoints,
* and project time constraints.

The main issue was not simply whether the model could detect the object, but whether detection remained sufficiently stable for real-time robotic control.

Because unstable detections directly affected the control loop, a simpler perception method was selected for the final demonstration.

---

## 2. OpenCV Color-Based Detection

The second approach used **HSV color segmentation and contour detection** with OpenCV.

The processing pipeline was:

```text
Camera Frame
    ↓
BGR → HSV Conversion
    ↓
Color Thresholding
    ↓
Binary Mask
    ↓
Contour Detection
    ↓
Target Center
    ↓
Image-Space Error
```

For the controlled environment used in the project, this approach provided a more predictable target location estimate than the trained YOLO model.

This was therefore used as the more practical perception solution for the final system.

This decision was an engineering trade-off rather than a claim that OpenCV is generally superior to learned object detection. The OpenCV method relies strongly on controlled object color and environmental conditions, while a well-trained learned detector would be expected to generalize better to more complex scenes.

---

## Closed-Loop Visual Alignment

After detecting the target, the system compares its image-space position with the center of the camera frame.

Conceptually:

```text
Target left of image center
        ↓
Move / rotate toward target

Target right of image center
        ↓
Move / rotate toward target

Target vertically misaligned
        ↓
Adjust arm position

Target centered and stable
        ↓
Execute grasp
```

The system uses repeated camera observations rather than issuing a single movement command.

This creates a simple visual feedback loop:

$$
Observation_t
\rightarrow
Error_t
\rightarrow
Control_t
\rightarrow
Observation_{t+1}
$$

The controller is rule-based rather than learned.

---

## Control State Machine

The robotic system contains several operating states.

### Search / Scan

If no target is available, the robotic arm scans the workspace.

### Target Detection

When the target is detected repeatedly, the system transitions from searching to alignment.

### Alignment

The target center is compared with the image center.

The system sends horizontal and vertical error information to the robot controller.

### Target Loss

If the target cannot be detected for a predefined number of frames, the system returns to the searching state.

### Grasp

Once the target remains inside the alignment tolerance for a predefined number of frames, a grasp command is issued.

A simplified representation is:

```text
SCAN
  ↓
TARGET DETECTED
  ↓
ALIGN
  ↓
TARGET STABLE
  ↓
GRAB

If target is lost:
ALIGN → SCAN
```

---

## Serial Communication

The vision program communicates with the robot controller through serial communication.

Representative commands include:

```text
SCAN
ERR_X
ERR_Y
GRAB
```

The computer-vision program is responsible for perception and high-level decision logic, while the microcontroller and servo-control system execute the physical robot movements.

This separation allowed the vision and control components to be developed and tested independently before system integration.

---

## Hardware

The system includes:

* Raspberry Pi
* USB camera
* ESP32 / robot control electronics
* ST3215 servo motors
* robotic arm structure
* gripper / end effector
* external servo power supply
* serial communication interface

The Raspberry Pi runs the main Python vision pipeline, while lower-level actuator commands are handled by the robot-control hardware.

---

## Software

Main software components include:

* Python
* OpenCV
* Ultralytics YOLOv8
* NumPy
* PySerial

The project was developed and tested across both computer and Raspberry Pi environments.

---

## My Contribution

This was a team engineering project.

My primary contribution focused on the **computer-vision component of the robotic system**, including:

* preparing and testing the YOLO object-detection pipeline,
* working with the training dataset,
* training and evaluating the target-object detector,
* implementing and testing OpenCV-based color detection,
* comparing learned detection with the simpler HSV-based approach,
* and supporting integration of the perception output with the robotic-arm control pipeline.

One of the main technical lessons from my part of the project was that perception performance must be evaluated in the context of the complete physical system.

A detector that performs reasonably well on individual images may still be unsuitable for closed-loop robotic control if its outputs are unstable between frames.

---

## Engineering Decisions

### Why was OpenCV used in the final system?

The initial objective was to use a learned object detector for perception.

However, the project had limited training data and a fixed development timeline. During real-world testing, the YOLO detector was not sufficiently consistent for reliable closed-loop alignment.

Because the target object had a distinctive color and the operating environment was relatively controlled, HSV segmentation provided a simpler and more stable alternative.

The final choice was therefore based on **system reliability**, not model complexity.

---

## What the System Does Not Do

The current project should not be interpreted as a general-purpose robotic manipulation system.

In particular, it does not currently implement:

* full 3D object localization,
* 6-DoF object pose estimation,
* depth-camera perception,
* learned visuomotor policies,
* imitation learning,
* reinforcement learning,
* diffusion policies,
* vision-language-action models,
* or general-purpose task planning.

The control system is primarily based on **2D visual feedback and manually designed control logic**.

---

## Original Design Direction

An earlier design direction considered extending the system from 2D visual alignment toward:

```text
Camera
    ↓
3D Object Localization
    ↓
Target End-Effector Pose
    ↓
Inverse Kinematics
    ↓
Joint Configuration
    ↓
Trajectory Generation
    ↓
Robot Execution
```

However, full 3D localization and inverse-kinematics-based arm positioning were not integrated into the final implementation.

The completed system therefore focused on reliable perception-to-control integration within the available project scope.

---

## Results and Evaluation

The system successfully demonstrated the complete integration of:

```text
Visual Perception
        +
Feedback Calculation
        +
Robot Communication
        +
Physical Actuation
```

Both YOLO-based and OpenCV-based perception pipelines were tested during development.

The final demonstration used the OpenCV pipeline because it provided more stable perception under the controlled experimental setup.

A systematic quantitative benchmark of grasp success rate, perception precision/recall, and processing latency was not recorded during the original course project.

Therefore, this repository does not report numerical performance metrics that were not measured during the project.

This is an important limitation of the original experimental design.

---

## Key Lessons

### 1. Real-world robustness matters more than offline model performance

A vision model used for robotics must provide sufficiently stable predictions for downstream control.

Small perception errors can propagate into physical movement errors.

### 2. Machine-learning models are strongly affected by data quality

Training data diversity, camera viewpoints, lighting conditions, and annotation quality all affected the usefulness of the YOLO detector.

### 3. Perception and control should be evaluated together

Object detection cannot be evaluated only as an isolated computer-vision task when its output directly controls a physical robot.

### 4. Simpler methods can be appropriate engineering choices

For a constrained environment, a deterministic vision method may outperform a more complex model in reliability, development time, and interpretability.

### 5. 2D image feedback has clear limitations

Image-space alignment does not provide explicit information about object depth, orientation, robot kinematics, or collision constraints.

These limitations motivated my interest in more advanced robotic perception and robot learning.

---

## Future Work

This project provides a starting point for several possible extensions.

### 1. RGB-D Perception

Replace purely 2D target localization with depth-aware perception:

```text
RGB-D Camera
    ↓
3D Target Position
    ↓
Robot Coordinate Frame
```

### 2. Robot Kinematics

Integrate forward and inverse kinematics for explicit end-effector positioning.

### 3. Simulation

Reconstruct the robotic system in an environment such as:

* MuJoCo
* Isaac Sim
* PyBullet

This would allow manipulation algorithms to be tested more systematically.

### 4. Imitation Learning

Replace manually designed alignment rules with a learned policy:

$$
\pi(a_t | o_t)
$$

where the policy predicts robot actions directly from observations.

### 5. Learned Visuomotor Control

A future version could learn the mapping:

```text
Camera Observation
        ↓
Neural Policy
        ↓
Robot Action
```

rather than using handcrafted image-error thresholds.

### 6. Language-Conditioned Manipulation

A longer-term extension would introduce task instructions such as:

> Pick up the red block and place it in the target area.

This would require combining visual perception, task understanding, and robot action generation.

These extensions move beyond the scope of the original project and toward modern research in **robot learning and embodied AI**.

---

## Repository Structure

```text
vision-guided-robotic-arm/
├── README.md
└── robotic-arm-object-pickup/
    ├── src/
    │   ├── opencv_color_tracking_control.py
    │   └── yolo_tracking_control.py
    │
    ├── models/
    │   ├── block_data.yaml
    │   ├── prepare_block_dataset.py
    │   └── train_blocks.py
    │
    ├── docs/
    │   └── serial-protocol.md
    │
    ├── hardware/
    │   └── Hardware picture.jpeg
    │
    └── media/
        ├── demo_pick_and_place.mp4
        └── system_overview.jpg
```

The repository separates the main control code, YOLO training utilities, communication documentation, hardware reference material, and demonstration media into dedicated directories.


---

## Demo

Add the final system demonstration here.

Recommended format:

```markdown
![System Overview](media/system_overview.jpg)

[Watch the robotic-arm demonstration](media/demo_pick_and_place.mp4)
```

A short GIF showing:

```text
Search → Detect → Align → Grasp
```

is recommended for the top section of the repository.

---

## Project Context

This project was completed as a **first-year engineering team project at The University of Hong Kong**.

Its main purpose was to gain practical experience in integrating:

* computer vision,
* embedded computing,
* communication between subsystems,
* robotic control,
* and physical system testing.

The project later motivated my interest in moving from manually engineered perception-and-control pipelines toward **robot learning and embodied intelligence**.
