import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import uuid
from datetime import datetime
import threading
import traceback

from utils.progress_tracker import progress_tracker
from core.processor import process_videos
from config.config_manager import config_manager
parent_dir = Path(__file__).parent.parent
config_manager.config_file=os.path.join(parent_dir,"config.json")
router = APIRouter()
# routes.py 中 wrapped_process_videos 开头

def wrapped_process_videos(task_id: str, input_folder: str, output_folder: str, video_language: str):
    """Wrapper function for process_videos that catches exceptions and reports them"""
    try:
        # Skip the validation step and go directly to processing as requested by user
        progress_tracker.update_task_progress(task_id, 3, "Processing thread started - initializing", 0)
        progress_tracker.add_log(task_id, "info", "Processing thread started - initialization complete, beginning file processing")

        # Small delay to ensure the update is processed before proceeding
        import time
        time.sleep(0.1)

        process_videos(task_id, input_folder, output_folder, video_language)

        # Ensure final progress update is sent
        if task_id in progress_tracker.tasks:
            final_status = progress_tracker.get_task_status(task_id)
            if final_status.get('status') not in ['completed', 'failed']:
                progress_tracker.update_task_progress(task_id, 100, "Processing completed", 100)
                progress_tracker.complete_task(task_id, success=True, message="Task completed successfully")
        

    except Exception as e:
        # Report the error to the progress tracker
        error_msg = f"Error in processing: {str(e)}"
        error_msg += f"\nTraceback: {traceback.format_exc()}"

        # Update progress tracker with error information
        progress_tracker.add_log(task_id, "error", error_msg)
        progress_tracker.complete_task(task_id, success=False, message=str(e))



class ProcessRequest(BaseModel):
    input_folder: str
    output_folder: str
    video_language: Optional[str] = "en"

class ProcessResponse(BaseModel):
    task_id: str
    status: str
    message: str
    individual_tasks: Optional[List[dict]] = None  # For multiple video processing

class SettingsRequest(BaseModel):
    transcription_provider: Optional[dict] = None
    ocr_provider: Optional[dict] = None
    summarization_provider: Optional[dict] = None
    folders: Optional[dict] = None

@router.post("/process", response_model=ProcessResponse)
async def start_processing(request: ProcessRequest):
    """启动视频处理任务"""
    try:
        # 验证API密钥是否已配置
        transcription_key = config_manager.get_setting("transcription_provider", "api_key")
        ocr_key = config_manager.get_setting("ocr_provider", "api_key")
        summarization_key = config_manager.get_setting("summarization_provider", "api_key")

        if not transcription_key and not ocr_key and not summarization_key:
            raise HTTPException(status_code=400, detail="至少需要配置一个服务的API密钥")

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 初始化进度跟踪
        progress_tracker.init_task(task_id, request.input_folder, request.output_folder)

        # 设置初始状态，告知前端任务已被接受
        progress_tracker.update_task_progress(task_id, 0, "任务已接受，准备开始处理", 0)
        progress_tracker.add_log(task_id, "info", f"Task accepted with input: {request.input_folder}, output: {request.output_folder}")

        # 启动处理任务（异步）
        thread = threading.Thread(
            target=wrapped_process_videos,
            args=(task_id, request.input_folder, request.output_folder, request.video_language)
        )
        thread.daemon = True  # 设置为守护线程
        thread.start()

        # 确保初始状态已设置后再返回响应
        # 短暂延迟以确保初始进度更新已经发出
        import time
        time.sleep(0.1)

        return ProcessResponse(
            task_id=task_id,
            status="started",
            message=f"Processing started for {request.input_folder}",
            individual_tasks=[]  # Will be populated later when individual tasks are created
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """获取处理状态"""
    if task_id not in progress_tracker.tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    return progress_tracker.get_task_status(task_id)

@router.websocket("/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """WebSocket端点用于实时进度更新"""
    await websocket.accept()

    if task_id not in progress_tracker.tasks:
        await websocket.close(code=1008, reason="Task not found")
        return

    try:
        last_status_hash = None
        last_progress_sent = -1  # Track the last progress percentage sent
        last_updated_at = ""  # Track the last updated_at timestamp sent

        while True:
            if task_id in progress_tracker.tasks:
                status = progress_tracker.get_task_status(task_id)

                # 获取当前进度值和更新时间
                current_progress = status.get('overall_progress', 0)
                current_updated_at = status.get('updated_at', "")

                # 检查进度是否发生了有意义的变化（例如，增加了至少1%）或时间戳更新
                progress_significant_change = abs(current_progress - last_progress_sent) >= 1
                timestamp_updated = current_updated_at != last_updated_at

                # 创建状态的哈希值，仅当状态改变时才发送更新
                current_status_str = str(sorted(status.items()))
                current_status_hash = hash(current_status_str)

                # 只在有意义的变化发生时发送更新
                if (progress_significant_change or timestamp_updated) and current_status_hash != last_status_hash:
                    await websocket.send_json(status)
                    last_status_hash = current_status_hash
                    last_progress_sent = current_progress  # Update the last sent progress
                    last_updated_at = current_updated_at  # Update the last sent timestamp

                # 检查任务是否已完成，如果是则退出循环
                if status.get('status') in ['completed', 'failed']:
                    # 已发送最终状态，退出循环以关闭连接
                    break

            await asyncio.sleep(0.5)  # 减少间隔时间以更快响应
    except WebSocketDisconnect:
        pass

@router.get("/settings")
async def get_settings():
    """获取当前设置"""
    return config_manager.config

@router.put("/settings")
async def update_settings(settings: SettingsRequest):
    """更新设置"""
    try:
        if settings.transcription_provider is not None:
            config_manager.update_setting("transcription_provider", settings.transcription_provider)
        if settings.ocr_provider is not None:
            config_manager.update_setting("ocr_provider", settings.ocr_provider)
        if settings.summarization_provider is not None:
            config_manager.update_setting("summarization_provider", settings.summarization_provider)
        if settings.folders is not None:
            config_manager.update_setting("folders", settings.folders)

        return {"message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))