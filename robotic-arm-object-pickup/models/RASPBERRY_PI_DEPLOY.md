# Raspberry Pi 部署 YOLO Block Detector

目标：把训练好的 `best.pt` 导出为适合 Raspberry Pi CPU 的 NCNN 格式，然后通过 USB webcam 或 Pi camera 实时检测 block。

## 1. 推荐模型格式

推荐部署格式是 **NCNN**。

- 训练后的权重：`block_training_results/white_block_realdata_yolov8n/weights/best.pt`
- 导出后的模型目录：`block_training_results/white_block_realdata_yolov8n/weights/best_ncnn_model/`
- 复制到树莓派时，需要复制整个 `best_ncnn_model` 文件夹。

`.pt` 也可以运行，但通常在 Raspberry Pi 上更慢，并且依赖 PyTorch。NCNN 更适合 ARM CPU。

## 2. 在训练电脑上导出 NCNN

在项目根目录运行：

```powershell
cd C:\Users\29454\Desktop\ENGG1101_YOLO_Model_v1
.\.venv\Scripts\Activate.ps1
pip install "ultralytics[export]"
python export_ncnn.py --imgsz 416 --package
```

如果你最终决定用 320 输入尺寸训练和部署，把 `--imgsz 416` 改成 `--imgsz 320`。训练尺寸和部署尺寸最好保持一致。

成功后会生成：

```text
deploy_pi/
  best_ncnn_model/
  detect_live.py
  requirements-rpi.txt
  RASPBERRY_PI_DEPLOY.md
```

## 3. 复制到 Raspberry Pi

用 `scp`：

```powershell
scp -r .\deploy_pi pi@<RASPBERRY_PI_IP>:~/block_detector
```

或者把整个 `deploy_pi` 文件夹复制到 U 盘，再放到 Raspberry Pi 上并改名为 `block_detector`。

## 4. 在 Raspberry Pi 上安装依赖

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-opencv
cd ~/block_detector
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements-rpi.txt
```

这里使用 `--system-site-packages` 是为了让虚拟环境直接使用系统安装的 `python3-opencv`，避免在树莓派上用 pip 编译 OpenCV。

## 5. 检查摄像头

```bash
ls /dev/video*
```

通常 `/dev/video0` 对应 `--source 0`。如果有多个摄像头，可以试 `--source 1` 或 `--source usb0`。

## 6. 实时检测

有桌面显示器时：

```bash
cd ~/block_detector
source .venv/bin/activate
python detect_live.py --model best_ncnn_model --source 0 --imgsz 416 --conf 0.25
```

SSH/headless 运行时：

```bash
python detect_live.py --model best_ncnn_model --source 0 --imgsz 416 --conf 0.25 --no-display
```

保存检测视频：

```bash
python detect_live.py --model best_ncnn_model --source 0 --imgsz 416 --conf 0.25 --save
```

## 7. 常见调整

如果画面卡顿，降低输入尺寸或摄像头分辨率：

```bash
python detect_live.py --model best_ncnn_model --source 0 --imgsz 320 --width 320 --height 240
```

如果误检太多，提高置信度：

```bash
python detect_live.py --model best_ncnn_model --source 0 --conf 0.4
```

如果漏检太多，先检查标注和光照，再适当降低置信度：

```bash
python detect_live.py --model best_ncnn_model --source 0 --conf 0.15
```
