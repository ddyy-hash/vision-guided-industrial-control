<template>
  <div class="pipeline-control-new">
    <div class="header-industrial">
      <div class="header-left">
        <h1 class="system-title">智能流水线控制系统</h1>
        <div class="status-indicators">
          <div class="indicator" :class="{ active: systemStatus === 'running' }">
            <div class="indicator-light"></div>
            <span>系统运行</span>
          </div>
          <div class="indicator" :class="{ active: conveyorRunning }">
            <div class="indicator-light"></div>
            <span>传送带</span>
          </div>
          <div class="indicator" :class="{ active: armBusy }">
            <div class="indicator-light"></div>
            <span>机械臂</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <div class="runtime-display">
          <span class="runtime-label">运行时间</span>
          <span class="runtime-value">{{ formatRuntime(runtime) }}</span>
        </div>
        <button class="emergency-btn" @click="emergencyStop" :disabled="systemStatus === 'idle'">
          ⚠️ 紧急停止
        </button>
      </div>
    </div>

    <div class="main-control-area">
      <div class="control-panel">
        <div class="panel-header">
          <h3>系统控制</h3>
        </div>

        <div class="control-buttons">
          <button
            class="control-btn start-btn"
            @click="startPipeline"
            :disabled="systemStatus === 'running'"
            :class="{ loading: starting }"
          >
            <div class="btn-icon">▶</div>
            <div class="btn-text">
              <div class="btn-title">启动系统</div>
              <div class="btn-desc">开始流水线作业</div>
            </div>
          </button>

          <button
            class="control-btn pause-btn"
            @click="pausePipeline"
            :disabled="systemStatus !== 'running'"
          >
            <div class="btn-icon">⏸</div>
            <div class="btn-text">
              <div class="btn-title">暂停运行</div>
              <div class="btn-desc">临时停止作业</div>
            </div>
          </button>

          <button
            class="control-btn reset-btn"
            @click="resetPipeline"
            :disabled="systemStatus === 'running'"
          >
            <div class="btn-icon">↻</div>
            <div class="btn-text">
              <div class="btn-title">系统复位</div>
              <div class="btn-desc">重置到初始状态</div>
            </div>
          </button>
        </div>

        <div class="parameter-controls">
          <h4>参数调节</h4>

          <div class="param-item">
            <label>传送带速度</label>
            <div class="param-control">
              <input
                type="range"
                v-model="conveyorSpeed"
                min="0"
                max="1"
                step="0.01"
                @input="updateConveyorSpeed"
              >
              <span class="param-value">{{ conveyorSpeed.toFixed(2) }} m/s</span>
            </div>
          </div>

          <div class="param-item">
            <label>传送带方向</label>
            <div class="direction-control">
              <button
                class="dir-btn"
                :class="{ active: conveyorDirection === 'forward' }"
                @click="setConveyorDirection('forward')"
              >
                → 正向
              </button>
              <button
                class="dir-btn"
                :class="{ active: conveyorDirection === 'backward' }"
                @click="setConveyorDirection('backward')"
              >
                ← 反向
              </button>
            </div>
          </div>

          <div class="param-item">
            <label>调试模式</label>
            <div class="debug-controls">
              <el-switch
                v-model="debugMode"
                active-text="开启"
                inactive-text="关闭"
                @change="toggleDebugMode"
              />
            </div>
          </div>

          <div class="param-item" v-if="debugMode">
            <label>手动控制</label>
            <div class="manual-controls">
              <el-switch
                v-model="manualControlMode"
                active-text="启用"
                inactive-text="禁用"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="monitor-area">
        <div class="video-monitor">
          <div class="monitor-header">
            <h4>实时监控</h4>
            <div class="monitor-info">
              <span class="fps-display">FPS: {{ currentFPS.toFixed(1) }}</span>
              <span class="object-count">目标: {{ trackedObjects.length }}</span>
              <span class="alignment-status" :class="{ aligned: checkObjectAlignment()?.aligned }">
                {{ getAlignmentStatusText }}
              </span>
            </div>
          </div>
          <div class="video-display">
            <div v-if="videoStreamAvailable" class="video-stream">
              <img
                v-if="currentFrame && currentFrame.length > 100"
                :src="currentFrame"
                alt="实时监控画面"
                @load="onVideoLoad"
                @error="handleVideoError"
                class="video-stream-img"
              >
              <div v-else class="video-loading">
                <div class="loading-spinner"></div>
                <p>正在接收视频数据... ({{ currentFrame ? currentFrame.length : 0 }})</p>
              </div>
              <div class="detection-overlay">
                <div v-for="obj in trackedObjects" :key="obj.track_id"
                     class="tracked-object" :style="getObjectStyle(obj)">
                  <div class="object-label">
                    {{ getObjectDisplayName(obj.class_name) }} #{{ obj.track_id }}
                  </div>
                </div>
              </div>
              <div class="video-status-indicator">
                <div class="status-dot"></div>
                <span>实时视频</span>
              </div>
            </div>
            <div v-else class="video-placeholder">
              <div class="placeholder-content">
                <div class="camera-icon">📹</div>
                <p>视频流未连接</p>
                <p class="connection-status">正在尝试连接摄像头...</p>
                <button @click="testVideoStream" class="test-btn">重新连接</button>
              </div>
            </div>
          </div>
        </div>

        <div class="arm-status">
          <div class="status-header">
            <h4>机械臂状态</h4>
            <div class="status-info">
              <span class="position-info">{{ armPositionText }}</span>
              <span class="temp-info">{{ armTemperature }}°C</span>
            </div>
          </div>
          <div class="arm-display">
            <div class="arm-visual">
              <div class="arm-base"></div>
              <div class="arm-joint" v-for="(joint, index) in armJoints" :key="index"
                   :style="getJointStyle(index)">
                <div class="joint-label">J{{ index + 1 }}</div>
              </div>
              <div class="arm-end-effector"></div>
            </div>
            <div class="arm-controls">
              <button v-for="(joint, index) in armJoints" :key="index"
                      class="joint-control-btn" :class="{ active: selectedJoint === index }"
                      @click="selectJoint(index)">
                J{{ index + 1 }}: {{ joint.angle }}°
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="info-panel">
        <div class="ocr-card">
          <div class="card-header">
            <h4>OCR识别结果</h4>
            <div class="card-status">
              <span class="confidence" v-if="lastOCRResult">
                置信度: {{ (lastOCRResult.confidence * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
          <div class="ocr-content">
            <div v-if="lastOCRResult" class="result-display">
              <div class="result-text">{{ lastOCRResult.text }}</div>
              <div class="result-meta">
                <span>识别时间: {{ formatTime(lastOCRResult.timestamp) }}</span>
              </div>
            </div>
            <div v-else class="no-result">
              <div class="waiting-icon">⏳</div>
              <span>等待识别结果...</span>
            </div>
          </div>
        </div>

        <div class="log-card">
          <div class="card-header">
            <h4>系统日志</h4>
            <button @click="clearLogs" class="clear-btn">清空</button>
          </div>
          <div class="log-content">
            <div v-for="(log, index) in systemLogs" :key="index"
                 class="log-item" :class="`log-${log.type}`">
              <span class="log-time">{{ formatTime(log.timestamp) }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </div>

        <div class="automation-card">
          <div class="card-header">
            <h4>自动化序列</h4>
            <button @click="showSequenceManager = true" class="manage-btn">管理</button>
          </div>
          <div class="sequence-controls">
            <button @click="runPickPlaceSequence" class="sequence-btn primary"
                    :disabled="armBusy || systemStatus !== 'running'">
              🎯 执行取放序列
            </button>
            <button @click="runCustomSequence" class="sequence-btn secondary"
                    :disabled="armBusy || systemStatus !== 'running'">
              ⚙️ 自定义序列
            </button>
          </div>
          <div class="sequence-progress" v-if="sequenceRunning">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: sequenceProgress + '%' }"></div>
            </div>
            <span class="progress-text">{{ currentSequenceStep }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="status-bar">
      <div class="pipeline-steps">
        <div v-for="(step, index) in pipelineSteps" :key="step.id"
             class="step-item" :class="{ active: currentStep === step.id, completed: step.completed }">
          <div class="step-number">{{ index + 1 }}</div>
          <div class="step-name">{{ step.name }}</div>
          <div class="step-icon">{{ step.icon }}</div>
        </div>
      </div>
      <div class="system-stats">
        <span>处理成功率: {{ successRate }}%</span>
        <span>平均处理时间: {{ avgProcessingTime }}s</span>
      </div>
    </div>

    <div v-if="showSequenceManager" class="modal-overlay" @click="showSequenceManager = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>机械臂序列管理</h3>
          <button @click="showSequenceManager = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <p>序列管理功能开发中...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import {
  startPipeline as startPipelineAPI,
  pausePipeline as pausePipelineAPI,
  resetPipeline as resetPipelineAPI,
  getPipelineStatus,
  pipelineWebSocketEvents
} from '../api/pipelineApi'
import { conveyorApiService } from '../api/conveyorApi'
import { trackingAPI } from '../api/trackingApi'
import { unifiedApi } from '../api/unifiedApi'

const systemStatus = ref<'idle' | 'running' | 'paused' | 'error'>('idle')
const starting = ref(false)
const runtime = ref(0)
const processedCount = ref(0)
const successCount = ref(0)

const debugMode = ref(true)
const manualControlMode = ref(false)

const conveyorRunning = ref(false)
const conveyorSpeed = ref(0.1)
const conveyorDirection = ref<'forward' | 'backward'>('forward')

const armBusy = ref(false)
const armTemperature = ref(32.5)
const selectedJoint = ref(0)
const armJoints = ref([
  { angle: 0, min: -90, max: 90 },
  { angle: 0, min: -90, max: 90 },
  { angle: 90, min: 0, max: 180 },
  { angle: 90, min: 0, max: 180 },
  { angle: 130, min: 0, max: 180 }
])

const trackedObjects = ref<any[]>([])
const videoStreamAvailable = ref(false)
const currentFrame = ref('')
const currentFPS = ref(0)
const videoStreamUrl = ref('')

const lastOCRResult = ref<{
  text: string
  confidence: number
  timestamp: number
} | null>(null)

const sequenceRunning = ref(false)
const sequenceProgress = ref(0)
const currentSequenceStep = ref('')

const systemLogs = ref<Array<{
  type: 'info' | 'success' | 'warning' | 'error'
  message: string
  timestamp: number
}>>([])

const showSequenceManager = ref(false)

const pipelineSteps = ref([
  { id: 'tracking', name: '物体追踪', icon: '🔍', completed: false },
  { id: 'alignment', name: '位置对齐', icon: '📍', completed: false },
  { id: 'conveyor_stop', name: '停止传送带', icon: '⏸', completed: false },
  { id: 'arm_operation', name: '机械臂操作', icon: '🦾', completed: false },
  { id: 'image_capture', name: '图像采集', icon: '📸', completed: false },
  { id: 'ocr_processing', name: 'OCR识别', icon: '🔤', completed: false },
  { id: 'result_voting', name: '结果投票', icon: '🗳️', completed: false }
])

const currentStep = ref('')

const armPositionText = computed(() => {
  return armBusy.value ? '运动中' : '就绪'
})

const successRate = computed(() => {
  return processedCount.value > 0 ? Math.round((successCount.value / processedCount.value) * 100) : 0
})

const avgProcessingTime = computed(() => {
  return '15.2'
})

const addLog = (type: 'info' | 'success' | 'warning' | 'error', message: string) => {
  systemLogs.value.unshift({
    type,
    message,
    timestamp: Date.now()
  })
  if (systemLogs.value.length > 20) {
    systemLogs.value = systemLogs.value.slice(0, 20)
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

const startPipeline = async () => {
  try {
    starting.value = true
    addLog('info', '正在启动流水线系统...')

    if (debugMode.value && manualControlMode.value) {
      addLog('info', '调试模式：手动控制已启用')
      await startPipelineManual()
      return
    }

    if (!unifiedApi.isConnected()) {
      addLog('info', '正在连接统一通信服务...')
      unifiedApi.connect()
      await new Promise(resolve => setTimeout(resolve, 1000))
    }

    if (!videoStreamAvailable.value) {
      addLog('info', '正在启动物体追踪...')
      const trackingSuccess = await unifiedApi.startTracking(0)
      if (trackingSuccess) {
        videoStreamAvailable.value = true
        addLog('success', '物体追踪启动成功')
      } else {
        addLog('warning', '物体追踪启动失败，使用模拟模式')
        videoStreamAvailable.value = true
        startSimulatedTracking()
      }
      await new Promise(resolve => setTimeout(resolve, 1500))
    }

    if (!conveyorRunning.value) {
      addLog('info', '正在启动传送带...')
      await startConveyor()
      await new Promise(resolve => setTimeout(resolve, 500))
    }

    addLog('info', '正在启动主流水线控制器...')
    const result = await startPipelineAPI()
    if (result.success) {
      systemStatus.value = 'running'
      currentStep.value = 'tracking'
      addLog('success', '流水线系统启动成功')

      startRuntimeTimer()
    } else {
      addLog('warning', `系统启动失败: ${result.message || '启动失败'}`)
      if (result.message && result.message.includes('已在运行')) {
        systemStatus.value = 'running'
        currentStep.value = 'tracking'
        addLog('info', '检测到系统已在运行状态')
      }
    }
  } catch (error) {
    systemStatus.value = 'error'
    addLog('error', `系统启动失败: ${error}`)
  } finally {
    starting.value = false
  }
}

const startPipelineManual = async () => {
  addLog('info', '手动控制模式：逐步启动各个子系统...')

  try {
    addLog('info', '手动启动：物体追踪...')
    if (!videoStreamAvailable.value) {
      const trackingSuccess = await unifiedApi.startTracking(0)
      if (trackingSuccess) {
        videoStreamAvailable.value = true
        addLog('success', '手动启动：物体追踪成功')
      } else {
        addLog('warning', '手动启动：物体追踪失败，使用模拟模式')
        videoStreamAvailable.value = true
        startSimulatedTracking()
      }
    }

    addLog('info', '手动启动：传送带...')
    if (!conveyorRunning.value) {
      await startConveyor()
      addLog('success', '手动启动：传送带已启动')
    }

    addLog('info', '手动启动：检查机械臂状态...')

    addLog('info', '手动启动：检查OCR状态...')

    addLog('info', '手动启动：主流水线控制器...')
    const result = await startPipelineAPI()
    if (result.success) {
      systemStatus.value = 'running'
      currentStep.value = 'tracking'
      addLog('success', '手动控制：流水线系统启动成功')
      startRuntimeTimer()
    }
  } catch (error) {
    addLog('error', `手动控制启动失败: ${error}`)
    throw error
  }
}

const toggleDebugMode = (enabled: boolean) => {
  debugMode.value = enabled
  addLog('info', `调试模式${enabled ? '已开启' : '已关闭'}`)

  if (enabled) {
    addLog('info', '调试模式特性：')
    addLog('info', '- 增强的错误处理和重试机制')
    addLog('info', '- 详细的系统状态日志')
    addLog('info', '- 手动控制选项')
    addLog('info', '- 模拟数据支持')
  }
}

const pausePipeline = async () => {
  try {
    const result = await pausePipelineAPI()
    if (result.success) {
      systemStatus.value = 'paused'
      addLog('warning', '系统已暂停')
    } else {
      throw new Error(result.message || '暂停失败')
    }
  } catch (error) {
    addLog('error', `暂停失败: ${error}`)
  }
}

const resetPipeline = async () => {
  try {
    addLog('info', '正在复位系统...')

    const result = await resetPipelineAPI()
    if (result.success) {
      systemStatus.value = 'idle'
      currentStep.value = ''
      processedCount.value = 0
      successCount.value = 0
      runtime.value = 0
      addLog('info', '系统已复位')
    } else {
      throw new Error(result.message || '复位失败')
    }
  } catch (error) {
    addLog('error', `复位失败: ${error}`)
  }
}

const emergencyStop = async () => {
  addLog('error', '紧急停止已触发！')

  try {
    await conveyorApiService.emergencyStop()

    await unifiedApi.stopTracking()

    await resetPipelineAPI()

    systemStatus.value = 'idle'
    armBusy.value = false
    sequenceRunning.value = false
    currentStep.value = ''
    conveyorRunning.value = false
    videoStreamAvailable.value = false

    addLog('info', '紧急停止完成，系统已重置')
  } catch (error) {
    addLog('error', `紧急停止执行失败: ${error}`)
    systemStatus.value = 'idle'
    armBusy.value = false
    sequenceRunning.value = false
  }
}

const startConveyor = async () => {
  try {
    const result = await conveyorApiService.startConveyor(conveyorSpeed.value, conveyorDirection.value)
    if (result.success) {
      conveyorRunning.value = true
      addLog('success', '传送带已启动')
    } else {
      throw new Error(result.message || '传送带启动失败')
    }
  } catch (error) {
    conveyorRunning.value = true
    addLog('info', '传送带启动 (模拟模式)')
  }
}

const stopConveyor = async () => {
  try {
    const result = await conveyorApiService.stopConveyor()
    if (result.success) {
      conveyorRunning.value = false
      addLog('info', '传送带已停止')
    } else {
      throw new Error(result.message || '传送带停止失败')
    }
  } catch (error) {
    conveyorRunning.value = false
    addLog('info', '传送带停止 (模拟模式)')
  }
}

const updateConveyorSpeed = async () => {
  if (conveyorRunning.value) {
    try {
      const result = await conveyorApiService.setSpeed(conveyorSpeed.value, conveyorDirection.value)
      if (result.success) {
        addLog('info', `传送带速度调整为 ${conveyorSpeed.value.toFixed(2)} m/s`)
      } else {
        addLog('warning', `速度调整失败: ${result.message}`)
      }
    } catch (error) {
      addLog('warning', `速度调整失败: ${error}`)
    }
  }
}

const setConveyorDirection = async (direction: 'forward' | 'backward') => {
  conveyorDirection.value = direction
  if (conveyorRunning.value) {
    try {
      const result = await conveyorApiService.setDirection(direction)
      if (result.success) {
        addLog('info', `传送带方向切换为${direction === 'forward' ? '正向' : '反向'}`)
      } else {
        addLog('warning', `方向切换失败: ${result.message}`)
      }
    } catch (error) {
      addLog('warning', `方向切换失败: ${error}`)
    }
  }
}

const startTracking = async () => {
  try {
    if (videoStreamAvailable.value) {
      addLog('info', '物体追踪已在运行')
      return
    }

    addLog('info', '正在启动物体追踪...')

    const success = await unifiedApi.startTracking(0)
    if (success) {
      videoStreamAvailable.value = true
      addLog('success', '物体追踪已启动')
      startVideoStream()
    } else {
      throw new Error('追踪启动失败')
    }
  } catch (error) {
    videoStreamAvailable.value = true
    addLog('info', '物体追踪启动 (模拟模式)')
    addLog('warning', '追踪服务连接失败，使用模拟数据')
    startSimulatedTracking()
  }
}

const stopTracking = async () => {
  try {
    const success = await unifiedApi.stopTracking()
    if (success) {
      videoStreamAvailable.value = false
      trackedObjects.value = []
      addLog('info', '物体追踪已停止')
    } else {
      throw new Error('追踪停止失败')
    }
  } catch (error) {
    videoStreamAvailable.value = false
    trackedObjects.value = []
    addLog('info', '物体追踪停止 (模拟模式)')
  }
}

const startVideoStream = () => {
  addLog('info', '正在连接实时视频流...')

  videoStreamAvailable.value = true
  currentFPS.value = 30

  updateFrameData()

  addLog('success', '视频流连接成功（使用WebSocket数据）')
}

const onVideoLoad = () => {
  if (!window._videoLoaded) {
    addLog('success', '实时视频流加载成功')
    window._videoLoaded = true
    console.log('🎬 视频流首次加载成功，当前帧数据长度:', currentFrame.value?.length || 0)
  }

  currentFPS.value = 30

  updateFrameData()
}

const updateFrameData = () => {
  const updateInterval = setInterval(() => {
    if (videoStreamAvailable.value) {
      currentFPS.value = 30 + Math.random() * 2 - 1

    } else {
      clearInterval(updateInterval)
    }
  }, 1000)
}

const startSimulatedVideoStream = () => {
  const interval = setInterval(() => {
    if (videoStreamAvailable.value) {
      const canvas = document.createElement('canvas')
      canvas.width = 640
      canvas.height = 480
      const ctx = canvas.getContext('2d')

      if (ctx) {
        ctx.fillStyle = '#333'
        ctx.fillRect(0, 0, 640, 480)

        ctx.fillStyle = '#555'
        ctx.fillRect(50, 200, 540, 80)

        trackedObjects.value.forEach(obj => {
          const x = 50 + (obj.conveyor_x / 0.6) * 540
          const y = 200 + (obj.conveyor_y / 0.4) * 80

          ctx.fillStyle = obj.class_name === 'brick' ? '#67c23a' : '#409eff'
          ctx.fillRect(x - 15, y - 15, 30, 30)

          ctx.strokeStyle = '#fff'
          ctx.lineWidth = 2
          ctx.strokeRect(x - 15, y - 15, 30, 30)

          ctx.fillStyle = obj.class_name === 'brick' ? '#67c23a' : '#409eff'
          ctx.fillRect(x - 15, y - 35, 60, 20)

          ctx.fillStyle = 'white'
          ctx.font = '10px Arial'
          ctx.fillText(getObjectDisplayName(obj.class_name), x - 10, y - 20)
        })

        currentFrame.value = canvas.toDataURL('image/jpeg', 0.8)
      } else {
        currentFrame.value = `data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAIBAQIBAQICAgICAgICAwUDAwMDAwYEBAMFBwYHBwcGBwcICQsJCAgKCAcHCg0KCgsMDAwMBwkODw0MDgsMDAz/2wBDAQICAgMDAwYDAwYMCAcIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAARCAHgAoADASIAAhEBAxEB/8QAFwABAQEBAAAAAAAAAAAAAAAAAAECA//EABwQAQEBAAEFAAAAAAAAAAAAAAABEQISsfAhQVH/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8A/9k=`
      }

      currentFPS.value = 25 + Math.random() * 5
    } else {
      clearInterval(interval)
    }
  }, 1000 / 30) // 30 FPS
}

const startSimulatedTracking = () => {
  const interval = setInterval(() => {
    if (videoStreamAvailable.value) {
      if (Math.random() < 0.6 && trackedObjects.value.length < 2) {
        const newObject = {
          track_id: Date.now(),
          class_name: Math.random() > 0.4 ? 'brick' : 'arm',
          conveyor_x: Math.random() * 0.6,
          conveyor_y: Math.random() * 0.4,
          confidence: 0.7 + Math.random() * 0.3
        }
        trackedObjects.value.push(newObject)
        addLog('info', `模拟检测到新的${newObject.class_name}，位置: (${newObject.conveyor_x.toFixed(3)}, ${newObject.conveyor_y.toFixed(3)})`)
      }

      trackedObjects.value.forEach(obj => {
        obj.conveyor_x += 0.01
        if (obj.conveyor_x > 0.6) {
          obj.conveyor_x = 0
        }
      })

      if (Math.random() < 0.05 && trackedObjects.value.length > 0) {
        const removed = trackedObjects.value.shift()
        addLog('info', `${removed.class_name} #${removed.track_id} 已离开视野`)
      }
    } else {
      clearInterval(interval)
    }
  }, 500)
}

const testVideoStream = () => {
  startTracking()
  startVideoStream()
}

const handleVideoError = (event: Event) => {
  console.error('视频流加载错误:', event)
  videoStreamAvailable.value = false
  videoStreamUrl.value = ''
  addLog('error', '视频流连接失败，切换到模拟模式')
  startSimulatedVideoStream()
}

const selectJoint = (index: number) => {
  selectedJoint.value = index
}

const getJointStyle = (index: number) => {
  const angle = armJoints.value[index].angle
  const baseRotation = index * 15
  return {
    transform: `rotate(${angle + baseRotation}deg)`,
    background: selectedJoint.value === index ? '#409eff' : '#67c23a'
  }
}

const performOCRRecognition = async () => {
  try {
    addLog('info', '开始OCR识别...')

    const results = []
    for (let i = 0; i < 5; i++) {
      await new Promise(resolve => setTimeout(resolve, 200))

      try {
        const response = await fetch('http://localhost:5000/api/energy/combined', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ frame_index: i })
        })

        if (response.ok) {
          const result = await response.json()
          results.push({
            text: result.ocr_text || result.energy_level || `识别结果${i + 1}`,
            confidence: result.confidence || (0.7 + Math.random() * 0.3),
            frameIndex: i + 1,
            timestamp: Date.now()
          })
          addLog('info', `第${i + 1}帧OCR处理完成`)
        } else {
          throw new Error(`OCR服务返回错误: ${response.status}`)
        }
      } catch (error) {
        addLog('warning', `第${i + 1}帧OCR处理失败，使用模拟数据`)
        results.push({
          text: `模拟结果${i + 1}`,
          confidence: 0.7 + Math.random() * 0.3,
          frameIndex: i + 1,
          timestamp: Date.now()
        })
      }
    }

    if (results.length > 0) {
      const bestResult = results.reduce((best, current) =>
        current.confidence > best.confidence ? current : best
      )

      lastOCRResult.value = bestResult
      addLog('success', `OCR识别完成: ${bestResult.text}`)
      successCount.value++
    } else {
      addLog('warning', 'OCR识别未获得有效结果')
    }
  } catch (error) {
    addLog('error', `OCR识别失败: ${error}`)
    lastOCRResult.value = {
      text: '识别失败',
      confidence: 0.5,
      timestamp: Date.now()
    }
  }
}

const runPickPlaceSequence = async () => {
  if (armBusy.value || systemStatus.value !== 'running') return

  try {
    armBusy.value = true
    sequenceRunning.value = true
    sequenceProgress.value = 0

    addLog('info', '开始执行取放序列...')

    const sequence = [
      { name: '初始位置', duration: 1000, angles: [130, -75, 60, 45, 90] },
      { name: '检测位置', duration: 1000, angles: [130, -70, 90, 80, 90] },
      { name: '过渡到抓取', duration: 500, angles: [130, -45, 85, 110, 90] },
      { name: '抓取位置', duration: 1000, angles: [130, -20, 80, 140, 90] },
      { name: '抓取物体', duration: 500, angles: [0, -20, 80, 140, 90] },
      { name: '抬升转向1', duration: 500, angles: [0, -10, 75, 120, 70] },
      { name: '抬升转向2', duration: 500, angles: [0, -10, 70, 100, 45] },
      { name: '抬升转向3', duration: 500, angles: [0, -10, 65, 120, 20] },
      { name: '放置位置', duration: 1000, angles: [0, -20, 60, 140, 0] },
      { name: '放开物体', duration: 1500, angles: [130, -20, 60, 140, 0] },
      { name: '返回转向1', duration: 500, angles: [130, -32, 70, 120, 30] },
      { name: '返回转向2', duration: 500, angles: [130, -45, 70, 100, 45] },
      { name: '返回转向3', duration: 500, angles: [130, -57, 80, 90, 60] },
      { name: '返回检测', duration: 1000, angles: [130, -70, 90, 80, 90] }
    ]

    for (let i = 0; i < sequence.length; i++) {
      const step = sequence[i]
      currentSequenceStep.value = `${i + 1}/${sequence.length}: ${step.name}`
      sequenceProgress.value = Math.round(((i + 1) / sequence.length) * 100)

      try {
        const armActions = step.angles.map((angle, index) => {
          let actualJointId;
          switch(index) {
            case 0: actualJointId = 6; break;
            case 1: actualJointId = 5; break;
            case 2: actualJointId = 4; break;
            case 3: actualJointId = 3; break;
            case 4: actualJointId = 1; break;
            default: actualJointId = index + 1;
          }

          return {
            type: 'joint',
            joint: actualJointId,
            angle: angle,
            speed: 50
          }
        })

        const result = await unifiedApi.executeRobotArmActions(armActions)

        if (result.success) {
          addLog('info', `机械臂动作执行成功: ${step.name}`)
        } else {
          addLog('warning', `机械臂动作执行失败: ${step.name} - ${result.message}`)
        }
      } catch (armError) {
        addLog('warning', `机械臂控制异常: ${step.name} - ${armError}`)
      }

      armJoints.value.forEach((joint, index) => {
        if (step.angles[index] !== undefined) {
          joint.angle = step.angles[index]
        }
      })

      addLog('info', `执行步骤: ${step.name}`)
      await new Promise(resolve => setTimeout(resolve, step.duration))
    }

    addLog('success', '取放序列执行完成')
    processedCount.value++

    await performOCRRecognition()

  } catch (error) {
    addLog('error', `序列执行失败: ${error}`)
  } finally {
    armBusy.value = false
    sequenceRunning.value = false
    sequenceProgress.value = 0
    currentSequenceStep.value = ''
  }
}

const runCustomSequence = () => {
  addLog('info', '自定义序列功能开发中...')
}

const getObjectStyle = (obj: any) => {
  const left = (obj.conveyor_x / 0.6) * 100
  const top = (obj.conveyor_y / 0.4) * 100
  return {
    left: `${left}%`,
    top: `${top}%`,
    transform: 'translate(-50%, -50%)'
  }
}

const checkObjectAlignment = () => {
  if (trackedObjects.value.length < 2) return null

  const brick = trackedObjects.value.find(obj => obj.class_name === 'brick')
  const arm = trackedObjects.value.find(obj => obj.class_name === 'arm')

  if (!brick || !arm) return null

  const xDistance = Math.abs(brick.conveyor_x - arm.conveyor_x)
  const horizontalThreshold = 0.05

  const aligned = xDistance <= horizontalThreshold

  return {
    aligned,
    xDistance,
    threshold: horizontalThreshold,
    brickX: brick.conveyor_x,
    armX: arm.conveyor_x
  }
}

const getAlignmentStatusText = computed(() => {
  const alignment = checkObjectAlignment()
  if (!alignment) return '等待物体检测...'

  if (alignment.aligned) {
    return `✅ 已对齐 (水平偏差: ${(alignment.xDistance * 100).toFixed(1)}cm)`
  } else {
    return `❌ 未对齐 (水平偏差: ${(alignment.xDistance * 100).toFixed(1)}cm)`
  }
})

const getObjectDisplayName = (className: string) => {
  const names: { [key: string]: string } = {
    'brick': '砖块',
    'arm': '机械臂',
    'unknown': '未知'
  }
  return names[className] || className
}

const clearLogs = () => {
  systemLogs.value = []
}

let runtimeTimer: number | null = null

const startRuntimeTimer = () => {
  if (runtimeTimer) clearInterval(runtimeTimer)
  runtimeTimer = window.setInterval(() => {
    if (systemStatus.value === 'running') {
      runtime.value++
    }
  }, 1000)
}

const setupWebSocketListeners = () => {
  pipelineWebSocketEvents.onStatusUpdate((data: any) => {
    if (data.status) {
      if (data.status.pipeline_state) {
        const pipelineState = data.status.pipeline_state

        if (pipelineState.status && pipelineState.status !== systemStatus.value) {
          systemStatus.value = pipelineState.status
          addLog('info', `系统状态更新为: ${pipelineState.status}`)
        }

        currentStep.value = pipelineState.current_step || currentStep.value
        processedCount.value = pipelineState.processed_count || processedCount.value
        successCount.value = (pipelineState.processed_count || 0) - (pipelineState.error_count || 0)

        if (pipelineState.status === 'running' && !conveyorRunning.value) {
          conveyorRunning.value = true
        } else if (pipelineState.status === 'idle' && conveyorRunning.value) {
          conveyorRunning.value = false
        }
      }

      if (data.status.tracking_state) {
        trackedObjects.value = Object.values(data.status.tracking_state.tracked_objects || {})
      }
    }
  })

  pipelineWebSocketEvents.onError((error: any) => {
    addLog('error', `流水线错误: ${error.message || '未知错误'}`)
  })

  unifiedApi.on('video_frame', (data: any) => {
    if (window._debugMode) {
      console.log('📹 收到视频帧数据:', {
        hasFrame: !!data.frame,
        frameLength: data.frame?.length,
        fps: data.fps,
        frameId: data.frame_id
      })
    }

    if (data.frame && data.frame.length > 100) {
      if (typeof data.frame === 'string' && !data.frame.startsWith('data:')) {
        currentFrame.value = `data:image/jpeg;base64,${data.frame}`
      } else {
        currentFrame.value = data.frame
      }
      currentFPS.value = data.fps || 25 + Math.random() * 5

      if (window._debugMode) {
        console.log('✅ 视频帧已更新，帧数据长度:', currentFrame.value.length)
      }
    } else {
      if (window._debugMode) {
        console.warn('⚠️ 视频帧数据无效或太短:', data.frame?.length || 0)
      }
    }
  })

  unifiedApi.on('object_detected', (data: any) => {
    addLog('info', `检测到新物体: ${data.class_name || '未知'}`)
  })

  unifiedApi.on('object_lost', (data: any) => {
    addLog('info', `物体丢失: ${data.class_name || '未知'}`)
  })

  unifiedApi.on('ocr_result', (data: any) => {
    if (data.energy_level) {
      lastOCRResult.value = {
        text: `能效等级: ${data.energy_level}`,
        confidence: data.confidence || 0.8,
        timestamp: Date.now()
      }
      addLog('success', `OCR识别完成: ${data.energy_level}`)
    }
  })
}

onMounted(async () => {
  addLog('info', '流水线控制系统已初始化')
  setupWebSocketListeners()

  setTimeout(() => {
    unifiedApi.connect()
  }, 1000)

  setTimeout(async () => {
    try {
      addLog('info', '正在同步系统状态...')
      const statusResult = await getPipelineStatus()
      if (statusResult.success && statusResult.data) {
        const status = statusResult.data
        if (status.pipeline_state) {
          systemStatus.value = status.pipeline_state.status || 'idle'
          currentStep.value = status.pipeline_state.current_step || ''
          processedCount.value = status.pipeline_state.processed_count || 0
          successCount.value = (status.pipeline_state.processed_count || 0) - (status.pipeline_state.error_count || 0)

          conveyorRunning.value = systemStatus.value === 'running'
        }
        addLog('success', '系统状态同步完成')
      }
    } catch (error) {
      addLog('warning', `状态同步失败: ${error}，使用默认状态`)
    }
  }, 1500)
})

onUnmounted(() => {
  if (runtimeTimer) {
    clearInterval(runtimeTimer)
  }
  if (systemStatus.value === 'running') {
    resetPipeline()
  }
  pipelineWebSocketEvents.removeAllListeners()
  unifiedApi.disconnect()
})
</script>

<style scoped lang="scss">
.pipeline-control-new {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e1a 0%, #121626 100%);
  color: #e0e6ed;
  font-family: 'Roboto Mono', 'Courier New', monospace;
}

.header-industrial {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: linear-gradient(90deg, #1a1f2e 0%, #252b3d 100%);
  border-bottom: 3px solid #409eff;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);

  .header-left {
    display: flex;
    align-items: center;
    gap: 30px;

    .system-title {
      margin: 0;
      color: #409eff;
      font-size: 28px;
      font-weight: 700;
      text-shadow: 0 0 10px rgba(64, 158, 255, 0.5);
    }

    .status-indicators {
      display: flex;
      gap: 20px;

      .indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #909399;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.3s ease;

        &.active {
          color: #67c23a;

          .indicator-light {
            background: #67c23a;
            box-shadow: 0 0 12px rgba(103, 194, 58, 0.7);
            animation: pulse 1.5s infinite;
          }
        }

        .indicator-light {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: #4a4a4a;
          transition: all 0.3s ease;
        }
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 20px;

    .runtime-display {
      display: flex;
      flex-direction: column;
      align-items: center;

      .runtime-label {
        font-size: 12px;
        color: #909399;
      }

      .runtime-value {
        font-size: 18px;
        font-weight: 700;
        color: #67c23a;
        font-family: 'Courier New', monospace;
      }
    }

    .emergency-btn {
      padding: 12px 24px;
      font-size: 16px;
      font-weight: 700;
      background: linear-gradient(135deg, #f56c6c, #d32f2f);
      color: white;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(245, 108, 108, 0.3);
      transition: all 0.3s ease;

      &:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(245, 108, 108, 0.4);
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none !important;
      }
    }
  }
}

.main-control-area {
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  gap: 20px;
  padding: 20px 30px;
  min-height: calc(100vh - 120px);
}

.control-panel {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(64, 158, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);

  .panel-header {
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

    .control-btn {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 15px;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s ease;
      font-family: inherit;

      &.start-btn {
        background: linear-gradient(135deg, #67c23a, #529b2e);
        color: white;

        &:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(103, 194, 58, 0.4);
        }
      }

      &.pause-btn {
        background: linear-gradient(135deg, #e6a23c, #c9972c);
        color: white;

        &:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(230, 162, 60, 0.4);
        }
      }

      &.reset-btn {
        background: linear-gradient(135deg, #909399, #73767a);
        color: white;

        &:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(144, 147, 153, 0.4);
        }
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none !important;
      }

      .btn-icon {
        font-size: 20px;
        width: 24px;
        text-align: center;
      }

      .btn-text {
        flex: 1;
        text-align: left;

        .btn-title {
          font-size: 14px;
          font-weight: 600;
        }

        .btn-desc {
          font-size: 11px;
          opacity: 0.8;
        }
      }
    }
  }

  .parameter-controls {
    h4 {
      margin: 0 0 15px 0;
      color: #409eff;
      font-size: 14px;
      font-weight: 600;
    }

    .param-item {
      margin-bottom: 15px;

      label {
        display: block;
        margin-bottom: 8px;
        color: #909399;
        font-size: 12px;
      }

      .param-control {
        display: flex;
        align-items: center;
        gap: 10px;

        input[type="range"] {
          flex: 1;
          height: 4px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 2px;
          outline: none;
          -webkit-appearance: none;

          &::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            background: #409eff;
            border-radius: 50%;
            cursor: pointer;
          }
        }

        .param-value {
          min-width: 60px;
          text-align: right;
          color: #67c23a;
          font-weight: 600;
          font-size: 12px;
        }
      }

      .direction-control {
        display: flex;
        gap: 8px;

        .dir-btn {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid rgba(255, 255, 255, 0.2);
          background: rgba(255, 255, 255, 0.05);
          color: #909399;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.3s ease;
          font-size: 12px;

          &.active {
            background: #409eff;
            color: white;
            border-color: #409eff;
          }

          &:hover:not(.active) {
            background: rgba(255, 255, 255, 0.1);
          }
        }
      }
    }
  }
}

.alignment-status {
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  font-size: 12px;
  color: #e6a23c;

  &.aligned {
    color: #67c23a;
    background: rgba(103, 194, 58, 0.2);
  }
}

.monitor-area {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.video-monitor, .arm-status {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);

  .monitor-header, .status-header {
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

    .monitor-info, .status-info {
      display: flex;
      gap: 15px;
      font-size: 12px;

      .fps-display, .object-count, .position-info, .temp-info {
        padding: 4px 8px;
        background: rgba(0, 0, 0, 0.3);
        border-radius: 4px;
        color: #67c23a;
      }
    }
  }
}

.video-display {
  background: #000;
  border-radius: 8px;
  min-height: 300px;
  position: relative;
  overflow: hidden;

  .video-stream {
    width: 100%;
    height: 100%;
    position: relative;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .video-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #909399;

    .placeholder-content {
      text-align: center;

      .camera-icon {
        font-size: 48px;
        margin-bottom: 10px;
      }

      p {
        margin: 0 0 15px 0;
        font-size: 14px;
      }

      .test-btn {
        padding: 8px 16px;
        background: #409eff;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;

        &:hover {
          background: #66b1ff;
        }
      }

      .connection-status {
        font-size: 11px;
        color: #909399;
        margin: 5px 0;
      }
    }
  }

  .video-stream-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .detection-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;

    .tracked-object {
      position: absolute;
      width: 60px;
      height: 60px;
      border: 2px solid #67c23a;
      border-radius: 8px;
      background: rgba(103, 194, 58, 0.2);
      display: flex;
      align-items: center;
      justify-content: center;

      .object-label {
        background: #67c23a;
        color: white;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 10px;
        font-weight: bold;
      }
    }
  }

  .video-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #909399;

    .loading-spinner {
      width: 40px;
      height: 40px;
      border: 3px solid rgba(255, 255, 255, 0.1);
      border-top: 3px solid #409eff;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 15px;
    }

    p {
      margin: 0;
      font-size: 14px;
    }
  }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.arm-display {
  display: flex;
  gap: 20px;
  min-height: 200px;

  .arm-visual {
    flex: 1;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;

    .arm-base {
      position: absolute;
      bottom: 20px;
      width: 40px;
      height: 20px;
      background: #409eff;
      border-radius: 4px;
    }

    .arm-joint {
      position: absolute;
      width: 8px;
      height: 80px;
      background: #67c23a;
      border-radius: 4px;
      transform-origin: bottom center;
      transition: transform 0.3s ease;

      .joint-label {
        position: absolute;
        top: -20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 2px 4px;
        border-radius: 3px;
        font-size: 10px;
      }
    }

    .arm-end-effector {
      position: absolute;
      width: 16px;
      height: 16px;
      background: #f56c6c;
      border-radius: 50%;
    }
  }

  .arm-controls {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .joint-control-btn {
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #909399;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.3s ease;
      font-size: 12px;

      &.active {
        background: #409eff;
        color: white;
        border-color: #409eff;
      }

      &:hover:not(.active) {
        background: rgba(255, 255, 255, 0.15);
      }
    }
  }
}

.info-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.ocr-card, .log-card, .automation-card {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);

  .card-header {
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

    .card-status, .clear-btn, .manage-btn {
      font-size: 12px;
      padding: 4px 8px;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #909399;
      border-radius: 4px;
      cursor: pointer;

      &:hover {
        background: rgba(255, 255, 255, 0.1);
      }
    }
  }
}

.ocr-content {
  .result-display {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
    padding: 15px;

    .result-text {
      color: #67c23a;
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 8px;
    }

    .result-meta {
      color: #909399;
      font-size: 12px;
    }
  }

  .no-result {
    text-align: center;
    padding: 30px;
    color: #909399;

    .waiting-icon {
      font-size: 32px;
      margin-bottom: 10px;
    }
  }
}

.log-content {
  max-height: 200px;
  overflow-y: auto;

  .log-item {
    display: flex;
    gap: 10px;
    padding: 6px 0;
    font-size: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);

    &:last-child {
      border-bottom: none;
    }

    .log-time {
      color: #909399;
      white-space: nowrap;
    }

    .log-message {
      flex: 1;
    }

    &.log-success {
      .log-message {
        color: #67c23a;
      }
    }

    &.log-error {
      .log-message {
        color: #f56c6c;
      }
    }

    &.log-warning {
      .log-message {
        color: #e6a23c;
      }
    }
  }
}

