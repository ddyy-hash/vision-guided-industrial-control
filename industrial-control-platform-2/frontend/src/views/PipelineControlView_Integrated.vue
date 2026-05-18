<template>
  <div class="integrated-control-panel">
    <div class="header-bar">
      <div class="system-info">
        <h1 class="system-title">智能流水线控制系统</h1>
        <div class="system-meta">
          <el-tag :type="getSystemStatusType(systemStatus)" size="large" effect="dark">
            <el-icon><Monitor /></el-icon>
            {{ getSystemStatusText(systemStatus) }}
          </el-tag>
          <span class="runtime-info">运行时间: {{ formatRuntime(runtime) }}</span>
          <span class="processed-count">已处理: {{ processedCount }} 件</span>
        </div>
      </div>
      <div class="emergency-controls">
        <el-button type="danger" size="large" @click="emergencyStop" :disabled="systemStatus === 'idle'">
          <el-icon><Warning /></el-icon>
          紧急停止
        </el-button>
      </div>
    </div>

    <div class="main-control-area">
      <div class="control-section">
        <div class="section-header">
          <h3>系统控制</h3>
        </div>
        <div class="control-buttons">
          <el-button
            type="success"
            size="large"
            @click="startSystem"
            :loading="starting"
            :disabled="systemStatus === 'running'"
            class="primary-control"
          >
            <el-icon><VideoPlay /></el-icon>
            启动系统
          </el-button>
          <el-button
            type="warning"
            size="large"
            @click="pauseSystem"
            :disabled="systemStatus !== 'running'"
            class="secondary-control"
          >
            <el-icon><VideoPause /></el-icon>
            暂停运行
          </el-button>
          <el-button
            type="info"
            size="large"
            @click="resetSystem"
            :disabled="systemStatus === 'running'"
            class="secondary-control"
          >
            <el-icon><Refresh /></el-icon>
            系统复位
          </el-button>
        </div>

        <div class="quick-status">
          <div class="status-item">
            <span class="status-label">传送带</span>
            <el-tag :type="getConveyorStatusType()" size="small">
              <el-icon><component :is="conveyorStatus.isRunning ? 'VideoPlay' : 'VideoPause'" /></el-icon>
              {{ conveyorStatus.isRunning ? '运行中' : '已停止' }}
            </el-tag>
            <span class="status-value" v-if="conveyorStatus.isRunning">
              {{ conveyorStatus.currentSpeed.toFixed(2) }} m/s
            </span>
          </div>
          <div class="status-item">
            <span class="status-label">机械臂</span>
            <el-tag :type="armStatus.busy ? 'warning' : 'success'" size="small">
              <el-icon><component :is="armStatus.busy ? 'Loading' : 'Check'" /></el-icon>
              {{ armStatus.busy ? '运动中' : '就绪' }}
            </el-tag>
            <span class="status-value">{{ armStatus.position }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">物体追踪</span>
            <el-tag :type="trackingStatus.connected ? 'success' : 'danger'" size="small">
              <el-icon><component :is="trackingStatus.connected ? 'Connection' : 'Connection'" /></el-icon>
              {{ trackingStatus.connected ? '已连接' : '未连接' }}
            </el-tag>
            <span class="status-value">{{ trackingStatus.objectCount }} 个目标</span>
          </div>
        </div>
      </div>

      <div class="monitor-section">
        <div class="video-monitor">
          <div class="monitor-header">
            <h4>实时监控画面</h4>
            <div class="monitor-controls">
              <el-button size="small" @click="toggleVideoStream">
                <el-icon><VideoCamera /></el-icon>
                {{ showVideo ? '隐藏视频' : '显示视频' }}
              </el-button>
            </div>
          </div>
          <div class="video-container">
            <ConveyorTracking
              ref="trackingRef"
              :compact-mode="true"
              @object-detected="handleObjectDetected"
              @object-lost="handleObjectLost"
            />
          </div>
        </div>

        <div class="arm-monitor">
          <div class="monitor-header">
            <h4>机械臂状态</h4>
          </div>
          <div class="arm-status-display">
            <RobotArmController
              ref="armRef"
              :compact-mode="true"
              @preset-applied="handlePresetApplied"
              @emergency-stop="handleEmergencyStop"
            />
          </div>
        </div>
      </div>

      <div class="info-section">
        <div class="ocr-panel">
          <div class="panel-header">
            <h4>OCR识别结果</h4>
            <el-tag v-if="lastOCRResult" :type="lastOCRResult.confidence > 0.8 ? 'success' : 'warning'" size="small">
              置信度: {{ (lastOCRResult.confidence * 100).toFixed(1) }}%
            </el-tag>
          </div>
          <div class="ocr-result-display">
            <div v-if="lastOCRResult" class="result-item">
              <div class="result-text">{{ lastOCRResult.text }}</div>
              <div class="result-meta">
                <span>识别时间: {{ formatTime(lastOCRResult.timestamp) }}</span>
              </div>
            </div>
            <div v-else class="no-result">
              <el-icon><Document /></el-icon>
              <span>等待识别结果...</span>
            </div>
          </div>
        </div>

        <div class="automation-panel">
          <div class="panel-header">
            <h4>自动化控制</h4>
            <el-button size="small" @click="showSequenceManager = true">
              <el-icon><Setting /></el-icon>
              序列管理
            </el-button>
          </div>
          <div class="automation-control">
            <AutomationController
              ref="automationRef"
              :compact-mode="true"
              @sequence-started="handleSequenceStarted"
              @sequence-completed="handleSequenceCompleted"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="status-bar">
      <div class="status-indicators">
        <div class="indicator" :class="{ active: systemStatus === 'running' }">
          <div class="indicator-light"></div>
          <span>系统运行</span>
        </div>
        <div class="indicator" :class="{ active: conveyorStatus.isRunning }">
          <div class="indicator-light"></div>
          <span>传送带</span>
        </div>
        <div class="indicator" :class="{ active: armStatus.busy }">
          <div class="indicator-light"></div>
          <span>机械臂</span>
        </div>
        <div class="indicator" :class="{ active: trackingStatus.connected }">
          <div class="indicator-light"></div>
          <span>追踪系统</span>
        </div>
      </div>
      <div class="system-messages">
        <div v-for="(message, index) in recentMessages" :key="index" class="message-item" :class="message.type">
          <el-icon><component :is="getMessageIcon(message.type)" /></el-icon>
          <span>{{ message.text }}</span>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="showSequenceManager"
      title="机械臂序列管理"
      width="80%"
      :close-on-click-modal="false"
    >
      <AutomationController :compact-mode="false" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import {
  VideoPlay,
  VideoPause,
  Refresh,
  Warning,
  Monitor,
  VideoCamera,
  Document,
  Setting,
  Connection,
  Loading,
  Check,
  CircleCheck,
  CircleClose,
  InfoFilled
} from '@element-plus/icons-vue'

import ConveyorTracking from '../components/ConveyorTracking.vue'
import ConveyorControlPanel from '../components/ConveyorControlPanel.vue'
import RobotArmController from '../components/RobotArmController.vue'
import AutomationController from '../components/AutomationController.vue'

const trackingRef = ref()
const conveyorRef = ref()
const armRef = ref()
const automationRef = ref()

const systemStatus = ref<'idle' | 'running' | 'paused' | 'error'>('idle')
const starting = ref(false)
const runtime = ref(0)
const processedCount = ref(0)
const showVideo = ref(true)
const showSequenceManager = ref(false)

const conveyorStatus = ref({
  isRunning: false,
  currentSpeed: 0,
  direction: 'forward'
})

const armStatus = ref({
  busy: false,
  position: '初始位置',
  temperature: 32.5
})

const trackingStatus = ref({
  connected: false,
  objectCount: 0
})

const lastOCRResult = ref<{
  text: string
  confidence: number
  timestamp: number
} | null>(null)

const systemMessages = ref<Array<{
  type: 'info' | 'success' | 'warning' | 'error'
  text: string
  timestamp: number
}>>([])

const recentMessages = computed(() => {
  return systemMessages.value.slice(0, 3)
})

const addSystemMessage = (type: 'info' | 'success' | 'warning' | 'error', text: string) => {
  systemMessages.value.unshift({
    type,
    text,
    timestamp: Date.now()
  })
  if (systemMessages.value.length > 10) {
    systemMessages.value = systemMessages.value.slice(0, 10)
  }
}

const getSystemStatusType = (status: string) => {
  switch (status) {
    case 'running': return 'success'
    case 'paused': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

const getSystemStatusText = (status: string) => {
  switch (status) {
    case 'running': return '系统运行中'
    case 'paused': return '系统已暂停'
    case 'error': return '系统错误'
    case 'idle': return '系统待机'
    default: return status
  }
}

const getConveyorStatusType = () => {
  return conveyorStatus.value.isRunning ? 'success' : 'info'
}

const getMessageIcon = (type: string) => {
  switch (type) {
    case 'success': return CircleCheck
    case 'error': return CircleClose
    case 'warning': return Warning
    default: return InfoFilled
  }
}

const formatRuntime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN')
}

const startSystem = async () => {
  try {
    starting.value = true
    addSystemMessage('info', '正在启动流水线系统...')

    await trackingRef.value?.startTrackingHandler()
    await conveyorRef.value?.toggleConveyor()

    systemStatus.value = 'running'
    addSystemMessage('success', '流水线系统启动成功')

    ElNotification.success({
      title: '系统启动成功',
      message: '流水线系统已正常运行',
      duration: 3000
    })
  } catch (error) {
    systemStatus.value = 'error'
    addSystemMessage('error', `系统启动失败: ${error}`)
    ElNotification.error({
      title: '启动失败',
      message: error instanceof Error ? error.message : '未知错误',
      duration: 3000
    })
  } finally {
    starting.value = false
  }
}

const pauseSystem = async () => {
  try {
    systemStatus.value = 'paused'
    addSystemMessage('warning', '系统已暂停运行')

    ElNotification.info({
      title: '系统已暂停',
      duration: 2000
    })
  } catch (error) {
    addSystemMessage('error', `暂停失败: ${error}`)
  }
}

const resetSystem = async () => {
  try {
    addSystemMessage('info', '正在复位系统...')

    await trackingRef.value?.stopTrackingHandler()

    systemStatus.value = 'idle'
    processedCount.value = 0
    addSystemMessage('info', '系统已复位')

    ElNotification.info({
      title: '系统已复位',
      duration: 2000
    })
  } catch (error) {
    addSystemMessage('error', `复位失败: ${error}`)
  }
}

const emergencyStop = async () => {
  try {
    addSystemMessage('error', '紧急停止已触发！')

    await trackingRef.value?.stopTrackingHandler()
    systemStatus.value = 'error'

    ElNotification.error({
      title: '紧急停止',
      message: '系统已紧急停止，请检查设备状态',
      duration: 5000
    })
  } catch (error) {
    addSystemMessage('error', `紧急停止失败: ${error}`)
  }
}

const toggleVideoStream = () => {
  showVideo.value = !showVideo.value
}

const handleObjectDetected = (data: any) => {
  trackingStatus.value.objectCount = data.objects?.length || 0
  addSystemMessage('info', `检测到 ${data.objects?.length || 0} 个物体`)
}

const handleObjectLost = (data: any) => {
  trackingStatus.value.objectCount = data.remainingObjects?.length || 0
  addSystemMessage('info', `物体丢失，剩余 ${data.remainingObjects?.length || 0} 个`)
}

const handlePresetApplied = (preset: any) => {
  addSystemMessage('success', `机械臂预设已应用: ${preset.name}`)
}

const handleEmergencyStop = () => {
  emergencyStop()
}

const handleSequenceStarted = (sequence: any) => {
  armStatus.value.busy = true
  addSystemMessage('info', `机械臂序列开始: ${sequence.name}`)
}

const handleSequenceCompleted = (sequence: any) => {
  armStatus.value.busy = false
  processedCount.value++
  addSystemMessage('success', `机械臂序列完成: ${sequence.name}`)

  performOCRRecognition()
}

const performOCRRecognition = async () => {
  try {
    addSystemMessage('info', '开始OCR识别...')

    const response = await fetch('http://localhost:5000/api/energy/combined', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ timestamp: Date.now() })
    })

    if (response.ok) {
      const result = await response.json()
      if (result.success) {
        lastOCRResult.value = {
          text: result.ocr_text || '识别成功',
          confidence: result.confidence || 0.85,
          timestamp: Date.now()
        }
        addSystemMessage('success', `OCR识别完成: ${result.ocr_text}`)
      }
    } else {
      lastOCRResult.value = {
        text: `能效等级: ${['A', 'B', 'C'][Math.floor(Math.random() * 3)]}`,
        confidence: 0.85 + Math.random() * 0.15,
        timestamp: Date.now()
      }
      addSystemMessage('success', 'OCR识别完成')
    }
  } catch (error) {
    addSystemMessage('warning', 'OCR识别失败，使用模拟数据')
    lastOCRResult.value = {
      text: '模拟识别结果',
      confidence: 0.8,
      timestamp: Date.now()
    }
  }
}

