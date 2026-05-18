<!-- filepath: src/views/EnergyDetectionView.vue -->
<template>
  <div class="energy-detection-container">
    <h1 class="title">流水线视觉检测 - 能效标签识别</h1>

    <div class="mode-tabs">
      <button class="tab-btn" :class="{ active: activeMode === 'single' }" @click="switchMode('single')">
        单张图片识别
      </button>
      <button class="tab-btn" :class="{ active: activeMode === 'realtime' }" @click="switchMode('realtime')">
        实时视频检测
      </button>
    </div>

    <div v-show="activeMode === 'single'" class="app-container">
      <div class="upload-area">
        <div class="input-methods">
          <div class="file-upload-section">
            <input type="file" id="fileInput" accept="image/*" hidden @change="handleFileSelect">
            <div class="drop-zone" @click="triggerFileInput"
                 @dragover.prevent @dragenter="highlight" @dragleave="unhighlight" @drop="handleDrop">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              <p>拖放图片到此处或 <span class="browse-link">浏览文件</span></p>
              <img v-if="previewUrl" :src="previewUrl" class="preview-img" />
            </div>
          </div>

          <div class="camera-section">
            <div class="camera-controls">
              <button class="btn camera-btn" @click="toggleCamera" :class="{ active: isCameraActive }">
                {{ isCameraActive ? '关闭摄像头' : '开启摄像头' }}
              </button>
              <button v-if="isCameraActive" class="btn capture-btn" @click="captureFromCamera" :disabled="!isCameraActive">
                拍摄识别
              </button>
            </div>

            <div class="camera-preview" v-show="isCameraActive">
              <video ref="videoElement" autoplay playsinline></video>
              <canvas ref="canvasElement" style="display: none;"></canvas>
              <div class="camera-overlay" v-if="isCameraActive">
                <div class="crosshair"></div>
                <p>对准能效标签后点击拍摄识别</p>
              </div>
            </div>
          </div>
        </div>

        <div class="options">
          <label>
            <input type="checkbox" id="keepFormatting" v-model="keepFormatting">
            保留原始格式
          </label>
        </div>
        <button id="processBtn" class="btn" :disabled="!currentFile" @click="processImage">开始识别</button>
      </div>

      <div class="result-area">
        <div class="energy-level-container" :class="energyLevelClass">
          <div class="energy-level-display">
            {{ energyLevelText }}
          </div>
        </div>

        <div class="tabs">
          <button class="tab" :class="{ active: activeTab === 'text' }" @click="activeTab = 'text'">识别文本</button>
          <button class="tab" :class="{ active: activeTab === 'json' }" @click="activeTab = 'json'">JSON 结果</button>
        </div>

        <div class="tab-content">
          <div id="textResult" class="tab-pane" :class="{ active: activeTab === 'text' }">
            <div class="result-container">
              <textarea id="textOutput" readonly placeholder="识别结果将显示在这里" v-model="textResult"></textarea>
              <button id="copyTextBtn" class="btn secondary" @click="copyToClipboard(textResult, '文本')">复制文本</button>
            </div>
          </div>

          <div id="jsonResult" class="tab-pane" :class="{ active: activeTab === 'json' }">
            <div class="result-container">
              <pre id="jsonOutput">{{ jsonResult }}</pre>
              <button id="copyJsonBtn" class="btn secondary" @click="copyToClipboard(jsonResult, 'JSON')">复制 JSON</button>
            </div>
          </div>
        </div>

        <div class="preview-container" v-show="previewUrl">
          <div class="image-preview">
            <img id="previewImage" :src="previewUrl" alt="预览图">
            <div class="loading-overlay" :class="{ active: isLoading }">
              <div class="spinner"></div>
              <p>识别中...</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-show="activeMode === 'realtime'" class="realtime-container">
      <div class="realtime-controls">
        <button class="btn start-btn" @click="startRealtimeDetection" :disabled="isRealtimeRunning">
          {{ isRealtimeRunning ? '检测中...' : '开始实时检测' }}
        </button>
        <button class="btn stop-btn" @click="stopRealtimeDetection" :disabled="!isRealtimeRunning">
          停止检测
        </button>
        <button class="btn config-btn" @click="showConfig = !showConfig">
          配置参数
        </button>
      </div>

      <div v-show="showConfig" class="config-panel">
        <div class="config-item">
          <label>检测间隔(ms):</label>
          <input type="number" v-model.number="detectionConfig.detection_interval" min="100" max="5000">
        </div>
        <div class="config-item">
          <label>置信度阈值:</label>
          <input type="number" v-model.number="detectionConfig.confidence_threshold" min="0.1" max="1.0" step="0.1">
        </div>
        <div class="config-item">
          <label>摄像头源:</label>
          <input type="number" v-model.number="detectionConfig.camera_source" min="0" max="10">
        </div>
        <div class="config-item">
          <label>
            <input type="checkbox" v-model="detectionConfig.enable_simulation">
            启用模拟模式
          </label>
        </div>
      </div>

      <div class="realtime-content">
        <div class="video-section">
          <div class="video-container">
            <div class="video-placeholder" v-if="!isRealtimeRunning">
              <div class="placeholder-content">
                <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
                  <line x1="7" y1="2" x2="7" y2="22"></line>
                  <line x1="17" y1="2" x2="17" y2="22"></line>
                  <line x1="2" y1="12" x2="22" y2="12"></line>
                  <line x1="2" y1="7" x2="7" y2="7"></line>
                  <line x1="2" y1="17" x2="7" y2="17"></line>
                  <line x1="17" y1="17" x2="22" y2="17"></line>
                  <line x1="17" y1="7" x2="22" y2="7"></line>
                </svg>
                <p>点击"开始实时检测"启动视频流</p>
              </div>
            </div>
            <img v-else :src="currentFrame" alt="实时视频流" class="video-frame" />
            <div class="video-overlay" v-if="isRealtimeRunning">
              <div class="detection-info">
                <div class="fps-counter">FPS: {{ realtimeStats.fps || 0 }}</div>
                <div class="frame-counter">帧数: {{ realtimeStats.frame_count || 0 }}</div>
                <div class="detection-counter">检测数: {{ realtimeStats.detection_count || 0 }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="realtime-results">
          <div class="results-header">
            <h3>实时检测结果</h3>
            <div class="status-indicator" :class="{
              connected: realtimeStats.camera_status === 'connected',
              disconnected: realtimeStats.camera_status === 'disconnected',
              error: realtimeStats.camera_status === 'error'
            }">
              {{ getStatusText(realtimeStats.camera_status) }}
            </div>
          </div>

          <div class="results-list">
            <div v-for="(result, index) in recentResults" :key="index" class="result-item">
              <div class="result-header">
                <span class="timestamp">{{ formatTimestamp(result.timestamp) }}</span>
                <span class="status" :class="{
                  success: result.success,
                  error: !result.success
                }">
                  {{ result.success ? '成功' : '失败' }}
                </span>
              </div>
              <div v-if="result.success" class="result-content">
                <div class="energy-level">能效等级: {{ result.energy_level || '未知' }}</div>
                <div class="confidence">置信度: {{ (result.confidence * 100).toFixed(1) }}%</div>
                <div class="detected-text" v-if="result.text">识别文本: {{ result.text }}</div>
              </div>
              <div v-else class="result-content error">
                错误: {{ result.error || '未知错误' }}
              </div>
            </div>
          </div>

          <div class="stats-panel">
            <h4>检测统计</h4>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-value">{{ realtimeStats.success_count || 0 }}</div>
                <div class="stat-label">成功识别</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ realtimeStats.error_count || 0 }}</div>
                <div class="stat-label">识别失败</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ realtimeStats.processing_time?.toFixed(2) || 0 }}ms</div>
                <div class="stat-label">处理时间</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ ((realtimeStats.success_count || 0) / (realtimeStats.detection_count || 1) * 100).toFixed(1) }}%</div>
                <div class="stat-label">成功率</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div id="toast" class="toast" :class="{ show: toast.show, success: toast.type === 'success', error: toast.type === 'error' }">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue';
