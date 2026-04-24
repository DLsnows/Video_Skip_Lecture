// 设置页面逻辑
document.addEventListener('DOMContentLoaded', () => {
  // DOM元素引用
  const settingsForm = document.getElementById('settings-form');
  const transcriptionBaseUrlInput = document.getElementById('transcription-base-url');
  const transcriptionApiKeyInput = document.getElementById('transcription-api-key');
  const transcriptionModelInput = document.getElementById('transcription-model');
  const ocrBaseUrlInput = document.getElementById('ocr-base-url');
  const ocrApiKeyInput = document.getElementById('ocr-api-key');
  const ocrModelInput = document.getElementById('ocr-model');
  const summarizationBaseUrlInput = document.getElementById('summarization-base-url');
  const summarizationApiKeyInput = document.getElementById('summarization-api-key');
  const summarizationModelInput = document.getElementById('summarization-model');
  const defaultInputFolderInput = document.getElementById('default-input-folder');
  const defaultOutputFolderInput = document.getElementById('default-output-folder');
  const loadDefaultSettingsBtn = document.getElementById('load-default-settings');

  // 页面加载时获取当前设置
  loadCurrentSettings();

  // 表单提交事件
  settingsForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    try {
      // 收集表单数据
      const settings = {
        transcription_provider: {
          base_url: transcriptionBaseUrlInput.value,
          api_key: transcriptionApiKeyInput.value,
          model: transcriptionModelInput.value
        },
        ocr_provider: {
          base_url: ocrBaseUrlInput.value,
          api_key: ocrApiKeyInput.value,
          model: ocrModelInput.value
        },
        summarization_provider: {
          base_url: summarizationBaseUrlInput.value,
          api_key: summarizationApiKeyInput.value,
          model: summarizationModelInput.value
        },
        folders: {
          default_input: defaultInputFolderInput.value,
          default_output: defaultOutputFolderInput.value
        }
      };

      // 更新设置
      await apiClient.updateSettings(settings);

      // 显示成功消息
      showMessage('设置已成功保存！', 'success');
    } catch (error) {
      console.error('保存设置失败:', error);
      showMessage(`保存设置失败: ${error.message}`, 'error');
    }
  });

  // 加载默认设置按钮事件
  loadDefaultSettingsBtn.addEventListener('click', async () => {
    try {
      // 获取默认设置（实际上就是获取当前设置，因为API会返回带默认值的完整配置）
      const settings = await apiClient.getSettings();

      // 显示确认对话框
      if (confirm('这将会重置所有设置为默认值。您确定要继续吗？')) {
        // 更新表单字段为默认值
        populateFormFields(settings);

        // 显示消息
        showMessage('已加载默认设置，请记得点击"保存设置"以应用更改', 'info');
      }
    } catch (error) {
      console.error('加载默认设置失败:', error);
      showMessage(`加载默认设置失败: ${error.message}`, 'error');
    }
  });

  // 加载当前设置
  async function loadCurrentSettings() {
    try {
      const settings = await apiClient.getSettings();
      populateFormFields(settings);
    } catch (error) {
      console.error('加载设置失败:', error);
      showMessage(`加载设置失败: ${error.message}`, 'error');
    }
  }

  // 填充表单字段
  function populateFormFields(settings) {
    if (!settings) return;

    // 填充转录提供商设置
    if (settings.transcription_provider) {
      transcriptionBaseUrlInput.value = settings.transcription_provider.base_url || '';
      transcriptionApiKeyInput.value = settings.transcription_provider.api_key || '';
      transcriptionModelInput.value = settings.transcription_provider.model || '';
    }

    // 填充OCR提供商设置
    if (settings.ocr_provider) {
      ocrBaseUrlInput.value = settings.ocr_provider.base_url || '';
      ocrApiKeyInput.value = settings.ocr_provider.api_key || '';
      ocrModelInput.value = settings.ocr_provider.model || '';
    }

    // 填充摘要化提供商设置
    if (settings.summarization_provider) {
      summarizationBaseUrlInput.value = settings.summarization_provider.base_url || '';
      summarizationApiKeyInput.value = settings.summarization_provider.api_key || '';
      summarizationModelInput.value = settings.summarization_provider.model || '';
    }

    // 填充文件夹设置
    if (settings.folders) {
      defaultInputFolderInput.value = settings.folders.default_input || '';
      defaultOutputFolderInput.value = settings.folders.default_output || '';
    }
  }

  // 显示消息
  function showMessage(message, type = 'info') {
    // 创建消息元素
    const messageEl = document.createElement('div');
    messageEl.textContent = message;
    messageEl.className = `message message-${type}`;

    // 添加样式
    messageEl.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 20px;
      border-radius: 4px;
      color: white;
      z-index: 1000;
      max-width: 400px;
      word-wrap: break-word;
    `;

    // 根据类型设置背景色
    switch (type) {
      case 'success':
        messageEl.style.backgroundColor = '#4CAF50';
        break;
      case 'error':
        messageEl.style.backgroundColor = '#f44336';
        break;
      case 'warning':
        messageEl.style.backgroundColor = '#ff9800';
        break;
      default:
        messageEl.style.backgroundColor = '#2196F3';
    }

    // 添加到页面
    document.body.appendChild(messageEl);

    // 3秒后移除消息
    setTimeout(() => {
      messageEl.remove();
    }, 3000);
  }
});