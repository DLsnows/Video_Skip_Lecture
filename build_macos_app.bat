@echo off
REM 构建macOS应用程序包
echo 开始构建macOS应用程序包...

REM 检查是否在macOS上运行（仅用于文档说明）
echo 注意：此构建脚本设计用于macOS系统
echo 在macOS上运行以下命令来构建应用程序：
echo.
echo pyinstaller video_processor_macos.spec
echo.

echo 在Windows上创建占位文件以便传输到macOS系统
if not exist "dist" mkdir dist
if not exist "dist\macOS_Build_Instructions.txt" (
    echo 要在macOS上构建应用程序，请执行以下步骤： > dist\macOS_Build_Instructions.txt
    echo 1. 将整个项目文件夹传输到macOS系统 >> dist\macOS_Build_Instructions.txt
    echo 2. 确保已安装Python和PyInstaller: pip install pyinstaller >> dist\macOS_Build_Instructions.txt
    echo 3. 运行: pyinstaller video_processor_macos.spec >> dist\macOS_Build_Instructions.txt
    echo 4. 构建完成后，您将在dist/文件夹中找到VideoSkipLecture.app >> dist\macOS_Build_Instructions.txt
    echo.
    echo 可选：如果您想要自定义应用图标，请提供一个icns格式的图标文件，并在spec文件中设置icon参数。
)

echo macOS构建说明已创建: dist\macOS_Build_Instructions.txt
echo.
echo 构建步骤：
echo 1. 将项目传输到macOS计算机
echo 2. 安装依赖: pip install -r requirements.txt
echo 3. 安装PyInstaller: pip install pyinstaller
echo 4. 运行: pyinstaller video_processor_macos.spec
echo 5. 在dist/VideoSkipLecture.app中找到构建完成的应用程序包