import {
  energyDetectionAPI,
  startEnergyDetection,
  stopEnergyDetection,
  getDetectionStatus,
  configureDetection,
  onEnergyDetectionResult,
  onEnergyDetectionStatus,
  onEnergyDetectionFrame,
  onEnergyDetectionError,
  type EnergyDetectionResult,
  type EnergyDetectionStats,
  type EnergyDetectionConfig
} from '../api/energyDetectionApi';

const isComponentReady = ref(false);
const currentFile = ref<File | null>(null);
const previewUrl = ref('');
const keepFormatting = ref(true);
const activeTab = ref<'text' | 'json'>('text');
const textResult = ref('识别结果将显示在这里');
const jsonResult = ref('JSON 结果将显示在这里');
const energyLevel = ref<string | null>(null);
const isLoading = ref(false);
const toast = ref({
  show: false,
  message: '',
  type: '' as 'success' | 'error' | ''
});

const isCameraActive = ref(false);
const videoElement = ref<HTMLVideoElement | null>(null);
const canvasElement = ref<HTMLCanvasElement | null>(null);
const stream = ref<MediaStream | null>(null);

const activeMode = ref<'single' | 'realtime'>('single');
const isRealtimeRunning = ref(false);
const showConfig = ref(false);
const currentFrame = ref('');
const recentResults = ref<EnergyDetectionResult[]>([]);
const realtimeStats = ref<EnergyDetectionStats>({
  is_running: false,
  fps: 0,
  processing_time: 0,
  frame_count: 0,
  detection_count: 0,
  success_count: 0,
  error_count: 0,
  camera_status: 'disconnected',
  ocr_service_status: 'disconnected'
});

