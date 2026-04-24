import sys
import os
import webbrowser
import threading
import time
from pathlib import Path

# For PyInstaller compatibility - find the resource path
def resource_path(relative_path):
    """Get absolute path to resource, works for dev, onedir, and onefile PyInstaller modes."""
    # Try _MEIPASS (onefile temp dir, or onedir _internal dir)
    try:
        base_path = sys._MEIPASS
        full_path = os.path.join(base_path, relative_path)
        if os.path.exists(full_path):
            return full_path
    except Exception:
        pass

    # Fallback: alongside the executable (dev mode, or onedir root)
    exe_base = os.path.dirname(sys.executable)
    full_path = os.path.join(exe_base, relative_path)
    if os.path.exists(full_path):
        return full_path

    # Fallback: _internal subdirectory (onedir mode)
    internal_path = os.path.join(exe_base, "_internal", relative_path)
    if os.path.exists(internal_path):
        return internal_path

    # Last resort: current working directory
    return os.path.join(os.path.abspath("."), relative_path)

# Add the project root to the path so imports work correctly
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import router as api_router
import uvicorn

app = FastAPI(
    title="Video Skip Lecture API",
    description="API for processing lecture videos and generating summaries",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1", tags=["processing"])

# Mount the frontend static files - use the resource_path function for PyInstaller compatibility
frontend_path = resource_path("frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    print(f"Frontend served from {frontend_path}")
else:
    print(f"Warning: Frontend directory not found at {frontend_path}")
    # Fallback route if frontend isn't found
    @app.get("/")
    def read_root():
        return {"message": "Video Skip Lecture API is running", "status": "ok", "frontend_available": False}

# 添加一个测试端点供前端连接测试
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}

import socket

def find_available_port(start_port=8001, max_attempts=100):
    """从 start_port 开始查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"无法找到可用端口（从 {start_port} 开始尝试 {max_attempts} 个）")

if __name__ == "__main__":
    print("=" * 50)
    print("  Video Skip Lecture - 视频讲座处理平台")
    print("=" * 50)
    if getattr(sys, '_MEIPASS', False):
        print(f"  运行模式: PyInstaller 打包")
        print(f"  程序目录: {os.path.dirname(sys.executable)}")
    else:
        print(f"  运行模式: 开发模式")

    from config.config_manager import config_manager
    print(f"  配置文件: {config_manager.config_file}")
    print()

    port = find_available_port()

    def open_browser():
        time.sleep(2)
        webbrowser.open(f"http://127.0.0.1:{port}")

    browser_thread = threading.Thread(target=open_browser)
    browser_thread.start()

    print(f"  服务器启动于 http://127.0.0.1:{port}")
    print(f"  按 Ctrl+C 停止服务器")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=port)