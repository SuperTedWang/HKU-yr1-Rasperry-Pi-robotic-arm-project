# Serial Protocol

The vision program sends simple newline-terminated text commands to the robotic arm controller.

## Commands Sent By The Vision Program

| Command | Meaning |
| --- | --- |
| `RESET` | Reset the arm before starting the main loop. |
| `SCAN` | Ask the controller to start a sweeping scan. |
| `ERR_X:<value>,ERR_Y:<value>` | Send horizontal and vertical image error from the camera frame center. |
| `GRAB` | Trigger the pickup sequence once the object is centered for enough frames. |

## Messages Sent By The Controller

| Message | Meaning |
| --- | --- |
| `SCAN_END` | The scan finished without a valid object detection. |

## Control Logic

1. The vision program resets the controller.
2. The program sends `SCAN`.
3. If an object is detected for enough consecutive frames, the scan is interrupted.
4. The program sends `ERR_X` and `ERR_Y` until the object is centered.
5. Once the object is centered for enough frames, the program sends `GRAB`.
6. After the grab sequence duration, the system resets to scanning mode.