const detectionConfig = ref<EnergyDetectionConfig>({
  detection_interval: 1000,
  confidence_threshold: 0.7,
  camera_source: 0,
  enable_simulation: false,
  max_frame_skip: 5
});

onMounted(async () => {
  await nextTick();
  isComponentReady.value = true;
  console.log('EnergyDetectionView 组件已完全挂载');

  setupRealtimeListeners();
});

onUnmounted(() => {
  stopCamera();
  stopRealtimeDetection();
  energyDetectionAPI.disconnect();
});

const energyLevelText = computed(() => {
  if (energyLevel.value === '未识别到能效等级') {
    return "未识别到能效等级";
  }
  return energyLevel.value
    ? `识别结果: 能效等级 ${energyLevel.value}级`
    : "能效等级识别结果将显示在这里";
});

const energyLevelClass = computed(() => {
  if (!energyLevel.value || energyLevel.value === '未识别到能效等级') return '';

  return {
    'level-1': energyLevel.value === '1',
    'level-2': energyLevel.value === '2',
    'level-3': energyLevel.value === '3'
  };
});

function triggerFileInput() {
  const fileInput = document.getElementById('fileInput') as HTMLInputElement;
  if (fileInput) {
    fileInput.click();
  }
}

function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement;
  const files = target.files;
  if (files && files.length > 0) {
    loadFile(files[0]);
  }
}

function preventDefaults(e: Event) {
  e.preventDefault();
  e.stopPropagation();
}

function highlight(e: Event) {
  const target = e.currentTarget as HTMLElement;
  target.classList.add('drag-over');
}

function unhighlight(e: Event) {
  const target = e.currentTarget as HTMLElement;
  target.classList.remove('drag-over');
}

function handleDrop(e: DragEvent) {
  preventDefaults(e);
  unhighlight(e);

  if (e.dataTransfer) {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      loadFile(files[0]);
    }
  }
}