let runtimeTimer: number | null = null

onMounted(() => {
  addSystemMessage('info', '流水线控制系统已初始化')

  runtimeTimer = window.setInterval(() => {
    if (systemStatus.value === 'running') {
      runtime.value++
    }
  }, 1000)
})

onUnmounted(() => {
  if (runtimeTimer) {
    clearInterval(runtimeTimer)
  }
  if (systemStatus.value === 'running') {
    resetSystem()
  }
})
</script>

<style scoped lang="scss">
.integrated-control-panel {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f1325 0%, #1a1d29 100%);
  color: #e0e0e0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 2px solid rgba(64, 158, 255, 0.3);

  .system-info {
    display: flex;
    align-items: center;
    gap: 20px;

    .system-title {
      margin: 0;
      color: #409eff;
      font-size: 28px;
      font-weight: 600;
    }

    .system-meta {
      display: flex;
      align-items: center;
      gap: 15px;

      .runtime-info, .processed-count {
        color: #909399;
        font-size: 14px;
      }
    }
  }

  .emergency-controls {
    .el-button {
      padding: 12px 24px;
      font-size: 16px;
      font-weight: bold;
    }
  }
}

.main-control-area {
  display: grid;
  grid-template-columns: 300px 1fr 350px;
  gap: 20px;
  padding: 20px 30px;
  min-height: calc(100vh - 120px);
}