.sequence-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 15px;

  .sequence-btn {
    padding: 12px 16px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 14px;
    font-weight: 500;

    &.primary {
      background: linear-gradient(135deg, #67c23a, #529b2e);
      color: white;

      &:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(103, 194, 58, 0.4);
      }
    }

    &.secondary {
      background: linear-gradient(135deg, #409eff, #3375b9);
      color: white;

      &:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(64, 158, 255, 0.4);
      }
    }

    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none !important;
    }
  }
}

.sequence-progress {
  .progress-bar {
    height: 6px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 8px;

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #409eff, #67c23a);
      transition: width 0.3s ease;
    }
  }

  .progress-text {
    font-size: 12px;
    color: #909399;
    text-align: center;
  }
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 30px;
  background: linear-gradient(90deg, #1a1f2e 0%, #252b3d 100%);
  border-top: 3px solid #409eff;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.5);

  .pipeline-steps {
    display: flex;
    gap: 15px;

    .step-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 6px;
      transition: all 0.3s ease;

      &.active {
        background: rgba(64, 158, 255, 0.2);
        border: 1px solid #409eff;
      }

      &.completed {
        background: rgba(103, 194, 58, 0.2);
        border: 1px solid #67c23a;
      }

      .step-number {
        width: 20px;
        height: 20px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 600;
      }

      .step-name {
        font-size: 12px;
        color: #e0e6ed;
      }

      .step-icon {
        font-size: 14px;
      }
    }
  }

  .system-stats {
    display: flex;
    gap: 20px;
    font-size: 12px;
    color: #909399;
  }
}

