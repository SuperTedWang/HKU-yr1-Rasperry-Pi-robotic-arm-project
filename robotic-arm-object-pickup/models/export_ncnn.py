import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_WEIGHTS = (
    SCRIPT_DIR
    / "block_training_results"
    / "white_block_realdata_yolov8n"
    / "weights"
    / "best.pt"
)
DEFAULT_PACKAGE_DIR = SCRIPT_DIR / "deploy_pi"


def build_parser():
    parser = argparse.ArgumentParser(
        description="Export the trained block detector to NCNN for Raspberry Pi deployment."
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=str(DEFAULT_WEIGHTS),
        help="Path to the trained .pt weights.",
    )
    parser.add_argument("--imgsz", type=int, default=416, help="Export image size.")
    parser.add_argument("--device", type=str, default="cpu", help="Export device.")
    parser.add_argument(
        "--package",
        action="store_true",
        help="Copy the exported model and runtime files into deploy_pi/.",
    )
    parser.add_argument(
        "--package-dir",
        type=str,
        default=str(DEFAULT_PACKAGE_DIR),
        help="Deployment package directory used with --package.",
    )
    return parser


def copy_runtime_files(exported_model: Path, package_dir: Path):
    package_dir.mkdir(parents=True, exist_ok=True)

    target_model = package_dir / exported_model.name
    if target_model.exists():
        shutil.rmtree(target_model)
    shutil.copytree(exported_model, target_model)

    for name in ("detect_live.py", "requirements-rpi.txt", "RASPBERRY_PI_DEPLOY.md"):
        src = SCRIPT_DIR / name
        if src.exists():
            shutil.copy2(src, package_dir / name)

    return target_model


def main():
    args = build_parser().parse_args()
    weights = Path(args.weights).expanduser().resolve()

    if not weights.exists():
        print(f"ERROR: Weights not found: {weights}")
        raise SystemExit(1)

    print(f"Exporting NCNN model from: {weights}")
    model = YOLO(str(weights))
    exported = Path(model.export(format="ncnn", imgsz=args.imgsz, device=args.device)).resolve()
    print(f"NCNN export complete: {exported}")

    if args.package:
        package_dir = Path(args.package_dir).expanduser().resolve()
        target_model = copy_runtime_files(exported, package_dir)
        print(f"Deployment package created: {package_dir}")
        print(f"Packaged model: {target_model}")


if __name__ == "__main__":
    main()
