import argparse
import csv
from pathlib import Path

import yaml
from ultralytics import YOLO


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_YAML = SCRIPT_DIR / "block_data.yaml"
RESULTS_DIR = SCRIPT_DIR / "block_training_results"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def image_files(path: Path) -> list[Path]:
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def validate_label_file(label_path: Path, class_count: int) -> list[str]:
    issues: list[str] = []
    text = label_path.read_text(encoding="utf-8").strip()
    if not text:
        issues.append("empty label")
        return issues

    for line_number, line in enumerate(text.splitlines(), start=1):
        parts = line.split()
        if len(parts) != 5:
            issues.append(f"line {line_number}: expected 5 values")
            continue
        try:
            class_id = int(float(parts[0]))
            values = [float(v) for v in parts[1:]]
        except ValueError:
            issues.append(f"line {line_number}: non-numeric value")
            continue
        if class_id < 0 or class_id >= class_count:
            issues.append(f"line {line_number}: class id {class_id} outside 0..{class_count - 1}")
        if any(v < 0.0 or v > 1.0 for v in values):
            issues.append(f"line {line_number}: bbox values must be normalized 0..1")
        if values[2] <= 0.0 or values[3] <= 0.0:
            issues.append(f"line {line_number}: bbox width/height must be positive")
    return issues


def validate_dataset(data_yaml: Path) -> dict[str, int]:
    if not data_yaml.exists():
        raise FileNotFoundError(f"Missing data yaml: {data_yaml}")

    config = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    root = Path(config["path"])
    class_names = config["names"]
    class_count = int(config["nc"])

    if class_count != len(class_names):
        raise ValueError("nc does not match names length in data yaml")

    summary: dict[str, int] = {}
    all_issues: list[str] = []
    for split in ("train", "val"):
        image_dir = root / config[split]
        label_dir = image_dir.parent / "labels"
        images = image_files(image_dir)
        labels = sorted(label_dir.glob("*.txt"))
        summary[f"{split}_images"] = len(images)
        summary[f"{split}_labels"] = len(labels)

        if not images:
            all_issues.append(f"{split}: no images found in {image_dir}")

        for image in images:
            label = label_dir / f"{image.stem}.txt"
            if not label.exists():
                all_issues.append(f"{split}: missing label for {image.name}")
                continue
            for issue in validate_label_file(label, class_count):
                all_issues.append(f"{split}/{label.name}: {issue}")

    print("Dataset check")
    print(f"  root:  {root}")
    print(f"  names: {class_names}")
    print(f"  train: {summary['train_images']} images, {summary['train_labels']} labels")
    print(f"  val:   {summary['val_images']} images, {summary['val_labels']} labels")

    if all_issues:
        print("\nIssues to review before a serious training run:")
        for issue in all_issues[:30]:
            print(f"  - {issue}")
        if len(all_issues) > 30:
            print(f"  - ... {len(all_issues) - 30} more")
        raise ValueError("Dataset validation failed")

    return summary


def find_column(fieldnames: list[str], needle: str) -> str | None:
    for fieldname in fieldnames:
        if needle in fieldname.strip():
            return fieldname
    return None


def diagnose_fit(save_dir: Path) -> None:
    results_csv = save_dir / "results.csv"
    if not results_csv.exists():
        print("No results.csv found; skipping fit diagnostic.")
        return

    with results_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if not rows:
        print("results.csv is empty; skipping fit diagnostic.")
        return

    train_box = find_column(fieldnames, "train/box_loss")
    val_box = find_column(fieldnames, "val/box_loss")
    map50 = find_column(fieldnames, "metrics/mAP50(B)")
    map5095 = find_column(fieldnames, "metrics/mAP50-95(B)")

    print("\nFit diagnostic")
    last = rows[-1]
    if map50:
        print(f"  final mAP50:    {float(last[map50]):.4f}")
    if map5095:
        print(f"  final mAP50-95: {float(last[map5095]):.4f}")

    if not train_box or not val_box:
        print("  loss columns not found")
        return

    recent = rows[-10:] if len(rows) >= 10 else rows
    gaps = [float(row[val_box]) - float(row[train_box]) for row in recent]
    avg_gap = sum(gaps) / len(gaps)
    print(f"  final train box loss: {float(last[train_box]):.4f}")
    print(f"  final val box loss:   {float(last[val_box]):.4f}")
    print(f"  avg val-train gap:    {avg_gap:.4f}")

    if avg_gap > 0.5:
        print("  likely overfitting: add more real validation scenes and reduce epochs/model size")
    elif avg_gap < -0.15:
        print("  possible underfitting or noisy labels: inspect labels and consider more epochs")
    else:
        print("  train/val loss gap looks reasonable")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the robotic arm block YOLO model.")
    parser.add_argument("--data", type=Path, default=DATA_YAML)
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--patience", type=int, default=25)
    parser.add_argument("--name", default="white_block_realdata_yolov8n")
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_dataset(args.data)
    if args.check_only:
        return

    model = YOLO(args.model)
    results = model.train(
        data=str(args.data.resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=str(RESULTS_DIR),
        name=args.name,
        exist_ok=True,
        pretrained=True,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        patience=args.patience,
        augment=True,
        mosaic=0.5,
        mixup=0.0,
        copy_paste=0.0,
        close_mosaic=10,
        hsv_h=0.005,
        hsv_s=0.25,
        hsv_v=0.35,
        degrees=20.0,
        translate=0.08,
        scale=0.35,
        shear=1.0,
        flipud=0.0,
        fliplr=0.5,
        cache=False,
        plots=True,
        val=True,
        verbose=True,
    )
    diagnose_fit(Path(results.save_dir))


if __name__ == "__main__":
    main()
