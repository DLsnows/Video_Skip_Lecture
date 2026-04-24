# 视频处理平台

这是一个基于AI的视频处理平台，可以自动将视频转换为Markdown格式的文字讲解。支持语音转文字、OCR识别和大语言模型分析。

## 功能特性

- 视频音频提取和语音转文字
- 视频帧OCR识别
- AI内容分析和整理
- 多任务进度监控
- 响应式极简暗色前端
- 可配置的API提供商

## 技术架构

- 后端：Python + FastAPI
- 前端：HTML/CSS/JavaScript (极简暗色主题)
- 数据库：无 (使用内存存储任务状态)
- AI服务：支持多种API提供商 (DeepInfra, DeepSeek等)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements1.txt
```

### 2. 配置API密钥

首次运行前，请配置所需的API密钥，默认url和model可以随意更改，在 `config.json` 中设置：

```json
{
  "transcription_provider": {
    "base_url": "https://api.deepinfra.com/v1/openai",
    "api_key": "your-transcription-api-key",
    "model": "openai/whisper-large-v3"
  },
  "ocr_provider": {
    "base_url": "https://api.deepinfra.com/v1/openai",
    "api_key": "your-ocr-api-key",
    "model": "deepseek-ai/DeepSeek-OCR"
  },
  "summarization_provider": {
    "base_url": "https://api.deepseek.com",
    "api_key": "your-summarization-api-key",
    "model": "deepseek-reasoner"
  }
}
```

### 3. 启动服务

```bash
python main.py
```

服务器将在 http://127.0.0.1:8001 上运行

### 4. 访问应用

打开浏览器访问 http://127.0.0.1:8001 查看前端界面

## 前端功能

- **主页**: 提交视频处理任务，实时监控进度
- **设置页**: 配置API提供商和文件夹路径
- **任务历史**: 查看以前的处理任务
- **实时进度**: 通过WebSocket获取任务进度更新

## API端点

- `POST /api/v1/process` - 开始视频处理任务
- `GET /api/v1/status/{task_id}` - 获取任务状态
- `WS /api/v1/ws/progress/{task_id}` - WebSocket实时进度
- `GET /api/v1/settings` - 获取当前设置
- `PUT /api/v1/settings` - 更新设置

## 项目结构

```
video_skip_backend/
├── main.py              # 主应用入口
├── api/
│   └── routes.py        # API路由定义
├── core/
│   └── processor.py     # 核心视频处理逻辑
├── utils/
│   └── progress_tracker.py # 进度跟踪工具
├── config/
│   └── config_manager.py # 配置管理
├── frontend/            # 前端文件
│   ├── index.html       # 主页面
│   ├── settings.html    # 设置页面
│   ├── css/style.css    # 样式文件
│   └── js/              # JavaScript文件
└── config.json          # 配置文件
```

## 使用说明

1. 在设置页面配置API提供商的Base URL和API密钥
2. 在主页设置输入和输出文件夹
3. 在主页填写视频处理任务的参数
4. 点击"开始处理"按钮启动任务
5. 通过实时进度条和日志监控处理过程

## 浏览器兼容性

支持现代浏览器 (Chrome, Firefox, Safari, Edge)