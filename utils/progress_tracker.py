import threading
import time
from typing import Dict, Any
from datetime import datetime

class ProgressTracker:
    """处理任务的进度跟踪器"""

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def init_task(self, task_id: str, input_folder: str, output_folder: str):
        """初始化新任务"""
        with self.lock:
            self.tasks[task_id] = {
                "task_id": task_id,
                "status": "initialized",
                "overall_progress": 0,
                "current_step": "Initializing",
                "step_progress": 0,
                "input_folder": input_folder,
                "output_folder": output_folder,
                "logs": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            print(f"[DEBUG] Initialized task {task_id}")

    def update_task_progress(self, task_id: str, overall_progress: int, current_step: str, step_progress: int = 0):
        """更新任务进度"""
        if task_id in self.tasks:
            with self.lock:
                self.tasks[task_id].update({
                    "overall_progress": overall_progress,
                    "current_step": current_step,
                    "step_progress": step_progress,
                    "status": "processing",
                    "updated_at": datetime.now().isoformat()
                })
                #print(f"[DEBUG] Updated progress for task {task_id}: {overall_progress}% - {current_step}")
        else:
            print(f"[DEBUG] Attempted to update progress for unknown task {task_id}")

    def add_log(self, task_id: str, level: str, message: str):
        """为任务添加日志条目"""
        if task_id in self.tasks:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message
            }
            with self.lock:
                self.tasks[task_id]["logs"].append(log_entry)
                print(f"[DEBUG] Added log to task {task_id}: [{level.upper()}] {message}")

    def complete_task(self, task_id: str, success: bool = True, message: str = ""):
        """标记任务完成"""
        if task_id in self.tasks:
            with self.lock:
                status = "completed" if success else "failed"
                self.tasks[task_id].update({
                    "status": status,
                    "overall_progress": 100 if success else self.tasks[task_id]["overall_progress"],
                    "updated_at": datetime.now().isoformat()
                })
                # 直接添加日志（已在锁内）
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "level": "info" if success else "error",
                    "message": message
                }
                self.tasks[task_id]["logs"].append(log_entry)
                print(f"[DEBUG] Completed task {task_id} with status: {status}")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务的当前状态"""
        if task_id in self.tasks:
            status = self.tasks[task_id]
            #print(f"[DEBUG] Retrieved status for task {task_id}: {status['overall_progress']}% - {status['current_step']}")
            return status
        return {}

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Return a snapshot of all currently tracked tasks"""
        with self.lock:
            return {tid: dict(data) for tid, data in self.tasks.items()}

    def cleanup_task(self, task_id: str):
        """从跟踪器中移除任务"""
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                print(f"[DEBUG] Cleaned up task {task_id}")
progress_tracker = ProgressTracker()