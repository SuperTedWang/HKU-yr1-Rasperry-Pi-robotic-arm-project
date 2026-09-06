# Model Evaluation Notes

This page summarizes only the metrics and observations that are available in this
repository. Values that were not measured are marked as unavailable instead of
being estimated.

## Summary

| Method | Accuracy / Success Rate | FPS | Failure Cases / Limitations |
| --- | --- | --- | --- |
| YOLOv8 | No classification accuracy is logged. The available detection run reports final `precision = 98.7%`, `recall = 100.0%`, `mAP50 = 99.5%`, and `mAP50-95 = 85.0%` in [`block_training_results/exp1_cpu_overfitting_controlled/results.csv`](block_training_results/exp1_cpu_overfitting_controlled/results.csv). These are detection metrics, not a general accuracy value. The validation split contains only 5 images, so the result should be treated as a small-validation-set result. | Not recorded. [`detect_live.py`](detect_live.py) computes and prints FPS at runtime, but this repository does not contain a saved FPS benchmark log. | No systematic failure-case benchmark was found. The deployment notes mention possible false detections, missed detections, slow inference, and sensitivity to the final camera/lighting/setup. The small validation set is the main evidence limitation. |
| OpenCV HSV | No validated accuracy or success-rate benchmark was found. The preprocessing report shows `25/25` images received generated labels in [`dataset_qc/annotation_report.csv`](dataset_qc/annotation_report.csv), but this is label-generation coverage, not verified detection accuracy against an independent ground truth. | Not recorded. No committed FPS benchmark for the HSV method was found. | No quantified failure rate was found. The implementation uses fixed HSV thresholds for red-object autolabeling in [`prepare_block_dataset.py`](prepare_block_dataset.py), so expected limitations are sensitivity to object color, lighting, shadows, and red-like background objects. |

## Data Sources Checked

- YOLO training metrics: [`block_training_results/exp1_cpu_overfitting_controlled/results.csv`](block_training_results/exp1_cpu_overfitting_controlled/results.csv)
- YOLO training settings: [`block_training_results/exp1_cpu_overfitting_controlled/args.yaml`](block_training_results/exp1_cpu_overfitting_controlled/args.yaml)
- Dataset configuration: [`block_data.yaml`](block_data.yaml)
- HSV autolabel report: [`dataset_qc/annotation_report.csv`](dataset_qc/annotation_report.csv)
- HSV autolabel implementation: [`prepare_block_dataset.py`](prepare_block_dataset.py)
- Runtime FPS display code: [`detect_live.py`](detect_live.py)
- Raspberry Pi deployment notes: [`RPI_YOLO_DEPLOY_FLAT_PACKAGE/MODEL_INFO.txt`](RPI_YOLO_DEPLOY_FLAT_PACKAGE/MODEL_INFO.txt)

## Important Notes

- The current YOLO dataset configuration uses one class, `white_block`, in
  [`block_data.yaml`](block_data.yaml). However, the exported NCNN metadata names
  class `0` as `block` in
  [`block_training_results/exp1_cpu_overfitting_controlled/weights/best_ncnn_model/metadata.yaml`](block_training_results/exp1_cpu_overfitting_controlled/weights/best_ncnn_model/metadata.yaml).
  This is a naming inconsistency, not evidence of a measured wrong-class failure.
- The active dataset configured by [`block_data.yaml`](block_data.yaml) contains
  20 training images and 5 validation images under `block_dataset_white_block/`.
  The validation set is too small to support a broad generalization claim.
- The repository also contains a Roboflow dataset note reporting 462 images in
  [`README.roboflow.txt`](README.roboflow.txt), but the active training config
  points to `block_dataset_white_block/`, not directly to the top-level
  `train/` folder. Therefore, the 462-image note should not be used as the
  validation basis for the YOLO metrics above.

## Recommended Report Wording

The YOLOv8 model achieved high detection metrics on the committed validation
run (`mAP50 = 99.5%`, `mAP50-95 = 85.0%`), but the validation set contains only
5 images, so these results should be interpreted as preliminary rather than as
evidence of robust real-world accuracy. No saved FPS benchmark was found in the
repository.

The OpenCV HSV method is present as an autolabeling/preprocessing approach.
The repository shows that it generated labels for all 25 images in the local
QC report, but no independent accuracy, success-rate, or FPS benchmark was
found. Because it relies on fixed HSV color thresholds, it is expected to be
sensitive to changes in lighting, object color, shadows, and background colors.
