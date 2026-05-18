<template>
  <div class="pipeline-coordinator">
    <div class="pipeline-overview">
      <h3>流水线协调控制</h3>

      <div class="status-cards">
        <div class="status-card" :class="pipelineStatus">
          <div class="status-icon">
            <el-icon><Operation /></el-icon>
          </div>
          <div class="status-info">
            <div class="status-text">{{ getStatusText(pipelineStatus) }}</div>
            <div class="step-text">{{ currentStep }}</div>
          </div>
        </div>

        <div class="stats-card">
          <div class="stat-item">
            <span class="label">已处理</span>
            <span class="value">{{ stats.processed }}</span>
          </div>
          <div class="stat-item">
            <span class="label">成功率</span>
            <span class="value">{{ stats.successRate }}%</span>
          </div>
          <div class="stat-item">
            <span class="label">当前物体</span>
            <span class="value">{{ currentObjectId || '无' }}</span>
          </div>
        </div>
      </div>

      <div class="control-buttons">
        <el-button
          type="success"
          :disabled="pipelineStatus === 'running'"
          @click="startPipeline"
        >
          <el-icon><VideoPlay /></el-icon>
          启动流水线
        </el-button>

        <el-button
          type="warning"
          :disabled="pipelineStatus !== 'running'"
          @click="pausePipeline"
        >
          <el-icon><VideoPause /></el-icon>
          暂停流水线
        </el-button>

        <el-button
          type="danger"
          :disabled="pipelineStatus === 'idle'"
          @click="stopPipeline"
        >
          <el-icon><SwitchButton /></el-icon>
          停止流水线
        </el-button>

        <el-button
          type="info"
          @click="resetPipeline"
        >
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
      </div>
    </div>

    <div class="real-time-monitor">
      <h4>实时状态监控</h4>

      <div class="monitor-grid">
        <div class="monitor-item">
          <label>物体追踪状态</label>
          <el-tag :type="trackingStatus ? 'success' : 'info'">
            {{ trackingStatus ? '运行中' : '已停止' }}
          </el-tag>
        </div>

        <div class="monitor-item">
          <label>传送带状态</label>
          <el-tag :type="conveyorStatus === 'running' ? 'success' : 'info'">
            {{ conveyorStatus === 'running' ? '运行中' : '已停止' }}
          </el-tag>
        </div>

        <div class="monitor-item">
          <label>机械臂状态</label>
          <el-tag :type="armStatus === 'running' ? 'warning' : 'info'">
            {{ armStatus === 'running' ? '运行中' : '待机' }}
          </el-tag>
        </div>

        <div class="monitor-item">
          <label>检测到物体</label>
          <span class="object-count">{{ trackedObjects.length }}</span>
        </div>
      </div>

      <div class="object-positions" v-if="trackedObjects.length > 0">
        <h5>物体位置信息</h5>
        <div class="position-list">
          <div
            v-for="obj in trackedObjects"
            :key="obj.track_id"
            class="position-item"
            :class="{ 'target-object': isTargetObject(obj) }"
          >
            <span class="object-id">ID: {{ obj.track_id }}</span>
            <span class="object-type">{{ obj.class_name === 'brick' ? '砖块' : '机械臂' }}</span>
            <span class="object-position">
              X: {{ obj.conveyor_x?.toFixed(3) || 0 }}m
              Y: {{ obj.conveyor_y?.toFixed(3) || 0 }}m
            </span>
            <span class="object-distance" v-if="obj.class_name === 'brick'">
              距离: {{ calculateDistance(obj).toFixed(3) }}m
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="event-log">
      <h4>操作日志</h4>
      <div class="log-container">
        <div
          v-for="(log, index) in eventLog"
          :key="index"
          class="log-item"
          :class="`log-${log.type}`"
        >
          <span class="log-time">{{ log.timestamp }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import {
  Operation,
  VideoPlay,
  VideoPause,
  SwitchButton,
  Refresh
} from '@element-plus/icons-vue'

import {
  startTracking,
  stopTracking,
  getCurrentObjects,
  onObjectDetected,
  onFrameProcessed
} from '../api/trackingApi'

import {
  startConveyor,
  stopConveyor,
  setSpeed,
  getConveyorStatus
} from '../api/conveyorApi'

import {
  runSequence as runArmSequence
} from '../api/robotArmApi'

import {
  detectEnergy
} from '../api/energyDetectionApi'

const pipelineStatus = ref<'idle' | 'running' | 'paused' | 'error'>('idle')
const trackingStatus = ref(false)
const conveyorStatus = ref<'stopped' | 'running'>('stopped')
const armStatus = ref<'idle' | 'running'>('idle')
const currentStep = ref('等待启动')
const currentObjectId = ref<string | null>(null)
const trackedObjects = ref<any[]>([])
const eventLog = ref<Array<{type: string, message: string, timestamp: string}>>([])

const stats = ref({
  processed: 0,
  success: 0,
  failed: 0,
  get successRate() {
    return this.processed > 0 ? Math.round((this.success / this.processed) * 100) : 0
  }
})

const config = ref({
  captureDistance: 0.05,
  capturePosition: 0.3,
  frameInterval: 2,
  frameCount: 5,
  conveyorSpeed: 0.1
})

const isTargetObject = (obj: any) => {
  return obj.class_name === 'brick' &&
         Math.abs(obj.conveyor_x - config.value.capturePosition) < config.value.captureDistance
}

const calculateDistance = (obj: any) => {
  return Math.abs(obj.conveyor_x - config.value.capturePosition)
}

const addLog = (type: string, message: string) => {
  const timestamp = new Date().toLocaleTimeString('zh-CN')
  eventLog.value.unshift({
    type,
    message,
    timestamp
  })

  if (eventLog.value.length > 50) {
    eventLog.value = eventLog.value.slice(0, 50)
  }
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'idle': '空闲',
    'running': '运行中',
    'paused': '已暂停',
    'error': '错误'
  }
  return statusMap[status] || status
}

