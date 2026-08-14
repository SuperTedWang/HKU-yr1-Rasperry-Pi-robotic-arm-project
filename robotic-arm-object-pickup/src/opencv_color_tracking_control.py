import argparse
import time

import cv2
import numpy as np
import serial


def parse_hsv(value):
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("HSV values must use the format H,S,V.")
    return np.array(parts, dtype=np.uint8)


def parse_args():
    parser = argparse.ArgumentParser(
        description="OpenCV color tracking and robotic arm serial control."
    )
    parser.add_argument(
        "--serial-port",
        default="/dev/ttyUSB0",
        help="Serial port connected to the arm controller, for example /dev/ttyUSB0 or COM3.",
    )
    parser.add_argument("--baud-rate", type=int, default=9600)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--send-delay", type=float, default=0.5)
    parser.add_argument("--center-threshold", type=int, default=50)
    parser.add_argument("--detect-frames", type=int, default=3)
    parser.add_argument("--lock-frames", type=int, default=20)
    parser.add_argument("--lost-frames", type=int, default=15)
    parser.add_argument("--grab-duration", type=float, default=16.0)
    parser.add_argument("--lower-hsv", type=parse_hsv, default=parse_hsv("35,60,60"))
    parser.add_argument("--upper-hsv", type=parse_hsv, default=parse_hsv("85,255,255"))
    parser.add_argument("--min-area", type=float, default=500.0)
    parser.add_argument("--snapshot", default="tracking.jpg")
    parser.add_argument("--no-reset", action="store_true")
    return parser.parse_args()


def open_serial(port, baud_rate, no_reset):
    try:
        ser = serial.Serial(port, baud_rate, timeout=1)
        time.sleep(2)
        print("Serial connected.")
        if not no_reset:
            ser.write(b"RESET\n")
            time.sleep(3)
        return ser
    except Exception as exc:
        print(f"Serial connection failed: {exc}")
        return None


def detect_with_hsv(frame, lower_hsv, upper_hsv, min_area, center_threshold):
    frame_h, frame_w, _ = frame.shape
    center_x = frame_w // 2
    center_y = frame_h // 2

    detection = {
        "direction": "NONE",
        "error_x": 0,
        "error_y": 0,
    }

    blurred = cv2.GaussianBlur(frame, (7, 7), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return detection

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    if area < min_area:
        return detection

    x, y, w, h = cv2.boundingRect(contour)
    obj_center_x = x + w // 2
    obj_center_y = y + h // 2

    error_x = obj_center_x - center_x
    error_y = obj_center_y - center_y

    h_off = abs(error_x) > center_threshold
    v_off = abs(error_y) > center_threshold

    if h_off:
        direction = "LEFT" if error_x < 0 else "RIGHT"
    elif v_off:
        direction = "UP" if error_y < 0 else "DOWN"
    else:
        direction = "CENTER"

    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.circle(frame, (obj_center_x, obj_center_y), 6, (0, 0, 255), -1)
    cv2.drawContours(frame, [contour], -1, (255, 0, 0), 2)

    detection["direction"] = direction
    detection["error_x"] = error_x
    detection["error_y"] = error_y
    return detection


def read_controller_message(ser):
    if not ser or ser.in_waiting <= 0:
        return ""

    try:
        incoming = ser.read(ser.in_waiting).decode(errors="ignore")
        if incoming.strip():
            print(f"Controller: {incoming.strip()}")
        return incoming
    except Exception:
        return ""


def main():
    args = parse_args()
    ser = open_serial(args.serial_port, args.baud_rate, args.no_reset)
    cap = cv2.VideoCapture(args.camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {args.camera_index}.")

    locked_count = 0
    grab_sent = False
    grab_time = 0
    scanning = True
    scan_wait_until = 0
    scan_started = False
    scan_done = False
    object_found = False
    scan_detect_count = 0
    lost_count = 0
    last_send_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            detection = detect_with_hsv(
                frame,
                lower_hsv=args.lower_hsv,
                upper_hsv=args.upper_hsv,
                min_area=args.min_area,
                center_threshold=args.center_threshold,
            )
            direction = detection["direction"]
            error_x = detection["error_x"]
            error_y = detection["error_y"]

            incoming = read_controller_message(ser)
            if "SCAN_END" in incoming:
                scan_done = True
                scanning = False
                print("Sweep complete from controller; no object found.")

            now = time.time()
            print(
                "STATE >> "
                f"scanning:{scanning} | started:{scan_started} | done:{scan_done} | "
                f"found:{object_found} | grab:{grab_sent} | dir:{direction} | "
                f"err_x:{error_x} | err_y:{error_y}"
            )

            if ser and (now - last_send_time > args.send_delay):
                if grab_sent and (now - grab_time < args.grab_duration):
                    pass

                elif grab_sent and (now - grab_time >= args.grab_duration):
                    print("Grab sequence done, resetting for next patrol.")
                    locked_count = 0
                    grab_sent = False
                    scan_done = False
                    object_found = False
                    scanning = True
                    scan_started = False
                    scan_detect_count = 0
                    lost_count = 0

                elif scanning and not scan_done and not grab_sent:
                    if not scan_started:
                        ser.write(b"SCAN\n")
                        scan_started = True
                        scan_wait_until = now + 3.0
                        last_send_time = now
                        print("Sent: SCAN")

                    elif now < scan_wait_until:
                        pass

                    elif direction != "NONE" and direction != "":
                        scan_detect_count += 1
                        if scan_detect_count >= args.detect_frames:
                            scanning = False
                            object_found = True
                            lost_count = 0
                            print("Object found. Interrupting sweep.")
                            msg = f"ERR_X:{error_x},ERR_Y:{error_y}\n"
                            ser.write(msg.encode())
                            last_send_time = now
                            print(f"Sent: {msg.strip()}")

                elif object_found and not grab_sent and not scan_done:
                    if direction == "NONE" or direction == "":
                        lost_count += 1
                        print(f"Object lost... ({lost_count}/{args.lost_frames})")
                        if lost_count > args.lost_frames:
                            print("Object lost. Restarting scan.")
                            locked_count = 0
                            object_found = False
                            scanning = True
                            scan_started = False
                            scan_detect_count = 0
                            lost_count = 0
                    else:
                        lost_count = 0
                        if direction == "CENTER":
                            locked_count += 1
                            print(f"Locked. ({locked_count}/{args.lock_frames})")
                            if locked_count > args.lock_frames:
                                ser.write(b"GRAB\n")
                                print("Sent: GRAB")
                                grab_sent = True
                                grab_time = now
                        else:
                            locked_count = 0
                            msg = f"ERR_X:{error_x},ERR_Y:{error_y}\n"
                            ser.write(msg.encode())
                            print(f"Sent: {msg.strip()}")

                    last_send_time = now

            if args.snapshot:
                cv2.imwrite(args.snapshot, frame)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        if ser:
            ser.close()


if __name__ == "__main__":
    main()