function loadFile(file: File) {
  if (!file.type.match('image.*')) {
    showToast('请选择图片文件', 'error');
    return;
  }

  currentFile.value = file;

  const reader = new FileReader();
  reader.onload = (e) => {
    if (e.target) {
      previewUrl.value = e.target.result as string;
      console.log('图片预览已创建');
    }
  };
  reader.readAsDataURL(file);

  energyLevel.value = null;
  textResult.value = '识别中...';
  jsonResult.value = '识别中...';
}

async function processImage() {
  if (!currentFile.value || !isComponentReady.value) {
    console.log('组件未准备好或没有文件');
    return;
  }

  isLoading.value = true;
  console.log('开始处理图片');

  try {
    const formData = new FormData();
    formData.append('file', currentFile.value);

    const combinedResponse = await fetch('http://localhost:5000/api/energy/combined', {
      method: 'POST',
      body: formData
    });

    if (!combinedResponse.ok) {
      throw new Error(`综合识别失败: ${combinedResponse.status}`);
    }

    const combinedData = await combinedResponse.json();

    if (!combinedData.success) {
      throw new Error(combinedData.message || '识别失败');
    }

    displayCombinedResults(combinedData);
    showToast('识别成功!', 'success');

    console.log('综合识别API响应:', combinedResponse.status);
  } catch (error) {
    console.error('处理图像时出错:', error);
    showToast(error.message || '发生未知错误', 'error');

    textResult.value = '识别失败，请重试';
    jsonResult.value = '识别失败，请重试';
    energyLevel.value = null;
  } finally {
    isLoading.value = false;
  }
}

function displayCombinedResults(combinedData: any) {
  let text = combinedData.ocr_text || '未识别到文本';
  textResult.value = text;

  jsonResult.value = JSON.stringify(combinedData, null, 2);

  if (combinedData.energy_level) {
    const levelMatch = combinedData.energy_level.match(/\d+/);
    energyLevel.value = levelMatch ? levelMatch[0] : '未知';
  } else {
    energyLevel.value = '未识别到能效等级';
  }

  activeTab.value = 'text';
}

function copyToClipboard(content: string, type: string) {
  navigator.clipboard.writeText(content).then(() => {
    showToast(`${type}已复制到剪贴板`, 'success');
  }).catch(() => {
    showToast('复制失败', 'error');
  });
}

function showToast(message: string, type: 'success' | 'error' | '' = '') {
  toast.value = {
    show: true,
    message,
    type
  };

  setTimeout(() => {
    toast.value.show = false;
  }, 3000);
}

async function toggleCamera() {
  if (isCameraActive.value) {
    stopCamera();
  } else {
    await startCamera();
  }
}

async function startCamera() {
  try {
    const mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'environment'
      }
    });

    if (videoElement.value) {
      stream.value = mediaStream;
      videoElement.value.srcObject = mediaStream;
      isCameraActive.value = true;
      showToast('摄像头已开启', 'success');
    }
  } catch (error) {
    console.error('摄像头开启失败:', error);
    showToast('摄像头开启失败，请检查权限', 'error');
  }
}

function stopCamera() {
  if (stream.value) {
    stream.value.getTracks().forEach(track => track.stop());
    stream.value = null;
  }
  if (videoElement.value) {
    videoElement.value.srcObject = null;
  }
  isCameraActive.value = false;
}

async function captureFromCamera() {
  if (!videoElement.value || !canvasElement.value || !isCameraActive.value) {
    showToast('摄像头未就绪', 'error');
    return;
  }

  try {
    const video = videoElement.value;
    const canvas = canvasElement.value;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('无法获取画布上下文');
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(async (blob) => {
      if (!blob) {
        throw new Error('无法捕获图像');
      }

      const file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });

      loadFile(file);

      await processImage();

    }, 'image/jpeg', 0.9);

  } catch (error) {
    console.error('摄像头捕获失败:', error);
    showToast('图像捕获失败', 'error');
  }
}

function switchMode(mode: 'single' | 'realtime') {
  activeMode.value = mode;
  if (mode === 'realtime') {
    stopCamera();
  } else {
    stopRealtimeDetection();
  }
}

