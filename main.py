import sys
import os
import webbrowser
import threading
import time
from pathlib import Path

# For PyInstaller compatibility - find the resource path
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

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
else:
    print(f"Warning: Frontend directory not found at {frontend_path}")
    # Fallback route if frontend isn't found
    @app.get("/")
    def read_root():
        return {"message": "Video Skip Lecture API is running", "status": "ok", "frontend_available": False}

@app.get("/")
def read_root():
    frontend_path = resource_path("frontend")
    if os.path.exists(frontend_path):
        return {"message": "Video Skip Lecture API is running", "status": "ok", "frontend_available": True}
    else:
        return {"message": "Video Skip Lecture API is running", "status": "ok", "frontend_available": False}

# 添加一个测试端点供前端连接测试
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}

if __name__ == "__main__":
    def open_browser():
        # Wait a bit for the server to start
        time.sleep(2)
        webbrowser.open("http://127.0.0.1:8001")

    # Start the browser opening in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.start()

    uvicorn.run(app, host="127.0.0.1", port=8001)