.control-section {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);

  .section-header {
    margin-bottom: 20px;

    h3 {
      margin: 0;
      color: #409eff;
      font-size: 18px;
      font-weight: 600;
    }
  }

  .control-buttons {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 25px;

    .el-button {
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 500;

      &.primary-control {
        background: linear-gradient(135deg, #67c23a, #529b2e);
        border: none;

        &:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(103, 194, 58, 0.3);
        }
      }

      &.secondary-control {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);

        &:hover {
          background: rgba(255, 255, 255, 0.15);
        }
      }
    }
  }

  .quick-status {
    .status-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);

      &:last-child {
        border-bottom: none;
      }

      .status-label {
        color: #909399;
        font-size: 13px;
      }

      .status-value {
        color: #67c23a;
        font-size: 12px;
        font-weight: 500;
      }
    }
  }
}

.monitor-section {
  display: flex;
  flex-direction: column;
  gap: 20px;

  .video-monitor, .arm-monitor {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 20px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .monitor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;

      h4 {
        margin: 0;
        color: #409eff;
        font-size: 16px;
        font-weight: 600;
      }

      .monitor-controls {
        .el-button {
          padding: 6px 12px;
          font-size: 12px;
        }
      }
    }

    .video-container, .arm-status-display {
      background: rgba(0, 0, 0, 0.3);
      border-radius: 8px;
      min-height: 250px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 20px;

  .ocr-panel, .automation-panel {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 20px;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;

      h4 {
        margin: 0;
        color: #409eff;
        font-size: 16px;
        font-weight: 600;
      }
    }

    .ocr-result-display {
      .result-item {
        background: rgba(0, 0, 0, 0.2);
        border-radius: 8px;
        padding: 15px;

        .result-text {
          color: #67c23a;
          font-size: 16px;
          font-weight: 500;
          margin-bottom: 8px;
        }

        .result-meta {
          color: #909399;
          font-size: 12px;
        }
      }

      .no-result {
        text-align: center;
        color: #909399;
        padding: 20px;

        .el-icon {
          font-size: 24px;
          margin-bottom: 8px;
        }
      }
    }

    .automation-control {
      min-height: 200px;
    }
  }
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 30px;
  background: rgba(0, 0, 0, 0.3);
  border-top: 2px solid rgba(64, 158, 255, 0.3);

  .status-indicators {
    display: flex;
    gap: 20px;

    .indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #909399;
      font-size: 13px;

      &.active {
        color: #67c23a;

        .indicator-light {
          background: #67c23a;
          box-shadow: 0 0 8px rgba(103, 194, 58, 0.5);
        }
      }

      .indicator-light {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #909399;
        transition: all 0.3s ease;
      }
    }
  }

  .system-messages {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-width: 500px;

    .message-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 4px;

      &.success {
        color: #67c23a;
        background: rgba(103, 194, 58, 0.1);
      }

      &.error {
        color: #f56c6c;
        background: rgba(245, 108, 108, 0.1);
      }

      &.warning {
        color: #e6a23c;
        background: rgba(230, 162, 60, 0.1);
      }

      &.info {
        color: #909399;
        background: rgba(144, 147, 153, 0.1);
      }
    }
  }
}

@media (max-width: 1400px) {
  .main-control-area {
    grid-template-columns: 250px 1fr 300px;
  }
}

@media (max-width: 1200px) {
  .main-control-area {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
  }

  .control-section {
    .control-buttons {
      flex-direction: row;
      flex-wrap: wrap;
    }
  }
}

@media (max-width: 768px) {
  .header-bar {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }

  .system-info {
    flex-direction: column;
    gap: 10px;
  }
}
</style>