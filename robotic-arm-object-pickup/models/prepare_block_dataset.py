import argparse
import csv
import random
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont, ImageOps


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = Path.home() / "Desktop" / "Yolo dataset" / "images"
DEFAULT_OUTPUT = SCRIPT_DIR / "block_dataset_white_block"
DEFAULT_YAML = SCRIPT_DIR / "block_data.yaml"
DEFAULT_QC = SCRIPT_DIR / "dataset_qc"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def list_images(source: Path) -> list[Path]:
    return sorted(
        p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )


def read_rgb(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def red_object_box(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Return an expanded xyxy box around a red/white block-like object."""
    rgb = np.array(image)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    lower_red_a = np.array([0, 55, 45])
    upper_red_a = np.array([14, 255, 255])
    lower_red_b = np.array([165, 55, 45])
    upper_red_b = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lower_red_a, upper_red_a) | cv2.inRange(
        hsv, lower_red_b, upper_red_b
    )

    kernel = np.ones((13, 13), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    height, width = rgb.shape[:2]
    min_area = max(500, int(width * height * 0.00025))
    boxes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w < 20 or h < 20:
            continue
        boxes.append((x, y, x + w, y + h, area))

    if not boxes:
        return None

    # Use the largest red region. It normally corresponds to the block body.
    x1, y1, x2, y2, _ = max(boxes, key=lambda item: item[4])
    box_w = x2 - x1
    box_h = y2 - y1

    # Expand to include the white end caps and some perspective blur/shadow.
    pad_x = int(max(18, box_w * 0.22))
    pad_y = int(max(18, box_h * 0.22))
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(width - 1, x2 + pad_x)
    y2 = min(height - 1, y2 + pad_y)

    if (x2 - x1) * (y2 - y1) < min_area:
        return None
    return x1, y1, x2, y2


def to_yolo(box: tuple[int, int, int, int], width: int, height: int) -> str:
    x1, y1, x2, y2 = box
    x_center = ((x1 + x2) / 2) / width
    y_center = ((y1 + y2) / 2) / height
    norm_w = (x2 - x1) / width
    norm_h = (y2 - y1) / height
    values = [0, x_center, y_center, norm_w, norm_h]
    return f"{values[0]} {values[1]:.6f} {values[2]:.6f} {values[3]:.6f} {values[4]:.6f}\n"


def split_images(images: list[Path], val_ratio: float, seed: int) -> tuple[list[Path], list[Path]]:
    shuffled = images[:]
    random.Random(seed).shuffle(shuffled)
    val_count = max(1, round(len(shuffled) * val_ratio)) if len(shuffled) > 1 else 0
    val = sorted(shuffled[:val_count])
    train = sorted(shuffled[val_count:])
    return train, val


def reset_output(output: Path) -> None:
    resolved = output.resolve()
    workspace = SCRIPT_DIR.resolve()
    if workspace not in resolved.parents and resolved != workspace:
        raise ValueError(f"Refusing to reset output outside workspace: {resolved}")
    if output.exists():
        shutil.rmtree(output)
    for split in ("train", "val"):
        (output / split / "images").mkdir(parents=True, exist_ok=True)
        (output / split / "labels").mkdir(parents=True, exist_ok=True)


def draw_preview_cell(
    image_path: Path,
    box: tuple[int, int, int, int] | None,
    label: str,
    size: tuple[int, int],
) -> Image.Image:
    image = read_rgb(image_path)
    original_w, original_h = image.size
    image.thumbnail(size)
    canvas = Image.new("RGB", size, (245, 245, 245))
    offset = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
    canvas.paste(image, offset)

    draw = ImageDraw.Draw(canvas)
    if box is not None:
        scale_x = image.width / original_w
        scale_y = image.height / original_h
        x1, y1, x2, y2 = box
        rect = [
            offset[0] + int(x1 * scale_x),
            offset[1] + int(y1 * scale_y),
            offset[0] + int(x2 * scale_x),
            offset[1] + int(y2 * scale_y),
        ]
        draw.rectangle(rect, outline=(255, 40, 40), width=4)
    draw.rectangle([0, 0, size[0] - 1, 28], fill=(20, 20, 20))
    draw.text((8, 7), label, fill=(255, 255, 255))
    return canvas


def write_preview(qc_dir: Path, rows: list[dict[str, str]], source_lookup: dict[str, Path]) -> Path:
    qc_dir.mkdir(parents=True, exist_ok=True)
    cell_size = (420, 240)
    cols = 3
    cells = []
    for row in rows:
        source = source_lookup[row["image"]]
        box = None
        if row["status"] == "labeled":
            box = tuple(int(float(row[key])) for key in ("x1", "y1", "x2", "y2"))
        label = f"{row['split']}: {row['image']} [{row['status']}]"
        cells.append(draw_preview_cell(source, box, label, cell_size))

    total_rows = int(np.ceil(len(cells) / cols))
    sheet = Image.new("RGB", (cols * cell_size[0], total_rows * cell_size[1]), (235, 235, 235))
    for idx, cell in enumerate(cells):
        x = (idx % cols) * cell_size[0]
        y = (idx // cols) * cell_size[1]
        sheet.paste(cell, (x, y))

    preview_path = qc_dir / "autolabel_preview.jpg"
    sheet.save(preview_path, quality=92)
    return preview_path


def prepare_dataset(args: argparse.Namespace) -> None:
    source = args.source.resolve()
    output = args.output.resolve()
    data_yaml = args.data_yaml.resolve()
    qc_dir = args.qc_dir.resolve()

    images = list_images(source)
    if not images:
        raise FileNotFoundError(f"No images found in {source}")

    reset_output(output)
    train, val = split_images(images, args.val_ratio, args.seed)
    split_map = {path: "train" for path in train}
    split_map.update({path: "val" for path in val})

    rows: list[dict[str, str]] = []
    source_lookup: dict[str, Path] = {}
    missing_labels: list[Path] = []

    for image_path in sorted(split_map):
        split = split_map[image_path]
        target_name = image_path.name
        target_image = output / split / "images" / target_name
        target_label = output / split / "labels" / f"{image_path.stem}.txt"

        image = read_rgb(image_path)
        image.save(target_image, quality=95)
        width, height = image.size

        box = red_object_box(image) if args.autolabel_red_object else None
        status = "labeled" if box else "missing_label"
        if box:
            target_label.write_text(to_yolo(box, width, height), encoding="utf-8")
        else:
            target_label.write_text("", encoding="utf-8")
            missing_labels.append(image_path)

        row = {
            "image": target_name,
            "split": split,
            "status": status,
            "width": str(width),
            "height": str(height),
            "x1": "",
            "y1": "",
            "x2": "",
            "y2": "",
        }
        if box:
            row.update({key: str(value) for key, value in zip(("x1", "y1", "x2", "y2"), box)})
        rows.append(row)
        source_lookup[target_name] = image_path

    classes_path = output / "classes.txt"
    classes_path.write_text(f"{args.class_name}\n", encoding="utf-8")

    data = {
        "path": str(output),
        "train": "train/images",
        "val": "val/images",
        "nc": 1,
        "names": [args.class_name],
    }
    data_yaml.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    qc_dir.mkdir(parents=True, exist_ok=True)
    report_path = qc_dir / "annotation_report.csv"
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["image", "split", "status", "width", "height", "x1", "y1", "x2", "y2"],
        )
        writer.writeheader()
        writer.writerows(rows)

    preview_path = write_preview(qc_dir, rows, source_lookup)

    print(f"Source images: {len(images)}")
    print(f"Train images:  {len(train)}")
    print(f"Val images:    {len(val)}")
    print(f"Output:        {output}")
    print(f"YAML:          {data_yaml}")
    print(f"Classes:       {classes_path}")
    print(f"QC report:     {report_path}")
    print(f"Preview:       {preview_path}")
    if missing_labels:
        print("Images needing manual labels:")
        for path in missing_labels:
            print(f"  {path.name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a YOLO detection dataset for the robotic arm block model."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--data-yaml", type=Path, default=DEFAULT_YAML)
    parser.add_argument("--qc-dir", type=Path, default=DEFAULT_QC)
    parser.add_argument("--class-name", default="white_block")
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=1101)
    parser.add_argument(
        "--autolabel-red-object",
        action="store_true",
        help="Create first-pass labels from the red object body and expand around it.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    prepare_dataset(parse_args())
