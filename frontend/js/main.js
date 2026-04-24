// 主页面逻辑
document.addEventListener('DOMContentLoaded', () => {
  // DOM元素引用
  const processForm = document.getElementById('process-form');
  const inputFolderInput = document.getElementById('input-folder');
  const outputFolderInput = document.getElementById('output-folder');
  const languageSelect = document.getElementById('language');
  const currentTaskDiv = document.getElementById('current-task');
  const taskHistoryDiv = document.getElementById('task-history');
  const refreshStatusBtn = document.getElementById('refresh-status');

  // 任务相关的变量
  let activeTasks = new Map(); // 使用Map来跟踪所有活跃任务
  let webSocketClients = new Map(); // 存储WebSocket客户端
  let taskHistory = [];

  // 页面加载时获取默认设置填充表单
  initializeForm();
  // 恢复之前未完成的任务状态
  restoreTasksFromBackend();

  // 表单提交事件
  processForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const inputFolder = inputFolderInput.value.trim();
    const outputFolder = outputFolderInput.value.trim();
    const language = languageSelect.value;

    if (!inputFolder || !outputFolder) {
      alert('请输入输入和输出文件夹路径');
      return;
    }

    try {
      // 禁用表单防止重复提交
      disableForm(true);

      // 开始处理任务
      const response = await apiClient.startProcessing(inputFolder, outputFolder, language);
      const masterTaskId = response.task_id;

      // 添加主任务到活跃任务列表
      activeTasks.set(masterTaskId, response);

      // 更新UI显示当前任务（所有活跃任务）
      updateAllActiveTasksDisplay();

      // 为主任务连接WebSocket - 这将处理动态任务发现
      connectToWebSocket(masterTaskId);

      // 重置表单
      processForm.reset();

    } catch (error) {
      console.error('启动处理任务失败:', error);
      alert(`启动处理任务失败: ${error.message}`);
    } finally {
      disableForm(false);
    }
  });

  // 页面加载时从后端恢复未完成的任务
  async function restoreTasksFromBackend() {
    try {
      const allTasks = await apiClient.getAllTasks();
      if (!allTasks || Object.keys(allTasks).length === 0) {
        return;
      }

      for (const [taskId, taskData] of Object.entries(allTasks)) {
        // 跳过主协调任务
        if (isCoordinatorTask(taskData)) {
          continue;
        }

        if (taskData.status === 'initialized' || taskData.status === 'processing') {
          // 恢复为活跃任务并重连WebSocket
          activeTasks.set(taskId, taskData);
          connectToWebSocket(taskId);
        } else if (taskData.status === 'completed' || taskData.status === 'failed') {
          // 恢复到历史记录，保留原始完成时间
          taskData.timestamp = taskData.updated_at || taskData.created_at || new Date().toISOString();
          addToTaskHistory(taskData, true);
        }
      }

      updateAllActiveTasksDisplay();
    } catch (error) {
      console.warn('恢复任务状态失败:', error);
    }
  }

  function isCoordinatorTask(taskData) {
    if (!taskData.current_step) return false;
    return taskData.current_step.includes("Coordinated") ||
           taskData.current_step.includes("Delegating") ||
           taskData.current_step.includes("Monitoring") ||
           taskData.current_step.includes("Processing:") ||
           taskData.current_step.includes("Processing :") ||
           (taskData.current_step.includes("Completed") && taskData.current_step.includes("individual tasks"));
  }

  // 监听个体任务的创建
  async function listenForIndividualTasks(masterTaskId) {
    // 目前不再需要定期轮询，因为我们通过WebSocket消息处理来发现新任务
    // 这里可以放置其他需要的监听逻辑
  }

  // 刷新状态按钮事件
  refreshStatusBtn.addEventListener('click', async () => {
    // 为每个活跃任务刷新状态
    for (const [taskId] of activeTasks) {
      try {
        const status = await apiClient.getTaskStatus(taskId);

        // 更新任务状态，但只在新状态比较新时才更新
        const existingTask = activeTasks.get(taskId);
        if (existingTask && existingTask.updated_at && status.updated_at) {
          // 如果API返回的状态比现有状态旧，则跳过更新
          if (new Date(existingTask.updated_at) > new Date(status.updated_at)) {
            console.log(`Skipping older status update for task ${taskId}`);
            continue;
          }
        }

        // 更新任务状态
        if (activeTasks.has(taskId)) {
          // 保留原始的输入/输出文件夹信息
          status.input_folder = existingTask.input_folder || status.input_folder;
          status.output_folder = existingTask.output_folder || status.output_folder;
        }

        activeTasks.set(taskId, status);

        // 更新UI
        updateAllActiveTasksDisplay();
      } catch (error) {
        console.error(`获取任务 ${taskId} 状态失败:`, error);
      }
    }
  });

  // 初始化表单函数
  async function initializeForm() {
    try {
      const settings = await apiClient.getSettings();
      if (settings && settings.folders) {
        if (settings.folders.default_input) {
          inputFolderInput.value = settings.folders.default_input;
        }
        if (settings.folders.default_output) {
          outputFolderInput.value = settings.folders.default_output;
        }
      }
    } catch (error) {
      console.warn('获取默认设置失败:', error);
      // 继续执行，不阻塞页面加载
    }
  }

  // 禁用/启用表单
  function disableForm(disabled) {
    const inputs = processForm.querySelectorAll('input, select, button[type="submit"]');
    inputs.forEach(input => {
      input.disabled = disabled;
    });
  }

  // 更新所有活跃任务显示
  function updateAllActiveTasksDisplay() {
    // 清空当前任务显示
    currentTaskDiv.innerHTML = '';

    if (activeTasks.size === 0) {
      currentTaskDiv.innerHTML = '<p class="no-task-message">没有正在进行的任务</p>';
      return;
    }

    // 为每个活跃任务创建显示元素
    for (const [taskId, taskData] of activeTasks) {
      // 过滤掉主协调任务，只显示实际的视频处理任务
      // 这次我们完全过滤掉主协调任务，无论它们是否已完成
      if (taskData.current_step &&
          (taskData.current_step.includes("Coordinated") ||
           taskData.current_step.includes("Delegating") ||
           taskData.current_step.includes("Monitoring") ||
           taskData.current_step.includes("Processing:") ||
           taskData.current_step.includes("Processing :") ||
           taskData.current_step.includes("Completed") && taskData.current_step.includes("individual tasks"))) {
        continue; // 跳过主协调任务的显示
      }

      const taskElement = createTaskElement(taskData);
      currentTaskDiv.appendChild(taskElement);
    }

    // 如果没有有效的任务显示，显示提示信息
    if (currentTaskDiv.children.length === 0) {
      currentTaskDiv.innerHTML = '<p class="no-task-message">没有正在进行的任务</p>';
    }
  }

  // 辅助函数：从路径中提取文件名
  function extractFileName(filePath) {
    // 处理各种路径分隔符（Windows和Unix风格）
    const fileName = filePath.replace(/.*[/\\]/, '');
    return fileName || filePath; // 如果没有找到路径分隔符，返回原字符串
  }

  // 创建单个任务元素
  function createTaskElement(taskData) {
    const taskElement = document.createElement('div');
    taskElement.className = 'task-info';

    // 根据状态设置不同的样式
    const statusClass = `status-${taskData.status}`;
    // 使用增强版状态文本，根据进度细分状态
    const statusText = getStatusText(taskData.status, taskData.overall_progress);

    // 提取视频名称（从current_step中或从任务ID中推断）
    let videoName = '未知视频';

    // 首先检查任务日志中是否有关于视频名称的信息
    if (taskData.logs && taskData.logs.length > 0) {
      // 查找包含 "开始处理视频" 的日志条目
      for (let i = taskData.logs.length - 1; i >= 0; i--) {
        const log = taskData.logs[i];
        const match = log.message.match(/开始处理视频: ([^,，]+)/);
        if (match) {
          videoName = extractFileName(match[1]); // 从路径中提取文件名
          break;
        }
      }
    }

    // 如果日志中没有找到视频名，再从current_step中尝试提取
    if (videoName === '未知视频' && taskData.current_step) {
      // 尝试从当前步骤中提取视频名称
      const match = taskData.current_step.match(/开始处理视频: ([^,，]+)/);
      if (match) {
        videoName = extractFileName(match[1]); // 从路径中提取文件名
      } else {
        // 尝试从current_step中提取视频文件名 - 检查是否有视频相关的描述
        const videoMatch = taskData.current_step.match(/([a-zA-Z0-9_\-一-龥]+\.(mp4|avi|mov|mkv|wmv|flv|webm))/);
        if (videoMatch) {
          videoName = extractFileName(videoMatch[1]); // 从路径中提取文件名
        } else {
          // 作为最后的备选，使用任务ID的前几个字符（可能不是理想方案）
          // 但我们优先保留当前步骤名称而不显示错误的格式
          videoName = '处理中的视频';
        }
      }
    }

    taskElement.innerHTML = `
      <div class="task-id">${videoName}</div>
      <div class="current-step">${taskData.current_step || '等待开始...'}</div>
      <div class="progress-container">
        <div class="progress-bar">
          <div class="progress-value" style="width: ${taskData.overall_progress}%"></div>
        </div>
        <div class="progress-text">${taskData.overall_progress}% 完成</div>
      </div>
      <div class="status-info">
        <span class="status-badge ${statusClass}">
          ${statusText}
        </span>
        <small>任务ID: ${taskData.task_id.substring(0, 8)}...</small>
      </div>
    `;

    // 如果有日志，添加日志部分
    if (taskData.logs && taskData.logs.length > 0) {
      const logsContainer = document.createElement('div');
      logsContainer.className = 'logs-container';

      // 过滤掉主协调任务相关的日志条目，然后显示最近的5条日志
      const filteredLogs = taskData.logs.filter(log =>
        !log.message.includes("NEW_TASK_CREATED") &&
        !log.message.includes("Created individual tasks") &&
        !(log.message.includes("Found") && log.message.includes("videos") && log.message.includes("creating"))
      ).slice(-5); // 只取过滤后的最后5条日志

      // 如果没有过滤后的日志，则显示原始日志的最后5条
      const logsToShow = filteredLogs.length > 0 ? filteredLogs : taskData.logs.slice(-5);

      logsToShow.forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${log.level}`;
        logEntry.innerHTML = `
          <span class="log-timestamp">${formatTimestamp(log.timestamp)}</span>
          <span>[${log.level.toUpperCase()}]</span>
          <span>${log.message}</span>
        `;
        logsContainer.appendChild(logEntry);
      });

      taskElement.appendChild(logsContainer);
    }

    return taskElement;
  }

  // 添加到任务历史
  function addToTaskHistory(taskData, preserveTimestamp = false) {
    // 添加时间戳，恢复时保留原始时间
    if (!preserveTimestamp) {
      taskData.timestamp = new Date().toISOString();
    }

    // 防止重复添加
    const existingIndex = taskHistory.findIndex(task => task.task_id === taskData.task_id);
    if (existingIndex !== -1) {
      // 如果任务已完成或失败，替换现有的条目
      // 如果任务还在进行中，只在状态更新更大或更新时间更新时更新
      const existingTask = taskHistory[existingIndex];
      if (taskData.status === 'completed' || taskData.status === 'failed' ||
          taskData.overall_progress > existingTask.overall_progress ||
          (existingTask.updated_at && taskData.updated_at &&
           new Date(existingTask.updated_at) < new Date(taskData.updated_at))) {
        taskHistory[existingIndex] = taskData; // 更新现有条目
      }
    } else {
      taskHistory.unshift(taskData); // 添加到开头
    }

    // 只保留最近10个任务
    if (taskHistory.length > 10) {
      taskHistory = taskHistory.slice(0, 10);
    }

    updateTaskHistoryDisplay();
  }

  // 更新任务历史显示
  function updateTaskHistoryDisplay() {
    // 过滤掉主协调任务，只显示实际的视频处理任务
    // 这次我们完全过滤掉主协调任务，无论它们是否已完成
    const filteredHistory = taskHistory.filter(task =>
      !(task.current_step &&
        (task.current_step.includes("Coordinated") ||
         task.current_step.includes("Delegating") ||
         task.current_step.includes("Monitoring") ||
         task.current_step.includes("Processing:") ||
         task.current_step.includes("Processing :") ||
         task.current_step.includes("Completed") && task.current_step.includes("individual tasks")))
    );

    if (filteredHistory.length === 0) {
      taskHistoryDiv.innerHTML = '<p class="no-tasks-message">暂无任务历史</p>';
      return;
    }

    const historyHtml = filteredHistory.map(task => {
      const statusClass = `status-${task.status}`;
      // 使用增强版状态文本，根据进度细分状态
      const statusText = getStatusText(task.status, task.overall_progress);

      // 提取视频名称
      let videoName = '未知视频';

      // 首先检查任务日志中是否有关于视频名称的信息
      if (task.logs && task.logs.length > 0) {
        // 查找包含 "开始处理视频" 的日志条目
        for (let i = task.logs.length - 1; i >= 0; i--) {
          const log = task.logs[i];
          const match = log.message.match(/开始处理视频: ([^,，]+)/);
          if (match) {
            videoName = extractFileName(match[1]); // 从路径中提取文件名
            break;
          }
        }
      }

      // 如果日志中没有找到视频名，再从current_step中尝试提取
      if (videoName === '未知视频' && task.current_step) {
        const match = task.current_step.match(/开始处理视频: ([^,，]+)/);
        if (match) {
          videoName = extractFileName(match[1]); // 从路径中提取文件名
        } else {
          // 尝试从current_step中提取视频文件名 - 检查是否有视频相关的描述
          const videoMatch = task.current_step.match(/([a-zA-Z0-9_\-一-龥]+\.(mp4|avi|mov|mkv|wmv|flv|webm))/);
          if (videoMatch) {
            videoName = extractFileName(videoMatch[1]); // 从路径中提取文件名
          } else {
            videoName = '处理中的视频';
          }
        }
      }

      return `
        <div class="task-info">
          <div class="task-id">${videoName}</div>
          <div><strong>状态:</strong> <span class="status-badge ${statusClass}">${statusText}</span></div>
          <div><strong>进度:</strong> ${task.overall_progress}%</div>
          <div><strong>步骤:</strong> ${task.current_step || 'N/A'}</div>
          <small>任务ID: ${task.task_id.substring(0, 8)}... | ${formatTimestamp(task.timestamp)}</small>
        </div>
      `;
    }).join('');

    taskHistoryDiv.innerHTML = historyHtml;
  }

  // 连接到WebSocket以获取实时进度
  function connectToWebSocket(taskId) {
  // 如果已存在连接，则先断开
  if (webSocketClients.has(taskId)) {
    disconnectWebSocket(taskId);
  }

  // 创建新的WebSocket连接
  const webSocketClient = new WebSocketClient(taskId);

  webSocketClient.onMessage = (data) => {
    console.log('Received WebSocket message:', data);

    // 1. 首先处理 NEW_TASK_CREATED 消息（如果有）
    if (data.logs) {
      data.logs.forEach(log => {
        if (log.message && log.message.startsWith("NEW_TASK_CREATED:")) {
          const parts = log.message.split(":");
          if (parts.length >= 3) {
            const newTaskId = parts[1];
            const videoName = parts[2];

            // 若任务已存在则跳过，防止重复创建
            if (activeTasks.has(newTaskId)) {
              console.log(`Task ${newTaskId} already exists, skipping creation`);
              return;
            }

            // 创建新任务对象
            const newTask = {
              task_id: newTaskId,
              current_step: `开始处理视频: ${videoName}`,
              overall_progress: 0,
              status: 'processing',
              input_folder: data.input_folder,
              output_folder: data.output_folder,
              logs: []
            };

            // 添加到活跃任务列表
            activeTasks.set(newTaskId, newTask);

            // 连接到新任务的WebSocket
            connectToWebSocket(newTaskId);
          }
        }
      });
    }

    // 2. 获取当前任务的已存储状态
    const existingTask = activeTasks.get(taskId);

    // 3. 时间戳检查：防止旧消息覆盖新消息
    if (existingTask && existingTask.updated_at && data.updated_at) {
      if (new Date(existingTask.updated_at) > new Date(data.updated_at)) {
        console.log(`Ignoring older status update for task ${taskId}`);
        return;
      }
    }

    // 4. 进度回退检查
    if (existingTask && data.overall_progress < existingTask.overall_progress &&
        data.status !== 'initialized' && data.status !== 'failed') {
      console.log(`Progress decreased from ${existingTask.overall_progress}% to ${data.overall_progress}% for task ${taskId}, maintaining previous progress`);
      data.overall_progress = existingTask.overall_progress;
      data.current_step = existingTask.current_step;
    }

    // 🔥 新增：防止乱序的初始化消息（进度0且步骤是“开始处理视频”）覆盖已有真实进度
    if (existingTask) {
      const isInitMessage = data.overall_progress === 0 &&
                            data.current_step &&
                            data.current_step.includes('开始处理视频');
      const hasValidProgress = existingTask.overall_progress > 0 ||
                               (existingTask.current_step && !existingTask.current_step.includes('开始处理视频'));

      if (isInitMessage && hasValidProgress) {
        console.log(`Ignoring out-of-order init message for task ${taskId}`);
        return;   // 直接忽略，不更新 activeTasks
      }
    }

    // 5. 更新任务数据
    activeTasks.set(taskId, data);

    // 6. 任务完成或失败时断开连接
    if (data.status === 'completed' || data.status === 'failed') {
      disconnectWebSocket(taskId);
    }

    // 7. 节流更新 UI
    updateAllActiveTasksDisplayThrottled();

    // 8. 添加到历史记录
    addToTaskHistory(data);
  };

  webSocketClient.onError = (error) => {
    console.error(`WebSocket错误 for task ${taskId}:`, error);
  };

  webSocketClient.onClose = () => {
    console.log(`WebSocket连接已关闭 for task ${taskId}`);

    const currentTaskData = activeTasks.get(taskId);
    if (currentTaskData && currentTaskData.status === 'processing') {
      currentTaskData.current_step = currentTaskData.current_step || '连接已断开';
      activeTasks.set(taskId, currentTaskData);
    }

    webSocketClients.delete(taskId);
    updateAllActiveTasksDisplay();
  };

  webSocketClient.connect();
  webSocketClients.set(taskId, webSocketClient);
}

  // 断开WebSocket连接
  function disconnectWebSocket(taskId) {
    if (webSocketClients.has(taskId)) {
      const client = webSocketClients.get(taskId);
      if (client && client.ws && client.ws.readyState === WebSocket.OPEN) {
        client.disconnect();
      }
      webSocketClients.delete(taskId);
    }
  }

  // 辅助函数：获取状态文本
  function getStatusText(status, progress = 0) {
    if (status === 'initialized') {
      return '已开始';
    } else if (status === 'completed') {
      return '已完成';
    } else if (status === 'failed') {
      return '失败';
    } else if (status === 'processing') {
      // 根据进度确定更详细的状态
      if (progress >= 80) {
        return '接近完成';
      } else {
        return '进行中';
      }
    }
    return status;
  }

  // 辅助函数：格式化时间戳
  function formatTimestamp(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN');
  }

  // 辅助函数：截断长路径
  function truncatePath(path, maxLength) {
    if (!path || path.length <= maxLength) return path;
    return '...' + path.substring(path.length - maxLength + 3);
  }

  // 节流函数，限制UI更新频率以提高性能
  let uiUpdateTimeout = null;
  let pendingUiUpdate = false;

  function updateAllActiveTasksDisplayThrottled() {
    if (uiUpdateTimeout) {
      // 如果已经有待处理的更新，标记为待更新
      pendingUiUpdate = true;
    } else {
      // 执行更新
      updateAllActiveTasksDisplay();

      // 设置定时器，防止过于频繁的更新
      uiUpdateTimeout = setTimeout(() => {
        uiUpdateTimeout = null;
        if (pendingUiUpdate) {
          pendingUiUpdate = false;
          // 如果在此期间又有更新需求，执行一次额外的更新
          updateAllActiveTasksDisplayThrottled();
        }
      }, 200); // 200ms节流延迟
    }
  }
});