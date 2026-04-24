# 构建macOS应用程序包

要为macOS创建可直接使用的.app包，请按照以下步骤操作：

## 准备工作
1. 将整个项目文件夹传输到macOS计算机上
2. 确保已安装Python 3.8或更高版本

## 安装依赖
在macOS终端中运行以下命令：
```bash
pip install -r requirements.txt
pip install pyinstaller
```

## 构建应用程序包
运行以下命令来构建macOS应用程序包：
```bash
pyinstaller video_processor_macos.spec
```

## 结果
构建成功后，您将在 `dist/` 文件夹中找到 `VideoSkipLecture.app` 应用程序包，这是一个标准的macOS应用程序，可以直接双击运行。

## 自定义选项
- 如需自定义应用图标，请准备一个 `.icns` 格式的图标文件，并修改 `video_processor_macos.spec` 文件中的 `icon` 参数
- 可以在 `info_plist` 中修改应用的显示名称和其他属性