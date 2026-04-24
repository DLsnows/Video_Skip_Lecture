import os
import sys
import subprocess
import time
import gc
import torch
import whisperx
import cv2
import base64
from openai import OpenAI
from pathlib import Path
import concurrent.futures
from typing import List, Tuple
from datetime import datetime
import uuid
import threading
import shutil

# Add parent directory to path to import config
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from config.config_manager import config_manager
# Initialize global progress tracker
from utils.progress_tracker import progress_tracker
# processor.py 中 process_videos 开头

def chunk_list(lst, size):
    """Helper function to split a list into chunks"""
    result_list = []
    for i in range(0, len(lst), size):
        result_list.append(lst[i:i+size])
    return result_list

def get_ffmpeg_path() -> str:
    """Get the path to ffmpeg executable, works for both dev and PyInstaller."""
    if getattr(sys, '_MEIPASS', False):
        ffmpeg_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.exists(ffmpeg_path):
            return ffmpeg_path
    return "ffmpeg"

def deepseek(client, role, prompt, content):
    """Call DeepSeek API"""
    try:
        model = config_manager.get_setting("summarization_provider", "model") or "deepseek-reasoner"
        api_key = config_manager.get_setting("summarization_provider", "api_key") or ""

        if not api_key:
            raise ValueError("Summarization API key not configured")

        base_url = config_manager.get_setting("summarization_provider", "base_url") or "https://api.deepseek.com"

        client = OpenAI(api_key=api_key, base_url=base_url)

        # Update before making API call
        print("Making DeepSeek API call...")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": role},
                {"role": "user", "content": prompt + content},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        return ""

