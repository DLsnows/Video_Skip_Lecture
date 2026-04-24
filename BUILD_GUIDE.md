# Video Skip Lecture - 应用程序构建指南

## 概述
本指南介绍了如何将 Video Skip Lecture 应用程序打包为独立的 Windows 可执行文件 (exe)。

## 环境要求
- Python 3.10+ 环境
- 安装了所有项目依赖项
- PyInstaller 已安装 (`pip install pyinstaller`)

## 构建前的准备工作

### 1. 检查依赖
确保以下文件中的所有依赖都已安装：
- `requirements.txt`
- `requirements1.txt`

运行以下命令安装依赖：
```bash
pip install -r requirements.txt
pip install -r requirements1.txt
```

### 2. 确认文件结构
确保以下关键文件存在于项目根目录：
- `main.py` - 主程序入口
- `frontend/` - 前端静态文件目录
- `api/`, `core/`, `utils/`, `config/` - 核心模块目录
- `video_processor.spec` - PyInstaller 配置文件

## 构建步骤

### 方法一：使用预配置的 spec 文件（推荐）

1. **清理旧的构建缓存**
   ```bash
   # 删除 build 和 dist 目录（如有）
   rm -rf build/
   rm -rf dist/
   ```

2. **运行 PyInstaller**
   ```bash
   pyinstaller video_processor.spec
   ```

3. **等待构建完成**
   构建过程可能需要 10-30 分钟，具体取决于计算机性能和依赖数量。

4. **检查构建结果**
   - 构建成功后，exe 文件将出现在 `dist/` 目录中
   - 文件名为 `VideoSkipLecture.exe`
   - 文件大小约为 360+ MB

### 方法二：直接构建（不推荐，可能导致路径问题）
```bash
pyinstaller --onefile --windowed --add-data "frontend;frontend" main.py
```

## video_processor.spec 文件详解

当前使用的 spec 文件配置了以下功能：

### 数据文件包含
```python
# 递归包含 frontend 目录的所有文件
datas = []
frontend_path = 'frontend'
if os.path.exists(frontend_path):
    for root, dirs, files in os.walk(frontend_path):
        for file in files:
            file_path = os.path.join(root, file)
            dest_path = os.path.relpath(root, '.')
            datas.append((file_path, dest_path))
```

### 依赖处理
- 自动收集所有子模块
- 显式包含关键依赖（FastAPI, Uvicorn, Transformers, WhisperX, OpenCV 等）
- 包含配置文件（config.json）

## 常见问题及解决方案

### 问题1：RuntimeError: Directory 'frontend' does not exist
**解决方案**：确保 `main.py` 中包含资源路径处理函数：
```python
def resource_path(relative_path):
    """ 获取资源绝对路径，适用于开发环境和 PyInstaller 打包环境 """
    try:
        # PyInstaller 创建临时文件夹并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)
```

### 问题2：缺少模块错误
**解决方案**：在 spec 文件的 `hiddenimports` 列表中添加缺失的模块。

### 问题3：构建时间过长
**解决方案**：这是正常的，因为需要处理大量机器学习相关的依赖库。

## 验证构建结果

### 1. 检查文件
```bash
# 检查生成的文件
ls -la dist/

# 检查文件类型
file dist/VideoSkipLecture.exe
```

### 2. 运行测试
- 双击运行 `dist/VideoSkipLecture.exe`
- 检查浏览器是否自动打开 http://127.0.0.1:8001
- 确认前端界面正常加载
- 测试基本功能是否正常工作

## 自动化构建脚本

### Windows 批处理脚本 (build.bat)
```batch
@echo off
echo 开始构建 Video Skip Lecture 应用程序...
echo.

echo 清理旧的构建文件...
if exist build (
    echo 删除 build 目录...
    rmdir /s /q build
)
if exist dist (
    echo 删除 dist 目录...
    rmdir /s /q dist
)

echo.
echo 开始构建...
pyinstaller video_processor.spec

echo.
echo 构建完成！
echo 可执行文件位置：dist\VideoSkipLecture.exe
echo.
echo 按任意键退出...
pause > nul
```

### Linux/Mac Shell 脚本 (build.sh)
```bash
#!/bin/bash
echo "开始构建 Video Skip Lecture 应用程序..."
echo

echo "清理旧的构建文件..."
rm -rf build/
rm -rf dist/

echo
echo "开始构建..."
pyinstaller video_processor.spec

echo
echo "构建完成！"
echo "可执行文件位置：dist/VideoSkipLecture"
echo
```

## 发布版本管理

### 版本标记
建议每次构建后记录版本号，在 README 中添加版本信息：
- 构建日期
- 版本号
- 主要变更内容

### 备份策略
- 保留最近几个版本的可执行文件作为备份
- 对于重要的版本发布，创建 Git 标签
- 记录每次构建时使用的依赖版本

## 故障排除

### 构建失败
1. 检查 Python 环境是否包含所有必要依赖
2. 确认项目文件完整性
3. 检查磁盘空间是否充足
4. 查看详细的错误日志

### 运行时错误
1. 确认 spec 文件中的 `datas` 配置是否正确包含所有必要文件
2. 检查 `hiddenimports` 是否包含所有依赖模块
3. 确认 main.py 中的资源路径处理逻辑

## 性能优化建议

### 减少文件大小
- 仅包含必要的依赖
- 考虑使用 UPX 压缩（PyInstaller 默认启用）

### 提升启动速度
- 尽量减少启动时加载的模块
- 优化初始化代码

## 维护建议

### 定期更新
- 定期更新依赖包到稳定版本
- 测试新版本构建是否正常工作
- 更新 spec 文件以适应依赖变化

### 文档维护
- 记录每个版本的特殊构建要求
- 保存构建成功的依赖版本组合
- 维护常见问题解决方案文档

---

**注意**：第一次构建可能需要较长时间，后续构建会因为缓存而变快。如果更新了前端文件或添加了新的依赖，建议清理构建缓存重新构建。