const startPipeline = async () => {
  try {
    pipelineStatus.value = 'running'
    currentStep.value = '启动物体追踪'
    addLog('info', '启动流水线')

    await startTracking(0)
    trackingStatus.value = true
    addLog('success', '物体追踪已启动')

    await startConveyor(config.value.conveyorSpeed, 'forward')
    conveyorStatus.value = 'running'
    addLog('success', '传送带已启动')

    currentStep.value = '监控物体位置'
    ElMessage.success('流水线已启动')

  } catch (error) {
    pipelineStatus.value = 'error'
    addLog('error', `启动流水线失败: ${error}`)
    ElMessage.error('启动流水线失败')
  }
}

const pausePipeline = () => {
  pipelineStatus.value = 'paused'
  currentStep.value = '已暂停'
  addLog('warning', '流水线已暂停')
  ElMessage.info('流水线已暂停')
}

const stopPipeline = async () => {
  try {
    await stopConveyor()
    conveyorStatus.value = 'stopped'

    await stopTracking()
    trackingStatus.value = false

    pipelineStatus.value = 'idle'
    currentStep.value = '已停止'
    trackedObjects.value = []
    currentObjectId.value = null

    addLog('info', '流水线已停止')
    ElMessage.info('流水线已停止')

  } catch (error) {
    addLog('error', `停止流水线失败: ${error}`)
    ElMessage.error('停止流水线失败')
  }
}

const resetPipeline = () => {
  stats.value = {
    processed: 0,
    success: 0,
    failed: 0,
    get successRate() {
      return this.processed > 0 ? Math.round((this.success / this.processed) * 100) : 0
    }
  }
  eventLog.value = []
  addLog('info', '流水线已重置')
  ElMessage.success('流水线已重置')
}

const handleObjectDetection = async (data: any) => {
  if (pipelineStatus.value !== 'running') return

  const obj = data.object
  if (obj.class_name === 'brick' && isTargetObject(obj)) {
    currentObjectId.value = obj.track_id
    currentStep.value = '检测到目标物体，准备抓取'
    addLog('success', `检测到目标砖块 ID: ${obj.track_id}`)

    await executeCaptureSequence(obj)
  }
}