function setupRealtimeListeners() {
  onEnergyDetectionResult((data: EnergyDetectionResult) => {
    recentResults.value.unshift(data);
    if (recentResults.value.length > 10) {
      recentResults.value.pop();
    }
  });

  onEnergyDetectionStatus((data: EnergyDetectionStats) => {
    realtimeStats.value = data;
    isRealtimeRunning.value = data.is_running;
  });

  onEnergyDetectionFrame((data: { frame: string }) => {
    currentFrame.value = data.frame;
  });

  onEnergyDetectionError((data: { error: string }) => {
    showToast(`实时检测错误: ${data.error}`, 'error');
  });
}

async function startRealtimeDetection() {
  try {
    await configureDetection(detectionConfig.value);

    const success = await startEnergyDetection(detectionConfig.value.camera_source);
    if (success) {
      showToast('实时检测已启动', 'success');
    } else {
      showToast('启动实时检测失败', 'error');
    }
  } catch (error) {
    console.error('启动实时检测失败:', error);
    showToast('启动实时检测失败', 'error');
  }
}

async function stopRealtimeDetection() {
  try {
    const success = await stopEnergyDetection();
    if (success) {
      showToast('实时检测已停止', 'success');
      currentFrame.value = '';
    } else {
      showToast('停止实时检测失败', 'error');
    }
  } catch (error) {
    console.error('停止实时检测失败:', error);
    showToast('停止实时检测失败', 'error');
  }
}

function getStatusText(status: string) {
  const statusMap: { [key: string]: string } = {
    connected: '已连接',
    disconnected: '未连接',
    error: '错误'
  };
  return statusMap[status] || '未知';
}

function formatTimestamp(timestamp: number) {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}
</script>

<style scoped>
.energy-detection-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  background: #181c2a;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  color: #e0e0e0;
  min-height: 600px;
}

.input-methods {
  display: flex;
  gap: 20px;
  margin-bottom: 1.5rem;
}

.file-upload-section,
.camera-section {
  flex: 1;
}

.camera-controls {
  display: flex;
  gap: 10px;
  margin-bottom: 1rem;
}

.camera-btn,
.capture-btn {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.camera-btn {
  background-color: #23263a;
  color: #409eff;
  border: 1px solid #409eff;
}

.camera-btn:hover {
  background-color: #2c2f45;
}

.camera-btn.active {
  background-color: #409eff;
  color: white;
}

.capture-btn {
  background-color: #28a745;
  color: white;
}

.capture-btn:hover:not(:disabled) {
  background-color: #218838;
  transform: translateY(-2px);
}

.capture-btn:disabled {
  background-color: #666;
  cursor: not-allowed;
  transform: none;
}

.camera-preview {
  position: relative;
  width: 100%;
  height: 300px;
  border: 2px dashed #409eff;
  border-radius: 8px;
  overflow: hidden;
  background-color: #23263a;
}

.camera-preview video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: rgba(0, 0, 0, 0.3);
  color: white;
}

.crosshair {
  width: 60px;
  height: 60px;
  border: 2px solid #409eff;
  border-radius: 50%;
  position: relative;
  margin-bottom: 1rem;
}

.crosshair::before,
.crosshair::after {
  content: '';
  position: absolute;
  background: #409eff;
}