def markdownFromImageInfra(ocr_client, imagePath):
    """Convert image to markdown using DeepSeek OCR via configured provider"""
    try:
        model = config_manager.get_setting("ocr_provider", "model") or "deepseek-ai/DeepSeek-OCR"

        with open(imagePath, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        chat_completion = ocr_client.chat.completions.create(
            model=model,
            max_tokens=4092,
            messages=[
                {
                    "role": "system",
                    "content": "请将识别结果以 Markdown 格式输出。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error in OCR: {e}")
        return ""

def audio_transcriptInfra(whisper_client, audioPath, language):
    print("transcript")
    """Transcribe audio using Whisper via configured provider"""
    print(f"{audioPath} 分析音频中")

    try:
        model = config_manager.get_setting("transcription_provider", "model") or "openai/whisper-large-v3"

        audio_file = open(audioPath, "rb")
        transcript = whisper_client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format="verbose_json",
            language=language,
        )
        audio_file.close()

        # Force alignment using whisperx
        device = "cpu"  # Using CPU for alignment to conserve GPU for other tasks
        audio_data = whisperx.load_audio(audioPath)
        model_a, metadata = whisperx.load_align_model(
            language_code=language,
            device=device,
        )

        segments = [seg.model_dump() for seg in transcript.segments]

        result_final = whisperx.align(
            segments,
            model_a,
            metadata,
            audio_data,
            device
        )

        strings_to_return = []
        timelines_to_return = []
        end_to_return = []

        for seg in result_final["segments"]:
            strings_to_return.append(f"{seg['start']}: {seg['text']}")
            timelines_to_return.append(seg["start"])
            end_to_return.append(seg["end"])

        # Clean up
        del model_a
        del metadata
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return strings_to_return, timelines_to_return, end_to_return
    except Exception as e:
        print(f"Error in audio transcription: {e}")
        return [], [], []

def capture_frame(video_path, time_sec, output_path):
    """Capture a frame from video at specific time"""
    cap = cv2.VideoCapture(video_path)

    # Set the time point (in milliseconds)
    cap.set(cv2.CAP_PROP_POS_MSEC, float(time_sec) * 1000)

    success, frame = cap.read()
    if success:
        cv2.imwrite(output_path, frame)
    else:
        print(f"Cannot read frame at time {time_sec}")

    cap.release()

def manageTimeLine(timeline, mod):
    """Manage timeline by taking every nth element"""
    result = []
    for i in range(len(timeline)):
        if i % mod == 0:
            result.append(timeline[i])
    return result

def manageTimeLineEnd(timeline, mod):
    """Manage timeline by taking end elements"""
    result = []
    for i in range(len(timeline)):
        if i % mod == (mod-1):
            result.append(timeline[i])
    result.append(timeline[len(timeline)-1])
    return result

def getFrames(video_path, startTimelineManaged, endTimelineManaged, capture_frequency, capture_output_path):
    """Capture frames from video at specified intervals"""
    imagePaths = []
    for i in range(len(startTimelineManaged)):
        startTimeline = startTimelineManaged[i]
        endTimeline = endTimelineManaged[i]
        delta = round(((float(-float(startTimeline) + float(endTimeline))) / capture_frequency), 2)
        result = []
        for j in range(capture_frequency):
            mid = str(round((float(startTimeline) + j * delta), 2))
            capture_frame(video_path, mid, os.path.join(capture_output_path, f"{mid}.png"))
            result.append(os.path.join(capture_output_path, f"{mid}.png"))
        imagePaths.append(result)
    return imagePaths

def break_video(video_path, language, audio_path, capture_output_path):
    """Break video into segments for processing"""
    # Create clients for this processing task using configured settings
    transcription_base_url = config_manager.get_setting("transcription_provider", "base_url") or "https://api.deepinfra.com/v1/openai"
    transcription_api_key = config_manager.get_setting("transcription_provider", "api_key") or ""
    if not transcription_api_key:
        raise ValueError("Transcription API key not configured")

    whisper_client = OpenAI(
        api_key=transcription_api_key,
        base_url=transcription_base_url,
    )

    # Update progress before audio transcription
    print("Starting audio transcription...")
    stringsFromVideo, startTimelineFromVideo, endTimelineFromVideo = audio_transcriptInfra(whisper_client, audio_path, language)
    print("chunk list")
    stringsFromVideoChunked = chunk_list(stringsFromVideo, 25)  # ANALYSE_PARAGRAPH_NUMBER = 25
    print("timeline")
    startTimelineManaged = manageTimeLine(startTimelineFromVideo, 25)  # ANALYSE_PARAGRAPH_NUMBER = 25
    endTimelineManaged = manageTimeLineEnd(endTimelineFromVideo, 25)  # ANALYSE_PARAGRAPH_NUMBER = 25
    imagePaths = getFrames(video_path, startTimelineManaged, endTimelineManaged, 10, capture_output_path)  # CAPTURE_FREQUENCY = 10
    print(f"{video_path} 视频切片完成")

    return imagePaths, stringsFromVideoChunked

def analyse_ppt(ocr_client, imagePaths, task_id: str, max_workers=40):  # MAX_WORKERS_IMAGE = 40
    """Analyze PPT slides using OCR"""
    result = []
    total_sections = len(imagePaths)

    for i, images in enumerate(imagePaths):
        # Update progress for this section - this is part of the OCR processing within AI processing stage (55%-70%)
        progress_start = 20
        progress_end = 35
        progress_range = progress_end - progress_start

        progress_percent = int(progress_start + (i / total_sections) * progress_range)
        progress_tracker.update_task_progress(
            task_id,
            progress_percent,
            f"正在处理PPT {i+1}/{total_sections}",
            int((i / total_sections) * 100)
        )

        print(f"PPT {i+1}/{len(imagePaths)} 开始处理...")
        result2 = []

        # Process images in parallel for current PPT section
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {executor.submit(markdownFromImageInfra, ocr_client, img): idx
                             for idx, img in enumerate(images)}

            # Collect results, preserving order
            temp = [None] * len(images)
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    markdown = future.result()
                    if markdown is not None:
                        temp[idx] = markdown
                except Exception as e:
                    print(f"Image {idx} processing failed: {e}")
                    progress_tracker.add_log(task_id, "error", f"Image {idx} processing failed: {e}")

            # Filter out None values and preserve order
            result2 = [m for m in temp if m is not None]

        result.append(result2)
        print(f"PPT {i+1}/{len(imagePaths)} 处理完成")

    print("所有 PPT 分析完成")
    return result

def analyse_video(video_path, language, audio_path, capture_output_path, task_id: str):
    """Main function to analyze video content"""
    print("analyze")

    # Update progress before breaking video - audio analysis (10-20%)
    progress_tracker.update_task_progress(task_id, 10, "正在分析音频", 0)

    # Add more specific log for audio analysis start
    progress_tracker.add_log(task_id, "info", "开始分析语音")

    imagePaths, stringsFromVideoChunked = break_video(video_path, language, audio_path, capture_output_path)

    # Add log for audio analysis completion
    progress_tracker.add_log(task_id, "info", "语音分析完成")

    # Create OCR client for this processing task using configured settings
    ocr_base_url = config_manager.get_setting("ocr_provider", "base_url") or "https://api.deepinfra.com/v1/openai"
    ocr_api_key = config_manager.get_setting("ocr_provider", "api_key") or ""

    if not ocr_api_key:
        raise ValueError("OCR API key not configured")
    print("ocr client")
    ocr_client = OpenAI(
        api_key=ocr_api_key,
        base_url=ocr_base_url,
    )

    # Update progress before starting PPT analysis - OCR processing
    progress_tracker.update_task_progress(task_id, 20, "正在处理PPT幻灯片", 0)

    # Add more specific log for PPT analysis start
    progress_tracker.add_log(task_id, "info", "开始分析PPT")

    print(f"{video_path} 分析PPT中")
    pptContent = analyse_ppt(ocr_client, imagePaths, task_id)

    # Add log for PPT analysis completion
    progress_tracker.add_log(task_id, "info", "PPT分析完成")

    # Create main client for this processing task using configured settings
    summarization_base_url = config_manager.get_setting("summarization_provider", "base_url") or "https://api.deepseek.com"
    summarization_api_key = config_manager.get_setting("summarization_provider", "api_key") or ""

    if not summarization_api_key:
        raise ValueError("Summarization API key not configured")

    client = OpenAI(
        api_key=summarization_api_key,
        base_url=summarization_base_url,
    )

    # Update progress before generating explanations - content generation
    progress_tracker.update_task_progress(task_id, 35, "正在生成课程讲解", 0)

    # Add more specific log for course explanation start
    progress_tracker.add_log(task_id, "info", "开始生成课程讲解")

    print(f"{video_path} 正在生成课程讲解")

    # Define roles and prompts
    ROLE_SKIP = "你要扮演我的大学教授，根据我下面给你提供的，来自上课录屏的ppt的截图和教授说的话的转译，在尽可能不错过知识点的情况下，向我详细总结和讲解这节课的内容。"
    PROMPT_SKIP = "根据我下面给你提供的，来自上课录屏的ppt的截图和教授说的话的转译，在尽可能不错过知识点的情况下向我详细总结和讲解这一段的内容，用markdown格式输出。"

    answerList = ["下面让我们开始讲解这节课的内容："]
    for i in range(len(pptContent)):
        progress_tracker.update_task_progress(
            task_id,
            35 + int((i / len(pptContent)) * 50),  # Distribute 50% across content generation (from 35% to 85%)
            f"生成讲解 {i+1}/{len(pptContent)}",
            int((i / len(pptContent)) * 100)
        )

        content = f"这是老师的原话的转译: {stringsFromVideoChunked[i]}; 下面是PPT截图的内容: {pptContent[i]} 这是你上一段给我讲解的内容: {answerList[i]}"
        answerList.append(deepseek(client, ROLE_SKIP, PROMPT_SKIP, content))

    print(f"{video_path} 课程讲解生成完成")

    # Add log for completion of course explanation generation
    progress_tracker.add_log(task_id, "info", "课程讲解生成完成")

    return answerList

def resume_video_analyse(analyseResult, outputDir, task_id: str):
    """Generate final course summary"""

    # Add log for start of summary generation
    progress_tracker.add_log(task_id, "info", "开始生成课程总结")

    if len(analyseResult) > 0:
        analyseResult = analyseResult[1:]  # Remove first element

    answerListChunked = chunk_list(analyseResult, 3)  # RESUME_PARAGRAPH_NUMBER = 3
    result = ["下面让我们开始讲解这节课的内容："]
    print(f"{outputDir} 正在生成课程总结")

    # Create main client for this processing task using configured settings
    summarization_base_url = config_manager.get_setting("summarization_provider", "base_url") or "https://api.deepseek.com"
    summarization_api_key = config_manager.get_setting("summarization_provider", "api_key") or ""

    if not summarization_api_key:
        raise ValueError("Summarization API key not configured")

    client = OpenAI(
        api_key=summarization_api_key,
        base_url=summarization_base_url,
    )

    # Define roles and prompts for summarization
    ROLE_SKIP_RESUME = "你要扮演我的大学教授，在尽可能不错过知识点的情况下，整理和重写下面给你提供的分段讲解的内容，以便我可以更好的阅读和理解。"
    PROMPT_SKIP_RESUME = "你要扮演我的大学教授，在尽可能不错过知识点的情况下，整理和重写下面给你提供的分段讲解的内容，以便我可以更好的阅读和理解，用markdown格式输出。"

    # Update progress before starting summarization - final stage
    progress_tracker.update_task_progress(task_id, 85, "正在生成课程总结", 0)

    total_chunks = len(answerListChunked)
    for i in range(total_chunks):
        progress_tracker.update_task_progress(
            task_id,
            85 + int((i / total_chunks) * 10),  # Distribute final 10% across summary generation (from 85% to 95%)
            f"正在生成总结 {i+1}/{total_chunks}",
            int((i / total_chunks) * 100)
        )

        content = f"为了让你能更好的整理，这是你上一段整理的内容：{result[i]} 下面是你需要处理的内容：{answerListChunked[i]}"
        result.append(deepseek(client, ROLE_SKIP_RESUME, PROMPT_SKIP_RESUME, content))

    print(f"{outputDir} 课程讲解生成完成")

    # Add log for completion of summary generation
    progress_tracker.add_log(task_id, "info", "课程总结生成完成")

    # Write the final result to a file
    output_file = os.path.join(outputDir, "resume.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(result))


def cleanup_output_files(output_folder):
    """
    将所有子文件夹中的 resume.txt 文件移动到主输出目录并按视频名重命名，
    然后删除原始的子文件夹。
    """
    import os
    import shutil

    # 获取输出目录中的所有文件夹
    exclude = {"captureTemp", "output", "__pycache__"}   # 用集合更快

    folders = []

    for name in os.listdir(output_folder):
        full_path = os.path.join(output_folder, name)

        if os.path.isdir(full_path) and name not in exclude:
            folders.append(full_path)

    # 遍历所有文件夹并移动其中的 resume.txt 文件
    for folder in folders:
        try:
            # 检查当前文件夹中是否有resume.txt文件
            src = os.path.join(folder, "resume.txt")

            # 如果找到了resume.txt文件，则移动它
            if os.path.exists(src):
                dst = os.path.join(output_folder, f"{os.path.basename(folder)}_resume.txt")
                shutil.move(src, dst)
                print(f"Moved {src} to {dst}")

                # 删除整个文件夹
                if os.path.exists(folder):
                    shutil.rmtree(folder)
                    print(f"Removed folder: {folder}")
            else:
                print(f"No resume.txt found in {folder} or its subfolders")
        except Exception as e:
            # 记录错误但继续处理其他文件夹
            print(f"Error processing folder {folder}: {str(e)}")
            continue

def skip_this_lecture(video_path, language, audio_path, outputDir, capture_output_path, task_id: str):
    """Main function to process a single lecture video"""
    # Analyze the video and generate initial content
    print("skip this lecture")
    initial_content = analyse_video(video_path, language, audio_path, capture_output_path, task_id)

    # Generate final summary
    resume_video_analyse(initial_content, outputDir, task_id)


def process_single_video(video_path: str, task_id: str, input_folder: str, output_folder: str, video_language: str = "en"):
    """
    Process a single video file with its own task ID
    """
    try:
        video_name = os.path.basename(video_path)
        video_base_name = os.path.splitext(video_name)[0]

        # Initialize the specific task for this video
        progress_tracker.init_task(task_id, input_folder, output_folder)

        # Add to parent task's log if we can identify the parent
        progress_tracker.update_task_progress(task_id, 0, f"开始处理视频: {video_name}", 0)
        progress_tracker.add_log(task_id, "info", f"开始处理视频: {video_path}")

        # Create output directory for this specific video
        video_output_dir = os.path.join(output_folder, video_base_name)
        os.makedirs(video_output_dir, exist_ok=True)

        # Create a temporary directory for captures specific to this video
        capture_output_path = os.path.join(video_output_dir, "captureTemp")
        os.makedirs(capture_output_path, exist_ok=True)

        # Convert video to audio first
        audio_path = os.path.join(video_output_dir, video_base_name + ".mp3")  # Changed to put audio in video's output dir

        # Check if audio file already exists
        if not os.path.exists(audio_path):
            progress_tracker.update_task_progress(
                task_id,
                5,
                f"正在拆分音频: {video_name}",
                0
            )

            progress_tracker.add_log(task_id, "info", f"Starting audio extraction for {video_name} using ffmpeg")

            # Use ffmpeg to convert video to audio
            cmd = [
                get_ffmpeg_path(),
                "-i", os.path.normpath(video_path),
                "-vn",
                "-acodec", "libmp3lame",
                "-b:a", "192k",
                "-y",
                os.path.normpath(audio_path)
            ]

            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=1800)
                progress_tracker.add_log(task_id, "info", f"Successfully extracted audio: {video_name}")

                progress_tracker.update_task_progress(
                    task_id,
                    10,
                    f"音频提取完成: {video_name}",
                    100
                )
            except subprocess.TimeoutExpired:
                error_details = "Audio extraction timed out after 30 minutes"
                progress_tracker.add_log(task_id, "error", f"Audio extraction failed for {video_name}: {error_details}")
                progress_tracker.update_task_progress(task_id, 100, f"处理失败: {video_name}", 0)
                progress_tracker.complete_task(task_id, False, error_details)
                return
            except subprocess.CalledProcessError as e:
                error_details = f"Return code: {e.returncode}, Error: {e.stderr[:200]}..." if len(e.stderr) > 200 else f"Return code: {e.returncode}, Error: {e.stderr}"
                progress_tracker.add_log(task_id, "error", f"Audio extraction failed for {video_name}: {error_details}")
                progress_tracker.update_task_progress(task_id, 100, f"处理失败: {video_name}", 0)
                progress_tracker.complete_task(task_id, False, error_details)
                return
        else:
            progress_tracker.add_log(task_id, "info", f"Using existing audio file: {audio_path}")

            progress_tracker.update_task_progress(
                task_id,
                10,
                f"使用已有音频: {video_name}",
                100
            )

        # Process the lecture video
        try:
            progress_tracker.add_log(task_id, "info", f"Starting AI processing for {video_name}")
            print("start")

            skip_this_lecture(
                video_path=video_path,
                language=video_language,
                audio_path=audio_path,
                outputDir=video_output_dir,
                capture_output_path=capture_output_path,
                task_id=task_id
            )

            progress_tracker.add_log(task_id, "info", f"Completed processing: {video_name}")
            progress_tracker.update_task_progress(task_id, 100, f"处理完成: {video_name}", 100)
            try:
                # 清理输出文件，将各个子文件夹中的 resume.txt 移动到主输出目录并重命名
                progress_tracker.add_log(task_id, "info", f"Cleaning up: {video_name}")
                cleanup_output_files(output_folder)
            except Exception as e:
                progress_tracker.add_log(task_id, "error", f"Error cleaning up output files: {str(e)}")
            progress_tracker.complete_task(task_id, True, f"Successfully processed: {video_name}")

        except Exception as e:
            error_msg = f"Error processing {video_name}: {str(e)}"
            progress_tracker.add_log(task_id, "error", error_msg)
            progress_tracker.update_task_progress(task_id, 100, f"处理失败: {video_name}", 0)
            progress_tracker.complete_task(task_id, False, error_msg)

    except Exception as e:
        error_msg = f"Critical error in process_single_video: {str(e)}"
        progress_tracker.add_log(task_id, "error", error_msg)
        progress_tracker.update_task_progress(task_id, 100, "处理失败", 0)
        progress_tracker.complete_task(task_id, False, error_msg)

def makeaudio_multithread(input_dir, task_id: str, max_workers=4):
    """Convert MP4 files to MP3 in parallel"""
    # Find all subdirectories (excluding captureTemp and output)
    exclude = {"captureTemp", "output"}
    folders = []

    for name in os.listdir(input_dir):
        full_path = os.path.join(input_dir, name)
        if os.path.isdir(full_path) and name not in exclude:
            folders.append(full_path)

    # Collect all conversion tasks
    tasks = []
    for folder in folders:
        input_dir_plus = os.path.join(input_dir, os.path.basename(folder))
        if not os.path.isdir(input_dir_plus):
            continue

        for f in os.listdir(input_dir_plus):
            if f.endswith(".mp4"):
                input_path = os.path.join(input_dir_plus, f)
                output_path = os.path.join(input_dir_plus, os.path.splitext(f)[0] + ".mp3")
                tasks.append((input_path, output_path))

    total = len(tasks)
    if total == 0:
        print("No MP4 files found.")
        return

    print(f"Found {total} MP4 files, starting conversion with {max_workers} threads...")

    def convert_one(input_path, output_path):
        """Convert a single file"""
        cmd = [
            get_ffmpeg_path(),
            "-i", input_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-b:a", "192k",
            "-y",
            output_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return input_path, output_path, True, None
        except subprocess.CalledProcessError as e:
            return input_path, output_path, False, e.stderr

    # Execute conversions in parallel
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(convert_one, inp, outp): (inp, outp)
            for inp, outp in tasks
        }

        for future in concurrent.futures.as_completed(future_to_task):
            inp, outp = future_to_task[future]
            try:
                input_path, output_path, success, error_msg = future.result()
                if success:
                    completed += 1
                    progress_tracker.add_log(task_id, "info", f"[{completed}/{total}] Completed: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")

                    # Update progress based on completion percentage
                    progress_percent = int(5 + (completed / total) * 5)  # Audio extraction takes 5% of total progress
                    progress_tracker.update_task_progress(task_id, progress_percent, f"Converting audio: {os.path.basename(input_path)}", int((completed/total)*100))

                    # Add more detailed progress update
                    progress_tracker.update_task_progress(
                        task_id,
                        progress_percent,
                        f"Converting audio: {completed}/{total} files completed",
                        int((completed/total)*100)
                    )
                else:
                    progress_tracker.add_log(task_id, "error", f"[Error] {os.path.basename(input_path)} conversion failed:\n{error_msg}")

                    # Still update progress even when a file fails
                    progress_tracker.update_task_progress(
                        task_id,
                        int(5 + (completed / total) * 5),
                        f"Converting audio: {completed}/{total} files completed (some failed)",
                        int((completed/total)*100)
                    )
            except Exception as e:
                progress_tracker.add_log(task_id, "error", f"[Exception] Unknown error processing {os.path.basename(inp)}: {e}")

                # Still update progress even when there's an exception
                progress_tracker.update_task_progress(
                    task_id,
                    int(5 + (completed / total) * 5),
                    f"Converting audio: {completed}/{total} files completed (with errors)",
                    int((completed/total)*100)
                )

    print(f"All tasks completed! Successfully converted {completed} files.")

def process_multiple_videos(input_folder: str, output_folder: str, video_language: str = "en", master_task_id: str = None) -> List[Tuple[str, str]]:
    """
    Process multiple videos, each with its own task ID
    If master_task_id is provided, log the new task creation to the master task
    Returns a list of (video_filename, task_id) tuples
    """
    try:
        # Validate input folder exists
        if not os.path.exists(input_folder):
            raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

        # Walk through directory to find all MP4 files
        video_files = []
        for root, dirs, files in os.walk(input_folder):
            for file in files:
                if file.lower().endswith('.mp4'):
                    full_path = os.path.join(root, file)
                    video_files.append(full_path)

        if len(video_files) == 0:
            print(f"No MP4 files found in {input_folder}")
            return []

        # Create and start a thread for each video
        threads = []
        task_info = []  # Store (video_filename, task_id) pairs

        for video_path in video_files:
            # Generate a unique task ID for each video
            task_id = str(uuid.uuid4())

            # If there's a master task, log this new task creation
            if master_task_id:
                video_name = os.path.basename(video_path)
                progress_tracker.add_log(master_task_id, "info", f"NEW_TASK_CREATED:{task_id}:{video_name}")

            # Create a thread to process this specific video
            thread = threading.Thread(
                target=process_single_video,
                args=(video_path, task_id, input_folder, output_folder, video_language)
            )

            thread.start()
            threads.append(thread)
            task_info.append((os.path.basename(video_path), task_id))

            print(f"Started processing for {os.path.basename(video_path)} with task ID: {task_id}")

        
        return task_info

    except Exception as e:
        print(f"Error in process_multiple_videos: {str(e)}")
        return []


def process_videos(task_id: str, input_folder: str, output_folder: str, video_language: str = "en"):
    """
    Process videos from input folder and save results to output folder
    If there are multiple videos in the input folder, each will be assigned its own task ID
    """
    print(f"[processor] progress_tracker id: {id(progress_tracker)}, type: {type(progress_tracker)}")

    # Normalize paths to handle potential Windows path issues
    output_folder1=output_folder
    input_folder = os.path.normpath(input_folder)
    output_folder = os.path.normpath(output_folder)

    # Check how many MP4 files exist in the input folder
    video_files = []
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith('.mp4'):
                full_path = os.path.join(root, file)
                video_files.append(full_path)

    # If there are multiple videos, delegate to the multiple video processing function
    if len(video_files) > 1:
        print(f"Found {len(video_files)} videos, processing each with individual task IDs")

        # For backward compatibility, update the main task to indicate delegation
        progress_tracker.update_task_progress(task_id, 0, f"Delegating {len(video_files)} videos to individual tasks", 0)
        progress_tracker.add_log(task_id, "info", f"Found {len(video_files)} videos, creating individual tasks for each")

        # Process each video with its own task ID, passing the master task ID so it can be logged
        task_info = process_multiple_videos(input_folder, output_folder, video_language, task_id)

        # Report the task IDs created
        task_ids = [info[1] for info in task_info]
        progress_tracker.add_log(task_id, "info", f"Created individual tasks: {task_ids}")

        # Track child tasks and update main task progress based on their completion
        import time
        total_videos = len(video_files)

        # Update the main task to show we're monitoring child tasks
        progress_tracker.update_task_progress(task_id, 1, f"Monitoring {len(video_files)} individual tasks", 0)

        # Monitor child tasks until all are completed
        last_update_time = time.time()  # Track last update time to reduce frequency
        last_progress = 0  # Track last progress to avoid redundant updates

        while True:
            completed_tasks = 0
            failed_tasks = 0

            # Count completed and failed tasks
            for _, child_task_id in task_info:
                if child_task_id in progress_tracker.tasks:
                    child_task_status = progress_tracker.get_task_status(child_task_id)
                    if child_task_status.get('status') == 'completed':
                        completed_tasks += 1
                    elif child_task_status.get('status') == 'failed':
                        failed_tasks += 1

            # Calculate overall progress based on child task completion
            current_overall = int((completed_tasks + failed_tasks) / total_videos * 100)

            # Only update main task progress when there's a meaningful change or every 5 seconds
            current_time = time.time()
            if current_overall > last_progress or (current_time - last_update_time >= 5):
                # Update main task progress
                progress_tracker.update_task_progress(
                    task_id,
                    min(99, current_overall),  # Keep at 99% until all are done
                    f"Monitoring: {completed_tasks}/{total_videos} completed, {failed_tasks}/{total_videos} failed",
                    int((completed_tasks + failed_tasks) / total_videos * 100)
                )
                last_progress = current_overall
                last_update_time = current_time

            # Check if all tasks are completed
            if completed_tasks + failed_tasks >= total_videos:
                break

            # Sleep briefly before next check
            time.sleep(0.5)  # Check every 0.5 seconds but only update UI when necessary

        # Complete the main task after all children finish
        progress_tracker.update_task_progress(task_id, 100, f"Completed {len(video_files)} individual tasks", 100)
        progress_tracker.complete_task(task_id, True, f"Completed processing {len(video_files)} videos with {completed_tasks} successful and {failed_tasks} failed")

        return

    # If only one video, use the existing logic
    else:
        # Proceed with single video processing using the original logic
        try:
            # Update initial status to show processing has actually started
            progress_tracker.update_task_progress(task_id, 2, "Starting video processing - validating folders", 0)
            progress_tracker.add_log(task_id, "info", f"Starting to process videos in {input_folder}")

            # Validate input folder exists
            if not os.path.exists(input_folder):
                error_msg = f"Input folder does not exist: {input_folder}"
                progress_tracker.add_log(task_id, "error", error_msg)
                progress_tracker.complete_task(task_id, False, error_msg)
                return

            # Validate input folder is accessible
            try:
                os.listdir(input_folder)  # Test if we can list the directory
            except PermissionError:
                error_msg = f"No permission to access input folder: {input_folder}"
                progress_tracker.add_log(task_id, "error", error_msg)
                progress_tracker.complete_task(task_id, False, error_msg)
                return
            except OSError as e:
                error_msg = f"Error accessing input folder: {input_folder}, Error: {str(e)}"
                progress_tracker.add_log(task_id, "error", error_msg)
                progress_tracker.complete_task(task_id, False, error_msg)
                return

            # Validate output folder exists (create if needed)
            os.makedirs(output_folder, exist_ok=True)

            progress_tracker.update_task_progress(task_id, 5, "Scanning for MP4 files", 0)

            # Instead of using os.listdir which may hang in threads on Windows, use os.walk which is more reliable
            video_files = []

            # Walk through directory to find all MP4 files
            scanned_dirs = 0
            for root, dirs, files in os.walk(input_folder):
                scanned_dirs += 1

                # Update progress periodically during directory traversal
                if scanned_dirs % 5 == 0:  # Update every 5 directories
                    progress_tracker.update_task_progress(
                        task_id,
                        5,
                        f"Scanning directories... processed {scanned_dirs} directories",
                        0
                    )

                    # Yield control briefly to allow other threads to run
                    import time
                    time.sleep(0.01)  # Sleep briefly to allow other threads to run

                for file in files:
                    if file.lower().endswith('.mp4'):
                        full_path = os.path.join(root, file)
                        video_files.append(full_path)
                        progress_tracker.add_log(task_id, "info", f"Found video file: {full_path}")

                        # Update progress periodically during scanning
                        if len(video_files) % 5 == 0:  # Update every 5 files found
                            progress_tracker.update_task_progress(
                                task_id,
                                5,
                                f"Scanning... found {len(video_files)} MP4 file{'s' if len(video_files) != 1 else ''}",
                                0
                            )

                            # Yield control briefly to allow other threads to run
                            time.sleep(0.01)  # Sleep briefly to allow other threads to run

            progress_tracker.update_task_progress(task_id, 5, f"Found {len(video_files)} video file to process", 0)
            progress_tracker.add_log(task_id, "info", f"Total MP4 files found: {len(video_files)}")

            if len(video_files) == 0:
                progress_tracker.add_log(task_id, "warning", "No MP4 files found in the input folder")
                progress_tracker.complete_task(task_id, True, "No videos to process")
                return

            # Create subdirectories for each video and process them
            total_videos = len(video_files)
            processed_count = 0

            for i, video_path in enumerate(video_files):
                video_name = os.path.basename(video_path)

                # Update progress for this video
                progress_tracker.update_task_progress(
                    task_id,
                    int(5 + (i / total_videos) * 5),  # Distribute first 10% among setup tasks
                    f"Setting up for video {i+1}/{total_videos}: {video_name}",
                    0
                )

                # Extract video name without extension for folder creation
                video_base_name = os.path.splitext(video_name)[0]
                video_output_dir = os.path.join(output_folder, video_base_name)
                os.makedirs(video_output_dir, exist_ok=True)

                # Create a temporary directory for captures specific to this video
                capture_output_path = os.path.join(video_output_dir, "captureTemp")
                os.makedirs(capture_output_path, exist_ok=True)

                # Convert video to audio first
                audio_path = os.path.join(video_output_dir, video_base_name + ".mp3")  # Changed to put audio in video's output dir

                # Check if audio file already exists
                if not os.path.exists(audio_path):
                    # Update progress for audio extraction - this is typically the most time-consuming part
                    audio_start_progress = 5
                    audio_end_progress = 10
                    progress_range = audio_end_progress - audio_start_progress

                    progress_tracker.update_task_progress(
                        task_id,
                        int(audio_start_progress + (i / total_videos) * progress_range * 0.05),  # 5% of audio progress at start
                        f"正在拆分音频: {video_name}",
                        0
                    )

                    progress_tracker.add_log(task_id, "info", f"Starting audio extraction for {video_name} using ffmpeg")

                    # Use ffmpeg to convert video to audio
                    # Normalize the paths for the subprocess call
                    cmd = [
                        get_ffmpeg_path(),
                        "-i", os.path.normpath(video_path),
                        "-vn",
                        "-acodec", "libmp3lame",
                        "-b:a", "192k",
                        "-y",
                        os.path.normpath(audio_path)
                    ]

                    try:
                        progress_tracker.update_task_progress(
                            task_id,
                            int(audio_start_progress + (i / total_videos) * progress_range * 0.05),
                            f"正在拆分音频 ({video_name}) - 开始转换...",
                            0
                        )

                        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=1800)
                        progress_tracker.add_log(task_id, "info", f"Successfully extracted audio: {video_name}")

                        progress_tracker.update_task_progress(
                            task_id,
                            int(audio_start_progress + (i / total_videos) * progress_range),  # Full audio progress for this video
                            f"正在拆分音频 ({video_name}) - 转换完成",
                            100
                        )
                    except subprocess.TimeoutExpired:
                        error_details = "Audio extraction timed out after 30 minutes"
                        progress_tracker.add_log(task_id, "error", f"Audio extraction failed for {video_name}: {error_details}")
                        continue  # Skip this video if audio extraction fails
                    except subprocess.CalledProcessError as e:
                        error_details = f"Return code: {e.returncode}, Error: {e.stderr[:200]}..." if len(e.stderr) > 200 else f"Return code: {e.returncode}, Error: {e.stderr}"
                        progress_tracker.add_log(task_id, "error", f"Audio extraction failed for {video_name}: {error_details}")
                        continue  # Skip this video if audio extraction fails
                else:
                    progress_tracker.add_log(task_id, "info", f"Using existing audio file: {audio_path}")

                    # Update progress for using existing audio file - transition to analysis phase
                    analysis_start_progress = 10
                    analysis_end_progress = 20
                    progress_range = analysis_end_progress - analysis_start_progress

                    progress_tracker.update_task_progress(
                        task_id,
                        int(analysis_start_progress + (i / total_videos) * progress_range),  # Move to analysis phase
                        f"使用已有音频: {video_name}",
                        100
                    )

                # Process the lecture video
                try:
                    progress_tracker.add_log(task_id, "info", f"Starting AI processing for {video_name}")
                    print("start")

                    # Update progress before starting AI processing - covers 10%-95% range of skip_this_lecture
                    ai_start_progress = 10
                    ai_end_progress = 95
                    progress_range = ai_end_progress - ai_start_progress

                    progress_tracker.update_task_progress(
                        task_id,
                        int(ai_start_progress + (i / total_videos) * progress_range * 0.1),  # Start at 10% of AI progress for this video
                        f"正在处理视频: {video_name}",  # 更通用的状态描述
                        0
                    )

                    skip_this_lecture(
                        video_path=video_path,
                        language=video_language,
                        audio_path=audio_path,
                        outputDir=video_output_dir,
                        capture_output_path=capture_output_path,
                        task_id=task_id
                    )

                    processed_count += 1
                    progress_tracker.add_log(task_id, "info", f"Completed processing: {video_name}")
                    try:
                        # 清理输出文件，将各个子文件夹中的 resume.txt 移动到主输出目录并重命名
                        progress_tracker.add_log(task_id, "info", f"Cleaning up {video_name}")
                        cleanup_output_files(output_folder1)
                    except Exception as e:
                        progress_tracker.add_log(task_id, "error", f"Error cleaning up output files: {str(e)}")

                    # Update progress after completing this video - but don't complete the task yet
                    progress_tracker.update_task_progress(
                        task_id,
                        100,
                        f"Completed processing {video_name}, continuing with next videos...",
                        100
                    )
                    progress_tracker.complete_task(task_id, True, f"Successfully processed {processed_count} of {total_videos} videos")

                except Exception as e:
                    error_msg = f"Error processing {video_name}: {str(e)}"
                    progress_tracker.add_log(task_id, "error", error_msg)

                    # Update progress to reflect the error but continue with next video
                    progress_tracker.update_task_progress(
                        task_id,
                        int(10 + ((i + 1) / total_videos) * 85),  # Move to next video's progress slot based on new range
                        f"Error processing {video_name}, continuing...",
                        0
                    )
                    progress_tracker.complete_task(task_id, False, f"Error")
                    continue  # Continue with next video even if this one fails
            

        except Exception as e:
            error_msg = f"Critical error in process_videos: {str(e)}"
            progress_tracker.add_log(task_id, "error", error_msg)
            progress_tracker.complete_task(task_id, False, f"Processing failed: {str(e)}")