const executeCaptureSequence = async (targetObject: any) => {
  try {
    currentStep.value = '停止传送带'
    await stopConveyor()
    conveyorStatus.value = 'stopped'
    addLog('info', '传送带已停止')

    currentStep.value = '执行机械臂抓取'
    armStatus.value = 'running'

    const captureSequence = {
      name: "取放工件流程",
      steps: [
        {
          "name": "初始位置",
          "duration": 1000,
          "actions": [
            { "jointId": 1, "angle": 130 },
            { "jointId": 3, "angle": -75 },
            { "jointId": 4, "angle": 60 },
            { "jointId": 5, "angle": 45 },
            { "jointId": 6, "angle": 90 }
          ]
        },
        {
          "name": "检测位置",
          "duration": 1000,
          "actions": [
            { "jointId": 1, "angle": 130 },
            { "jointId": 3, "angle": -70 },
            { "jointId": 4, "angle": 90 },
            { "jointId": 5, "angle": 80 },
            { "jointId": 6, "angle": 90 }
          ]
        },
        {
          "name": "过渡到抓取",
          "duration": 500,
          "actions": [
            { "jointId": 1, "angle": 130 },
            { "jointId": 3, "angle": -45 },
            { "jointId": 4, "angle": 85 },
            { "jointId": 5, "angle": 110 },
            { "jointId": 6, "angle": 90 }
          ]
        },
        {
          "name": "抓取位置",
          "duration": 1000,
          "actions": [
            { "jointId": 1, "angle": 130 },
            { "jointId": 3, "angle": -20 },
            { "jointId": 4, "angle": 80 },
            { "jointId": 5, "angle": 140 },
            { "jointId": 6, "angle": 90 }
          ]
        },
        {
          "name": "抓取物体",
          "duration": 500,
          "actions": [
            { "jointId": 1, "angle": 0 }
          ]
        },
        {
          "name": "抬升转向1",
          "duration": 500,
          "actions": [
            { "jointId": 1, "angle": 0 },
            { "jointId": 3, "angle": -10 },
            { "jointId": 4, "angle": 75 },
            { "jointId": 5, "angle": 120 },
            { "jointId": 6, "angle": 70 }
          ]
        },
        {
          "name": "抬升转向2",
          "duration": 500,
          "actions": [
            { "jointId": 1, "angle": 0 },
            { "jointId": 3, "angle": -10 },
            { "jointId": 4, "angle": 70 },
            { "jointId": 5, "angle": 100 },
            { "jointId": 6, "angle": 45 }
          ]
        },
        {
          "name": "抬升转向3",
          "duration": 500,
          "actions": [
            { "jointId": 1, "angle": 0 },
            { "jointId": 3, "angle": -10 },
            { "jointId": 4, "angle": 65 },
            { "jointId": 5, "angle": 120 },
            { "jointId": 6, "angle": 20 }
          ]
        },
        {
          "name": "放置位置",
          "duration": 1000,
          "actions": [
            { "jointId": 1, "angle": 0 },
            { "jointId": 3, "angle": -20 },
            { "jointId": 4, "angle": 60 },
            { "jointId": 5, "angle": 140 },
            { "jointId": 6, "angle": 0 }
          ]
        },
        {
          "name": "放开物体",
          "duration": 1500,
          "actions": [
            { "jointId": 1, "angle": 130 }
          ]
        },
        {
          "name": "返回转向1",
          "duration": 500,
          "actions": [
            { "jointId": 1, "angle": 130 },
            { "jointId": 3, "angle": -32 },
            { "jointId": 4, "angle": 70 },
            { "jointId": 5, "angle": 120 },
            { "jointId": 6, "angle": 30 }
          ]
        },
        {
          "name": "返回转向2",
          "duration": 500,
          "actions": [
            { "jointId": 1, "angle": 130 },
            { "jointId": 3, "angle": -45 },
            { "jointId": 4, "angle": 70 },
            { "jointId": 5, "angle": 100 },
            { "jointId": 6, "angle": 45 }
          ]
        },
        {
          "name": "返回转向3",
          "duration": 500,
          "actions": [
            { "jointId": 1, "angle": 130 },
            { "jointId": 3, "angle": -57 },
            { "jointId": 4, "angle": 80 },
            { "jointId": 5, "angle": 90 },
            { "jointId": 6, "angle": 60 }
          ]
        },
        {
          "name": "返回检测位置",
          "duration": 1000,
          "actions": [
            { "jointId": 1, "angle": 130 },
            { "jointId": 3, "angle": -70 },
            { "jointId": 4, "angle": 90 },
            { "jointId": 5, "angle": 80 },
            { "jointId": 6, "angle": 90 }
          ]
        }
      ]
    }

    const actions = captureSequence.steps.flatMap(step => {
      return {
        type: "multi_joint",
        name: step.name,
        movetime: step.duration,
        servos: step.actions.map(action => ({
          jointId: action.jointId,
          angle: action.angle
        }))
      }
    })

    await runArmSequence(actions)
    addLog('success', '机械臂抓取序列执行完成')

    currentStep.value = '启动传送带并进行OCR识别'
    await startConveyor(config.value.conveyorSpeed, 'forward')
    conveyorStatus.value = 'running'

    await executeMultiFrameOCR()

    stats.value.processed++
    stats.value.success++

    currentStep.value = '处理完成，等待下一个物体'
    currentObjectId.value = null
    armStatus.value = 'idle'

    addLog('success', `物体 ${targetObject.track_id} 处理完成`)

  } catch (error) {
    pipelineStatus.value = 'error'
    armStatus.value = 'idle'
    addLog('error', `抓取序列执行失败: ${error}`)
    ElMessage.error('抓取序列执行失败')
  }
}

