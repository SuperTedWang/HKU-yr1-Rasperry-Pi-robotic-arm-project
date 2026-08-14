# GitHub 上传指南

这个项目已经整理成适合上传 GitHub 的仓库结构。你还需要在本机安装 Git，登录 GitHub，然后把本地仓库推送到远程仓库。

## 1. 安装 Git

如果终端运行 `git --version` 报错，先安装 Git for Windows:

```text
https://git-scm.com/download/win
```

安装完成后重新打开 PowerShell。

## 2. 进入项目目录

```powershell
cd C:\Users\29454\Documents\ChatGPT\Github\robotic-arm-object-pickup
```

## 3. 初始化 Git 仓库

```powershell
git init
git add .
git commit -m "Initial commit: add robotic arm object pickup project"
```

## 4. 在 GitHub 创建远程仓库

在 GitHub 网页端创建一个新仓库，推荐名字：

```text
robotic-arm-object-pickup
```

如果你还没有得到所有组员同意，建议先选择 `Private`。

## 5. 连接远程仓库并上传

把下面的 `YOUR_USERNAME` 换成你的 GitHub 用户名：

```powershell
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/robotic-arm-object-pickup.git
git push -u origin main
```

## 6. 如果模型文件太大

GitHub 普通文件限制为 100 MB。如果 `.pt` 模型文件比较大，使用 Git LFS：

```powershell
git lfs install
git lfs track "*.pt"
git add .gitattributes models/
git commit -m "Add YOLO model with Git LFS"
git push
```

如果你暂时不想使用 Git LFS，可以先不上传模型文件，只在 README 里说明模型文件放在哪里，以及如何获取。

## 7. 上传前检查

运行：

```powershell
git status
```

确认没有误上传：

- 私人信息
- Wi-Fi 密码
- API key
- 学校内部未公开资料
- 过大的视频文件
- `.venv` 虚拟环境