.crosshair::before {
  width: 2px;
  height: 20px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.crosshair::after {
  width: 20px;
  height: 2px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.camera-overlay p {
  margin: 0;
  font-size: 0.9rem;
  text-align: center;
}

.title {
  font-size: 1.8rem;
  font-weight: bold;
  margin-bottom: 20px;
  color: #fff;
  text-align: center;
}

.app-container {
  display: flex;
  flex-direction: column;
}

@media (min-width: 992px) {
  .app-container {
    flex-direction: row;
  }

  .upload-area, .result-area {
    width: 50%;
  }

  .upload-area {
    padding-right: 1rem;
  }

  .result-area {
    padding-left: 1rem;
  }
}

.upload-area, .result-area {
  margin-bottom: 2rem;
}

.drop-zone {
  border: 2px dashed #409eff;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  transition: all 0.3s ease;
  background-color: #23263a;
  cursor: pointer;
  margin-bottom: 1.5rem;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
}

.drop-zone:hover, .drop-zone.drag-over {
  border-color: #66b1ff;
  background-color: rgba(64, 158, 255, 0.1);
}

.drop-zone svg {
  margin-bottom: 1rem;
  color: #aaa;
}

.drop-zone p {
  color: #aaa;
  margin: 0;
}

.browse-link {
  color: #66b1ff;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}

.preview-img {
  max-width: 100%;
  max-height: 150px;
  margin-top: 15px;
  border-radius: 4px;
  border: 1px solid #444;
}

.options {
  margin-bottom: 1.5rem;
  padding: 0.75rem;
  background-color: #23263a;
  border-radius: 8px;
}

.options label {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #e0e0e0;
}

.options input {
  margin-right: 0.5rem;
}

.btn {
  display: block;
  width: 100%;
  padding: 0.75rem;
  background-color: #409eff;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn:hover {
  background-color: #66b1ff;
  transform: translateY(-2px);
}

.btn:disabled {
  background-color: #666;
  cursor: not-allowed;
  transform: none;
}

.btn.secondary {
  background-color: #23263a;
  color: #409eff;
  border: 1px solid #409eff;
  margin-top: 1rem;
}

.btn.secondary:hover {
  background-color: #2c2f45;
}

.result-area {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.energy-level-container {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #23263a;
  border-radius: 8px;
  border-left: 4px solid #6c757d;
  text-align: center;
  transition: all 0.5s ease;
}

.energy-level-container:not(.level-1):not(.level-2):not(.level-3) {
  border-left: 4px solid #6c757d;
}

.energy-level-display {
  padding: 1rem;
  border-radius: 8px;
  font-size: 1.2rem;
  font-weight: bold;
  text-align: center;
  transition: all 0.5s ease;
}

.level-1 {
  background-color: #2e7d32;
  color: white;
  border-left: 4px solid #2e7d32;
}

.level-2 {
  background-color: #7cb342;
  color: white;
  border-left: 4px solid #7cb342;
}

.level-3 {
  background-color: #d32f2f;
  color: white;
  border-left: 4px solid #d32f2f;
}

.tabs {
  display: flex;
  border-bottom: 1px solid #444;
  margin-bottom: 1rem;
}

.tab {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  position: relative;
  color: #aaa;
}

.tab.active {
  color: #409eff;
  font-weight: 600;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 3px;
  background-color: #409eff;
}

.tab-pane {
  display: none;
}

.tab-pane.active {
  display: block;
}

.result-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 300px;
}

#textOutput {
  flex: 1;
  width: 100%;
  padding: 1rem;
  border: 1px solid #444;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
  font-size: 1rem;
  line-height: 1.6;
  background: #23263a;
  color: #e0e0e0;
}

#jsonOutput {
  flex: 1;
  width: 100%;
  padding: 1rem;
  border: 1px solid #444;
  border-radius: 8px;
  background: #23263a;
  overflow: auto;
  font-size: 0.9rem;
  color: #e0e0e0;
}

.preview-container {
  margin-top: 1.5rem;
}

.image-preview {
  position: relative;
  border: 1px solid #444;
  border-radius: 8px;
  overflow: hidden;
  background-color: #1a1c2a;
  min-height: 200px;
}

#previewImage {
  display: block;
  max-width: 100%;
  max-height: 300px;
  margin: 0 auto;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
}

.loading-overlay.active {
  opacity: 1;
  visibility: visible;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-left: 4px solid #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 1rem 1.5rem;
  background-color: #343a40;
  color: white;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transform: translateY(100px);
  opacity: 0;
  transition: all 0.3s ease;
  z-index: 1000;
}

.toast.show {
  transform: translateY(0);
  opacity: 1;
}