const executeMultiFrameOCR = async () => {
  currentStep.value = '执行多帧OCR识别'
  addLog('info', '开始多帧OCR识别')

  const frameResults: any[] = []
  let frameCount = 0

  for (let i = 0; i < config.value.frameCount; i++) {
    await new Promise(resolve => setTimeout(resolve, config.value.frameInterval * 100))

    try {
      const result = await detectEnergy()
      if (result && result.success) {
        frameResults.push(result)
        frameCount++
        addLog('info', `第${i + 1}帧OCR识别完成`)
      }
    } catch (error) {
      addLog('warning', `第${i + 1}帧OCR识别失败`)
    }
  }

  if (frameResults.length > 0) {
    const bestResult = frameResults[0]
    addLog('success', `OCR识别完成，最佳结果: ${JSON.stringify(bestResult.data)}`)
    currentStep.value = `OCR识别完成: ${bestResult.data?.result || '未知'}`
  } else {
    addLog('warning', 'OCR识别无有效结果')
    currentStep.value = 'OCR识别无有效结果'
  }
}

const handleFrameProcessed = (data: any) => {
  if (data.frame_data && data.frame_data.tracked_objects) {
    trackedObjects.value = data.frame_data.tracked_objects
  }
}

onMounted(() => {
  onObjectDetected(handleObjectDetection)
  onFrameProcessed(handleFrameProcessed)

  addLog('info', '流水线协调器已初始化')
})

onUnmounted(() => {
  if (pipelineStatus.value === 'running') {
    stopPipeline()
  }
})
</script>

<style scoped lang="scss">
.pipeline-coordinator {
  padding: 20px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;

  h3 {
    margin-top: 0;
    color: #409eff;
    margin-bottom: 20px;
  }

  .pipeline-overview {
    margin-bottom: 25px;

    .status-cards {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 20px;

      .status-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 20px;
        display: flex;
        align-items: center;
        gap: 15px;
        border-left: 4px solid #409eff;

        &.running {
          border-left-color: #67c23a;
        }

        &.paused {
          border-left-color: #e6a23c;
        }

        &.error {
          border-left-color: #f56c6c;
        }

        .status-icon {
          .el-icon {
            font-size: 32px;
            color: #409eff;
          }
        }

        .status-info {
          .status-text {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
          }

          .step-text {
            font-size: 14px;
            color: #909399;
          }
        }
      }

      .stats-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 20px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;

        .stat-item {
          text-align: center;

          .label {
            display: block;
            font-size: 12px;
            color: #909399;
            margin-bottom: 5px;
          }

          .value {
            display: block;
            font-size: 20px;
            font-weight: bold;
            color: #409eff;
          }
        }
      }
    }

    .control-buttons {
      display: flex;
      gap: 12px;
      justify-content: center;

      .el-button {
        min-width: 120px;
        padding: 12px 20px;
      }
    }
  }

  .real-time-monitor {
    margin-bottom: 25px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 20px;

    h4 {
      margin-top: 0;
      color: #67c23a;
      margin-bottom: 15px;
    }

    .monitor-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 15px;
      margin-bottom: 20px;

      .monitor-item {
        display: flex;
        flex-direction: column;
        gap: 8px;

        label {
          font-size: 14px;
          color: #909399;
        }

        .object-count {
          font-size: 18px;
          font-weight: bold;
          color: #67c23a;
        }
      }
    }

    .object-positions {
      h5 {
        margin: 0 0 10px 0;
        color: #e6a23c;
      }

      .position-list {
        max-height: 200px;
        overflow-y: auto;

        .position-item {
          padding: 10px;
          background: rgba(0, 0, 0, 0.2);
          border-radius: 6px;
          margin-bottom: 8px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 13px;

          &.target-object {
            background: rgba(103, 194, 58, 0.2);
            border: 1px solid rgba(103, 194, 58, 0.5);
          }

          .object-id {
            font-weight: bold;
          }

          .object-type {
            color: #409eff;
          }

          .object-position {
            color: #e6a23c;
          }

          .object-distance {
            color: #67c23a;
            font-weight: bold;
          }
        }
      }
    }
  }

  .event-log {
    h4 {
      margin-top: 0;
      color: #e6a23c;
      margin-bottom: 15px;
    }

    .log-container {
      height: 200px;
      overflow-y: auto;
      background: rgba(0, 0, 0, 0.3);
      border-radius: 6px;
      padding: 15px;

      .log-item {
        font-size: 13px;
        margin-bottom: 8px;
        display: flex;
        gap: 12px;

        .log-time {
          color: rgba(255, 255, 255, 0.6);
          white-space: nowrap;
          min-width: 80px;
        }

        .log-message {
          color: rgba(255, 255, 255, 0.9);
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

        &.log-info {
          .log-message {
            color: #909399;
          }
        }
      }
    }
  }
}

@media (max-width: 900px) {
  .pipeline-coordinator {
    .pipeline-overview {
      .status-cards {
        grid-template-columns: 1fr;
      }
    }

    .real-time-monitor {
      .monitor-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }
  }
}
</style>