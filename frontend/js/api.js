// API客户端
class APIClient {
  constructor(baseURL = '/api/v1') {
    this.baseURL = baseURL;
  }

  // 通用请求方法
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `HTTP error! Status: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error(`API request failed: ${error.message}`);
      throw error;
    }
  }

  // 开始视频处理任务
  async startProcessing(inputFolder, outputFolder, videoLanguage = 'en') {
    return this.request('/process', {
      method: 'POST',
      body: JSON.stringify({
        input_folder: inputFolder,
        output_folder: outputFolder,
        video_language: videoLanguage,
      }),
    });
  }

  // 获取所有任务
  async getAllTasks() {
    return this.request('/tasks');
  }

  // 获取任务状态
  async getTaskStatus(taskId) {
    return this.request(`/status/${taskId}`);
  }

  // 获取当前设置
  async getSettings() {
    return this.request('/settings');
  }

  // 更新设置
  async updateSettings(settings) {
    return this.request('/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }
}

// WebSocket客户端用于实时进度更新
class WebSocketClient {
  constructor(taskId) {
    this.taskId = taskId;
    this.ws = null;
    this.onMessage = null;
    this.onError = null;
    this.onClose = null;
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/progress/${this.taskId}`;

    console.log('Attempting to connect to WebSocket:', wsUrl); // 添加调试信息

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connection opened'); // 添加连接打开的调试信息
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received WebSocket data:', data); // 添加接收到数据的调试信息
      if (this.onMessage) {
        this.onMessage(data);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (this.onError) {
        this.onError(error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket connection closed');
      if (this.onClose) {
        this.onClose();
      }
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// 创建全局API实例
const apiClient = new APIClient();