.toast.success {
  background-color: #28a745;
}

.toast.error {
  background-color: #dc3545;
}

.mode-tabs {
  display: flex;
  margin-bottom: 2rem;
  border-bottom: 1px solid #444;
}

.tab-btn {
  padding: 1rem 2rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  color: #aaa;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.tab-btn.active {
  color: #409eff;
  border-bottom-color: #409eff;
  font-weight: 600;
}

.tab-btn:hover {
  color: #66b1ff;
}

.realtime-container {
  background: #23263a;
  border-radius: 12px;
  padding: 2rem;
  margin-top: 1rem;
}

.realtime-controls {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.start-btn, .stop-btn, .config-btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  flex: 1;
  min-width: 120px;
}

.start-btn {
  background-color: #28a745;
  color: white;
}

.start-btn:hover:not(:disabled) {
  background-color: #218838;
}

.stop-btn {
  background-color: #dc3545;
  color: white;
}

.stop-btn:hover:not(:disabled) {
  background-color: #c82333;
}

.config-btn {
  background-color: #23263a;
  color: #409eff;
  border: 1px solid #409eff;
}

.config-btn:hover {
  background-color: #2c2f45;
}

.config-panel {
  background: #1a1c2a;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid #444;
}

.config-item {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
  gap: 1rem;
}

.config-item:last-child {
  margin-bottom: 0;
}

.config-item label {
  color: #e0e0e0;
  min-width: 120px;
}

.config-item input[type="number"] {
  background: #23263a;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 0.5rem;
  color: #e0e0e0;
  width: 100px;
}

.config-item input[type="checkbox"] {
  margin-right: 0.5rem;
}

.realtime-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.video-section {
  position: relative;
}

.video-container {
  position: relative;
  background: #1a1c2a;
  border-radius: 8px;
  overflow: hidden;
  aspect-ratio: 16/9;
}

.video-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.placeholder-content {
  text-align: center;
}

.placeholder-content svg {
  margin-bottom: 1rem;
  color: #444;
}

.video-frame {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 1rem;
  background: linear-gradient(to bottom, rgba(0,0,0,0.7), transparent);
}

.detection-info {
  display: flex;
  gap: 1rem;
  color: white;
  font-size: 0.9rem;
  font-weight: 600;
}

.realtime-results {
  background: #1a1c2a;
  border-radius: 8px;
  padding: 1.5rem;
  border: 1px solid #444;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #444;
}

.results-header h3 {
  margin: 0;
  color: #fff;
}

.status-indicator {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

.status-indicator.connected {
  background-color: #28a745;
  color: white;
}

.status-indicator.disconnected {
  background-color: #6c757d;
  color: white;
}

.status-indicator.error {
  background-color: #dc3545;
  color: white;
}

.results-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 1.5rem;
}

.result-item {
  background: #23263a;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 0.75rem;
  border-left: 4px solid #6c757d;
}

.result-item:last-child {
  margin-bottom: 0;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.timestamp {
  color: #aaa;
  font-size: 0.8rem;
}

.status {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
}

.status.success {
  background-color: #28a745;
  color: white;
}

.status.error {
  background-color: #dc3545;
  color: white;
}

.result-content {
  color: #e0e0e0;
}

.result-content.error {
  color: #dc3545;
}

.energy-level {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.confidence {
  color: #aaa;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.detected-text {
  font-size: 0.8rem;
  color: #888;
  margin-top: 0.5rem;
  word-break: break-all;
}

.stats-panel {
  background: #23263a;
  border-radius: 6px;
  padding: 1rem;
  border: 1px solid #444;
}

.stats-panel h4 {
  margin: 0 0 1rem 0;
  color: #fff;
  text-align: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.stat-item {
  text-align: center;
  padding: 0.75rem;
  background: #1a1c2a;
  border-radius: 6px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.8rem;
  color: #aaa;
}

@media (max-width: 768px) {
  .realtime-content {
    grid-template-columns: 1fr;
  }

  .realtime-controls {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>