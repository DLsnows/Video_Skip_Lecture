# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 构建配置 - Video Skip Lecture

用法:
    pyinstaller video_skip_lecture.spec

前置条件:
    1. ffmpeg.exe 应放在项目根目录，或系统 PATH 中
    2. 所有 Python 依赖已安装
"""

import os
import sys
from pathlib import Path

# ── 项目根目录 ──────────────────────────────────────────────
# SPECPATH 由 PyInstaller 自动定义，指向 spec 文件所在目录
PROJECT_ROOT = Path(SPECPATH).resolve()

# ── 数据文件 ────────────────────────────────────────────────
# 前端静态文件
frontend_tree = Tree(str(PROJECT_ROOT / "frontend"), prefix="frontend")

# ffmpeg.exe：优先从项目根目录查找，其次从系统 PATH 查找
datas = []
ffmpeg_source = PROJECT_ROOT / "ffmpeg.exe"
if ffmpeg_source.exists():
    datas.append((str(ffmpeg_source), "."))
else:
    # 尝试从 PATH 中查找
    import shutil
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        datas.append((ffmpeg_path, "."))
        print(f"[INFO] 使用系统 ffmpeg: {ffmpeg_path}")
    else:
        print("[WARN] ffmpeg.exe 未找到！请确保运行时已安装 ffmpeg 并加入 PATH")

# ── 隐藏导入 ────────────────────────────────────────────────
# FastAPI / Starlette 依赖链
hiddenimports = [
    "starlette",
    "starlette.routing",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.staticfiles",
    "starlette.datastructures",
    "starlette.concurrency",
    "starlette.requests",
    "starlette.responses",
    "starlette.websockets",
    "pydantic",
    "pydantic.dataclasses",
    "pydantic.types",
    "pydantic.fields",
    "pydantic.validators",
    "anyio",
    "anyio.streams",
    "sniffio",
    "h11",
    "multipart",
]

# Uvicorn 动态导入（关键！）
uvicorn_hidden = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.config",
]
hiddenimports.extend(uvicorn_hidden)

# ── 排除项（减小打包体积） ─────────────────────────────────
excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    "PIL",
    "tensorflow",
    "tensorboard",
    "notebook",
    "jupyter",
    "jupyter_client",
    "nbconvert",
    "nbformat",
    "ipython",
    "pandas",
    "numpy.random.examples",
    "setuptools",
    "pip",
    "wheel",
]

# ── Analysis ────────────────────────────────────────────────
block_cipher = None

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

# 如果使用 torch，确保关键子模块被包含
if "torch" in sys.modules or any("torch" in d for d in a.dependencies):
    torch_hidden = [
        "torch",
        "torch.nn",
        "torch.optim",
        "torch.utils",
        "torch.utils.data",
        "torch.serialization",
        "torch.jit",
    ]
    for mod in torch_hidden:
        if mod not in a.hiddenimports:
            a.hiddenimports.append(mod)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="video_skip_lecture",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,           # 保持控制台窗口以查看日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    frontend_tree,          # 包含前端静态文件
    strip=False,
    upx=True,
    upx_exclude=[],
    name="video_skip_lecture",
)
