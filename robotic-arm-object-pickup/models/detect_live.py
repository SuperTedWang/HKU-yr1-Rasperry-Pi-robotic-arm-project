import argparse
import platform
import time
from pathlib import Path

import cv2
from ultralytics import YOLO


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PT_MODEL = (
    SCRIPT_DIR
    / "block_training_results"
    / "exp1_cpu_overfitting_controlled"
    / "weights"
    / "best.pt"
)
DEFAULT_NCNN_MODEL = DEFAULT_PT_MODEL.with_name(f"{DEFAULT_PT_MODEL.stem}_ncnn_model")
PACKAGE_NCNN_MODEL = SCRIPT_DIR / "best_ncnn_model"

if PACKAGE_NCNN_MODEL.exists():
    DEFAULT_MODEL = PACKAGE_NCNN_MODEL
elif DEFAULT_NCNN_MODEL.exists():
    DEFAULT_MODEL = DEFAULT_NCNN_MODEL
else:
    DEFAULT_MODEL = DEFAULT_PT_MODEL


def parse_source(value: str):
    """Accept 0/1, usb0/usb1, file paths, or stream URLs."""
    text = str(value).strip()
    lower = text.lower()

    if text.isdigit():
        return int(text)

    if lower.startswith("usb") and lower[3:].isdigit():
        return int(lower[3:])

    return text


def open_camera(source, width: int, height: int):
    if isinstance(source, int) and platform.system().lower() == "linux":
        cap = cv2.VideoCapture(source, cv2.CAP_V4L2)
    else:
        cap = cv2.VideoCapture(source)

    if width > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height > 0:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    return cap


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run live block detection from a webcam or video source."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=str(DEFAULT_MODEL),
        help="Path to trained .pt file or exported *_ncnn_model directory.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Camera/video source. Examples: 0, 1, usb0, video.mp4, rtsp://...",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold.")
    parser.add_argument("--imgsz", type=int, default=320, help="Inference image size.")
    parser.add_argument("--width", type=int, default=640, help="Camera capture width.")
    parser.add_argument("--height", type=int, default=480, help="Camera capture height.")
    parser.add_argument("--device", type=str, default="cpu", help="Inference device.")
    parser.add_argument("--save", action="store_true", help="Save annotated output video.")
    parser.add_argument(
        "--save-dir",
        type=str,
        default=str(SCRIPT_DIR),
        help="Directory for saved videos and frames.",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run without cv2.imshow, useful over SSH/headless sessions.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Stop after this many frames. 0 means run until q/Ctrl+C.",
    )
    return parser


def main():
    args = build_parser().parse_args()

    model_path = Path(args.model).expanduser()
    if not model_path.exists():
        print(f"ERROR: Model not found: {model_path}")
        raise SystemExit(1)

    print(f"Loading model: {model_path}")
    model = YOLO(str(model_path))

    # Fusing only applies to native PyTorch weights, not exported NCNN folders.
    if model_path.is_file() and model_path.suffix.lower() == ".pt":
        try:
            model.fuse()
            print("Fused PyTorch model layers for CPU inference.")
        except Exception as exc:
            print(f"Model fuse skipped: {exc}")

    source = parse_source(args.source)
    cap = open_camera(source, args.width, args.height)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera/video source: {args.source}")
        print("Try --source 1, --source usb0, or check that /dev/video0 exists on Raspberry Pi.")
        raise SystemExit(1)

    save_dir = Path(args.save_dir).expanduser()
    save_dir.mkdir(parents=True, exist_ok=True)

    out = None
    if args.save:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out_path = save_dir / f"block_detection_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
        out = cv2.VideoWriter(str(out_path), fourcc, 20.0, (args.width, args.height))
        print(f"Saving video to: {out_path}")

    print("Starting live detection. Press 'q' to quit, 's' to save a frame, 'c' to toggle conf.")
    frame_count = 0
    start_time = time.time()
    current_conf = args.conf

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("ERROR: Failed to grab frame.")
                break

            frame_count += 1
            results = model.predict(
                source=frame,
                conf=current_conf,
                imgsz=args.imgsz,
                device=args.device,
                verbose=False,
                agnostic_nms=True,
            )

            annotated_frame = results[0].plot(
                font_size=12,
                line_width=2,
                boxes=True,
                conf=True,
                labels=True,
            )

            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0.0
            detections = len(results[0].boxes) if results[0].boxes is not None else 0

            cv2.putText(
                annotated_frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )
            cv2.putText(
                annotated_frame,
                f"Conf: {current_conf:.2f}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (200, 200, 255),
                2,
            )
            cv2.putText(
                annotated_frame,
                f"Blocks: {detections}",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 165, 255),
                2,
            )

            if out is not None:
                out.write(annotated_frame)

            if not args.no_display:
                cv2.imshow("Block Detection - Press q to quit", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("Exiting...")
                    break
                if key == ord("s"):
                    frame_path = save_dir / f"capture_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
                    cv2.imwrite(str(frame_path), annotated_frame)
                    print(f"Saved frame: {frame_path}")
                if key == ord("c"):
                    current_conf = 0.1 if current_conf > 0.2 else 0.4
                    print(f"Confidence threshold: {current_conf}")
            elif frame_count % 30 == 0:
                print(f"Frames: {frame_count} | FPS: {fps:.1f} | Blocks: {detections}")

            if args.max_frames and frame_count >= args.max_frames:
                break

    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        cap.release()
        if out is not None:
            out.release()
        if not args.no_display:
            cv2.destroyAllWindows()
        print("Cleanup complete.")


if __name__ == "__main__":
    main()