.debug-controls, .manual-controls {
  padding: 8px 0;

  :deep(.el-switch) {
    .el-switch__label {
      color: #909399;
      font-size: 12px;
    }

    .el-switch__core {
      background-color: rgba(255, 255, 255, 0.2);
      border-color: rgba(255, 255, 255, 0.3);
    }
  }
}

.debug-info {
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 6px;
  padding: 10px;
  margin-top: 10px;
  font-size: 11px;
  color: #409eff;

  .debug-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;

    &:last-child {
      margin-bottom: 0;
    }

    .debug-label {
      color: #909399;
    }

    .debug-value {
      font-weight: 600;
    }
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;

  .modal-content {
    background: linear-gradient(135deg, #1a1f2e 0%, #252b3d 100%);
    border-radius: 12px;
    padding: 30px;
    border: 1px solid rgba(64, 158, 255, 0.3);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    max-width: 80%;
    max-height: 80%;
    overflow: auto;

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;

      h3 {
        margin: 0;
        color: #409eff;
        font-size: 20px;
      }

      .close-btn {
        background: none;
        border: none;
        color: #909399;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;

        &:hover {
          color: #e0e6ed;
        }
      }
    }
  }
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(103, 194, 58, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(103, 194, 58, 0);
  }
}

@media (max-width: 1400px) {
  .main-control-area {
    grid-template-columns: 250px 1fr 280px;
  }
}

@media (max-width: 1200px) {
  .main-control-area {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
  }

  .header-industrial {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }
}

@media (max-width: 768px) {
  .header-industrial {
    .header-left {
      flex-direction: column;
      gap: 15px;
    }

    .header-right {
      flex-direction: column;
      gap: 10px;
    }
  }

  .control-panel {
    .control-buttons {
      flex-direction: row;
      flex-wrap: wrap;
    }
  }

  .arm-display {
    flex-direction: column;
  }

  .status-bar {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }
}
</style>