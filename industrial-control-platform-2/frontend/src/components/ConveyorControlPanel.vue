<template>
  <div class="conveyor-control-panel" :class="{ 'compact-mode': compactMode }">
    <div class="panel-header">
      <div class="header-actions">
        <el-button
          size="small"
          :type="compactMode ? 'primary' : 'default'"
          @click="toggleCompactMode"
        >
          <el-icon><FullScreen /></el-icon>
          {{ compactMode ? '展开' : '收起' }}
        </el-button>
        <el-button
          size="small"
          type="info"
          @click="refreshStatus"
          :loading="refreshing"
        >
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <div class="status-monitor-section">
      <div class="status-indicators">
        <div class="status-indicator" :class="getStatusClass(conveyorStatus.status)">
          <div class="status-light"></div>
          <span class="status-text">{{ getStatusText(conveyorStatus.status) }}</span>
        </div>

        <div class="speed-display">
          <div class="speed-value">
            {{ (conveyorStatus.currentSpeed || 0).toFixed(3) }}
            <span class="speed-unit">m/s</span>
          </div>
          <div class="speed-comparison">
            <span class="target-speed">目标: {{ (conveyorStatus.targetSpeed || 0).toFixed(3) }} m/s</span>
            <span class="actual-speed">实际: {{ (conveyorStatus.actualSpeed || 0).toFixed(3) }} m/s</span>
          </div>
        </div>

        <div class="direction-display">
          <el-tag
            :type="conveyorStatus.direction === 'forward' ? 'success' : 'warning'"
            size="large"
          >
            <el-icon>
              <component :is="conveyorStatus.direction === 'forward' ? 'ArrowRight' : 'ArrowLeft'" />
            </el-icon>
            {{ conveyorStatus.direction === 'forward' ? '正向' : '反向' }}
          </el-tag>
        </div>
      </div>

      <div class="device-info" v-if="!compactMode">
        <div class="info-item">
          <span class="label">设备类型:</span>
          <span class="value">{{ getDeviceTypeText(conveyorStatus.deviceType) }}</span>
        </div>
        <div class="info-item">
          <span class="label">速度范围:</span>
          <span class="value">
            {{ (conveyorStatus.speedRange?.min || 0).toFixed(3) }} - {{ (conveyorStatus.speedRange?.max || 5).toFixed(3) }} m/s
          </span>
        </div>
        <div class="info-item" v-if="conveyorStatus.temperature">
          <span class="label">设备温度:</span>
          <span class="value" :class="getTemperatureClass(conveyorStatus.temperature)">
            {{ conveyorStatus.temperature }}°C
          </span>
        </div>
        <div class="info-item" v-if="conveyorStatus.healthScore">
          <span class="label">健康评分:</span>
          <span class="value" :class="getHealthScoreClass(conveyorStatus.healthScore)">
            {{ conveyorStatus.healthScore }}%
          </span>
        </div>
      </div>
    </div>

    <div class="main-control-section">
      <div class="control-buttons">
        <el-button
          class="start-button control-button"
          :type="conveyorStatus.isRunning ? 'warning' : 'success'"
          size="large"
          @click="toggleConveyor"
          :loading="controlling"
        >
          <el-icon>
            <component :is="conveyorStatus.isRunning ? 'VideoPause' : 'VideoPlay'" />
          </el-icon>
          {{ conveyorStatus.isRunning ? '停止传送带' : '启动传送带' }}
        </el-button>

        <el-button
          class="emergency-button control-button"
          type="danger"
          size="large"
          @click="emergencyStop"
          :disabled="!conveyorStatus.isRunning"
        >
          <el-icon><Warning /></el-icon>
          紧急停止
        </el-button>
      </div>
    </div>

    <div class="parameter-control-section" v-if="!compactMode">
      <div class="speed-control-group">
        <h4>速度控制</h4>
        <div class="speed-slider">
          <el-slider
            v-model="currentSpeed"
            :min="getSpeedRange().min"
            :max="getSpeedRange().max"
            :step="0.001"
            :format-tooltip="formatSpeedTooltip"
            show-stops
            :show-input="true"
            input-size="small"
            @change="updateConveyorSpeed"
          />
          <div class="speed-input-precise">
            <el-input-number
              v-model.number="preciseSpeedInput"
              :min="getSpeedRange().min"
              :max="getSpeedRange().max"
              :step="0.001"
              size="small"
              controls-position="right"
              @change="applyPreciseSpeed"
            />
            <span class="unit">m/s</span>
            <el-button
              type="primary"
              size="small"
              @click="applyPreciseSpeed"
              :disabled="!isValidSpeed(parseFloat(preciseSpeedInput) || 0)"
            >
              应用
            </el-button>
          </div>
        </div>
      </div>

      <div class="direction-control-group">
        <h4>方向选择</h4>
        <div class="direction-options">
          <el-radio-group v-model="currentDirection" @change="updateDirection">
            <el-radio label="forward" size="large">
              <el-icon><ArrowRight /></el-icon>
              正向
            </el-radio>
            <el-radio label="backward" size="large">
              <el-icon><ArrowLeft /></el-icon>
              反向
            </el-radio>
          </el-radio-group>
          <el-button
            type="primary"
            size="small"
            @click="toggleDirection"
            :disabled="controlling"
          >
            <el-icon><Refresh /></el-icon>
            切换方向
          </el-button>
        </div>
      </div>

      <div class="speed-presets-group">
        <h4>速度预设</h4>
        <div class="preset-buttons">
          <el-button
            v-for="preset in speedPresets"
            :key="preset.speed"
            size="small"
            :type="currentSpeed === preset.speed ? 'primary' : 'default'"
            @click="applySpeedPreset(preset.speed)"
            :disabled="!isValidSpeed(preset.speed)"
          >
            {{ (preset.speed || 0).toFixed(3) }} m/s
            <el-tooltip
              :content="preset.description"
              placement="top"
            >
              <el-icon><InfoFilled /></el-icon>
            </el-tooltip>
          </el-button>
        </div>
      </div>
    </div>

    <div class="device-info-section" v-if="!compactMode">
      <h4>设备信息</h4>
      <div class="device-details">
        <div class="device-capability">
          <span class="label">设备速度能力:</span>
          <span class="value">
            {{ (conveyorStatus.speedRange?.min || 0).toFixed(3) }} - {{ (conveyorStatus.speedRange?.max || 5).toFixed(3) }} m/s
          </span>
        </div>
        <div class="speed-recommendations">
          <span class="label">应用建议:</span>
          <div class="recommendation-tags">
            <el-tag
              v-for="rec in speedRecommendations"
              :key="rec.speed"
              size="small"
              :type="getRecommendationType(rec.type) as any"
              @click="applySpeedPreset(rec.speed)"
              class="recommendation-tag"
            >
              {{ rec.description }}({{ (rec.speed || 0).toFixed(3) }})
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <div class="safety-control-section">
      <div class="safety-buttons">
        <el-button
          type="info"
          size="small"
          @click="resetSystem"
          :disabled="conveyorStatus.isRunning"
        >
          <el-icon><RefreshRight /></el-icon>
          系统复位
        </el-button>
        <el-button
          type="warning"
          size="small"
          @click="refreshStatus"
          :loading="refreshing"
        >
          <el-icon><Refresh /></el-icon>
          状态刷新
        </el-button>
        <el-button
          type="danger"
          size="small"
          @click="clearFaults"
          :disabled="conveyorStatus.status !== 'error'"
        >
          <el-icon><CloseBold /></el-icon>
          故障复位
        </el-button>
      </div>
    </div>

    <div class="alert-section" v-if="showAlerts">
      <el-alert
        v-if="conveyorStatus.errorMessage"
        :title="conveyorStatus.errorMessage"
        type="error"
        :closable="true"
        show-icon
      />
      <el-alert
        v-for="(warning, index) in conveyorStatus.warningMessages"
        :key="index"
        :title="warning"
        type="warning"
        :closable="true"
        show-icon
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Promotion,
  FullScreen,
  Refresh,
  VideoPlay,
  VideoPause,
  Warning,
  ArrowRight,
  ArrowLeft,
  InfoFilled,
  RefreshRight,
  CloseBold
} from '@element-plus/icons-vue'
import { conveyorApiService, conveyorWebSocketService } from '../api/conveyorApi'
import type {
  ConveyorStatus,
  ConveyorDirection,
  DeviceType,
  SpeedRecommendation
} from '../types/conveyor'

// Props
const props = defineProps<{
  compactMode?: boolean
}>()

const conveyorStatus = ref<ConveyorStatus>({
  isRunning: false,
  currentSpeed: 0.0,
  targetSpeed: 0.0,
  actualSpeed: 0.0,
  direction: 'forward',
  status: 'stopped',
  deviceType: 'unknown',
  speedRange: { min: 0.001, max: 0.8 },
  temperature: 25,
  load: 0,
  healthScore: 100,
  lastUpdate: new Date().toISOString()
})

const controlling = ref(false)
const refreshing = ref(false)
const compactMode = ref(props.compactMode || false)

const currentSpeed = ref(0.1)
const preciseSpeedInput = ref(0.100)
const currentDirection = ref<ConveyorDirection>('forward')

const speedPresets = ref([
  { speed: 0.001, description: '极低速' },
  { speed: 0.010, description: '低速' },
  { speed: 0.100, description: '标准速度' },
  { speed: 0.300, description: '中速' },
  { speed: 0.500, description: '高速' },
  { speed: 0.800, description: '极高速' }
])

const speedRecommendations = ref<SpeedRecommendation[]>([
  { speed: 0.005, description: '精密装配', type: 'precision' },
  { speed: 0.020, description: '质量检测', type: 'inspection' },
  { speed: 0.100, description: '标准输送', type: 'standard' },
  { speed: 0.500, description: '中速分拣', type: 'medium-speed' },
  { speed: 0.800, description: '高速分拣', type: 'high-speed' }
])

const showAlerts = computed(() => {
  return conveyorStatus.value.errorMessage ||
         (conveyorStatus.value.warningMessages && conveyorStatus.value.warningMessages.length > 0)
})

const getStatusClass = (status: string) => {
  const statusMap: Record<string, string> = {
    'stopped': 'stopped',
    'running': 'running',
    'adjusting': 'adjusting',
    'error': 'error',
    'emergency_stop': 'emergency'
  }
  return statusMap[status] || 'stopped'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'stopped': '已停止',
    'running': '运行中',
    'adjusting': '调整中',
    'error': '错误',
    'emergency_stop': '紧急停止'
  }
  return statusMap[status] || '未知状态'
}

const getDeviceTypeText = (deviceType: DeviceType) => {
  const typeMap: Record<DeviceType, string> = {
    'standard': '标准传送带',
    'lightweight': '轻型传送带',
    'heavy_duty': '重型传送带',
    'precision': '精密传送带',
    'unknown': '未知设备'
  }
  return typeMap[deviceType]
}

const getTemperatureClass = (temp: number) => {
  if (temp > 70) return 'high-temp'
  if (temp > 60) return 'medium-temp'
  return 'normal-temp'
}

const getHealthScoreClass = (score: number) => {
  if (score >= 90) return 'excellent'
  if (score >= 80) return 'good'
  if (score >= 70) return 'fair'
  return 'poor'
}

const getRecommendationType = (type: string) => {
  const typeMap: Record<string, any> = {
    'precision': 'success',
    'inspection': 'info',
    'standard': 'primary',
    'high-speed': 'warning',
    'medium-speed': 'warning',
    'default': 'info'
  }
  return typeMap[type] || 'info'
}

const formatSpeedTooltip = (value: number) => {
  return `${value.toFixed(3)} m/s`
}

const isValidSpeed = (speed: number) => {
  const range = getSpeedRange()
  return speed >= range.min && speed <= range.max
}

const getSpeedRange = () => {
  return conveyorStatus.value.speedRange || { min: 0.001, max: 0.8 }
}

const toggleConveyor = async () => {
  try {
    controlling.value = true
    if (conveyorStatus.value.isRunning) {
      const result = await conveyorApiService.stopConveyor()
      if (result.success) {
        ElMessage.success('传送带已停止')
        conveyorStatus.value.isRunning = false
        conveyorStatus.value.status = 'stopped'
        conveyorStatus.value.currentSpeed = 0
        conveyorStatus.value.targetSpeed = 0
        currentSpeed.value = 0
        preciseSpeedInput.value = 0
      } else {
        ElMessage.error(`停止失败: ${result.message}`)
      }
    } else {
      const result = await conveyorApiService.startConveyor(currentSpeed.value, currentDirection.value)
      if (result.success) {
        ElMessage.success('传送带已启动')
        conveyorStatus.value.isRunning = true
        conveyorStatus.value.status = 'running'
        conveyorStatus.value.targetSpeed = currentSpeed.value
        conveyorStatus.value.currentSpeed = currentSpeed.value
      } else {
        ElMessage.error(`启动失败: ${result.message}`)
      }
    }
    await refreshStatus()
  } catch (error: any) {
    ElMessage.error(`操作失败: ${error.message}`)
  } finally {
    controlling.value = false
  }
}

const emergencyStop = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要紧急停止传送带吗？此操作将立即停止传送带运行。',
      '紧急停止',
      {
        confirmButtonText: '紧急停止',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'emergency-confirm-button'
      }
    )

    controlling.value = true
    const result = await conveyorApiService.emergencyStop()
    if (result.success) {
      ElMessage.warning('传送带已紧急停止')
      await refreshStatus()
    } else {
      ElMessage.error(`紧急停止失败: ${result.message}`)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('紧急停止操作失败')
    }
  } finally {
    controlling.value = false
  }
}

const updateConveyorSpeed = async (speed: number) => {
  if (!isValidSpeed(speed)) {
    const range = getSpeedRange()
    ElMessage.error(`速度必须在 ${range.min.toFixed(3)} - ${range.max.toFixed(3)} m/s 范围内`)
    return
  }

  try {
    controlling.value = true
    const result = await conveyorApiService.setSpeed(speed)
    if (result.success) {
      ElMessage.success(`速度已设置为 ${(speed || 0).toFixed(3)} m/s`)
      conveyorStatus.value.targetSpeed = speed
      conveyorStatus.value.currentSpeed = speed
      conveyorStatus.value.isRunning = speed > 0
      conveyorStatus.value.status = speed > 0 ? 'running' : 'stopped'
      await refreshStatus()
    } else {
      ElMessage.error(`设置速度失败: ${result.message}`)
    }
  } catch (error: any) {
    ElMessage.error(`设置速度失败: ${error.message}`)
  } finally {
    controlling.value = false
  }
}

const applyPreciseSpeed = () => {
  const speed = typeof preciseSpeedInput.value === 'string'
    ? parseFloat(preciseSpeedInput.value)
    : preciseSpeedInput.value

  if (!isNaN(speed) && isValidSpeed(speed)) {
    updateConveyorSpeed(speed)
  } else {
    ElMessage.error('请输入有效的速度值')
  }
}

const updateDirection = async (direction: ConveyorDirection) => {
  if (conveyorStatus.value.isRunning) {
    ElMessage.warning('传送带运行中，无法更改方向')
    return
  }
  currentDirection.value = direction
}

const toggleDirection = async () => {
  try {
    controlling.value = true

    const newDirection = currentDirection.value === 'forward' ? 'backward' : 'forward'

    currentDirection.value = newDirection
    conveyorStatus.value.direction = newDirection

    if (conveyorStatus.value.isRunning) {
      const result = await conveyorApiService.setSpeed(currentSpeed.value, newDirection)
      if (result.success) {
        ElMessage.info(`方向已切换为${newDirection === 'forward' ? '正向' : '反向'}`)
        await refreshStatus()
      } else {
        ElMessage.error(`切换方向失败: ${result.message}`)
        const revertedDirection = newDirection === 'forward' ? 'backward' : 'forward'
        currentDirection.value = revertedDirection
        conveyorStatus.value.direction = revertedDirection
      }
    } else {
      ElMessage.info(`方向已设置为${newDirection === 'forward' ? '正向' : '反向'}`)
    }
  } catch (error: any) {
    ElMessage.error(`切换方向失败: ${error.message}`)
    const revertedDirection = currentDirection.value === 'forward' ? 'backward' : 'forward'
    currentDirection.value = revertedDirection
    conveyorStatus.value.direction = revertedDirection
  } finally {
    controlling.value = false
  }
}

const applySpeedPreset = (speed: number) => {
  if (isValidSpeed(speed)) {
    currentSpeed.value = speed
    preciseSpeedInput.value = parseFloat((speed || 0).toFixed(3))
    if (conveyorStatus.value.isRunning) {
      updateConveyorSpeed(speed)
    } else {
      conveyorStatus.value.targetSpeed = speed
    }
  }
}

const refreshStatus = async () => {
  try {
    refreshing.value = true
    const status = await conveyorApiService.getConveyorStatus()

    Object.assign(conveyorStatus.value, status)

    if (status.targetSpeed > 0) {
      currentSpeed.value = status.targetSpeed
      preciseSpeedInput.value = parseFloat((status.targetSpeed || 0).toFixed(3))
    }

    if (status.direction && status.direction !== currentDirection.value) {
      currentDirection.value = status.direction
    }

    if (!conveyorStatus.value.speedRange) {
      conveyorStatus.value.speedRange = { min: 0.001, max: 0.8 }
    }

    try {
      const capabilities = await conveyorApiService.getDeviceCapabilities()
      conveyorStatus.value.speedRange = capabilities.speedRange
      conveyorStatus.value.deviceType = capabilities.deviceType
    } catch (capError) {
      console.warn('获取设备能力失败:', capError)
    }

    try {
      const recommendations = await conveyorApiService.getSpeedRecommendations()
      speedRecommendations.value = recommendations
    } catch (recError) {
      console.warn('获取速度建议失败:', recError)
    }
  } catch (error: any) {
    console.error('刷新状态失败:', error)
    ElMessage.error(`刷新状态失败: ${error.message}`)
  } finally {
    refreshing.value = false
  }
}

const resetSystem = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要复位系统吗？所有参数将恢复默认值。',
      '系统复位',
      {
        confirmButtonText: '复位',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    const result = await conveyorApiService.resetSystem()
    if (result.success) {
      ElMessage.info('系统已复位')
      await refreshStatus()
    } else {
      ElMessage.error(`系统复位失败: ${result.message}`)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('系统复位失败')
    }
  }
}

const clearFaults = async () => {
  try {
    const result = await conveyorApiService.resetSystem()
    if (result.success) {
      ElMessage.success('故障已清除')
      await refreshStatus()
    } else {
      ElMessage.error(`清除故障失败: ${result.message}`)
    }
  } catch (error: any) {
    ElMessage.error(`清除故障失败: ${error.message}`)
  }
}

const toggleCompactMode = () => {
  compactMode.value = !compactMode.value
}

onMounted(() => {
  refreshStatus()

  conveyorWebSocketService.onStatusUpdate((status: ConveyorStatus) => {
    const userSpeed = currentSpeed.value
    const userDirection = currentDirection.value

    conveyorStatus.value = status

    if (status.targetSpeed !== undefined && status.targetSpeed !== userSpeed) {
      currentSpeed.value = status.targetSpeed
      preciseSpeedInput.value = parseFloat((status.targetSpeed || 0).toFixed(3))
    }

    if (status.direction && status.direction !== userDirection) {
      currentDirection.value = status.direction
    }
  })
})

onUnmounted(() => {
  conveyorWebSocketService.disconnect()
})
</script>

<style scoped lang="scss">
.conveyor-control-panel {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 2px solid #0f3460;
  border-radius: 12px;
  padding: 24px;
  color: #e94560;
  font-family: 'Courier New', monospace;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;

  &.compact-mode {
    padding: 16px;

    .parameter-control-section,
    .device-info-section {
      display: none;
    }
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);

    .panel-title {
      margin: 0;
      color: #e94560;
      font-size: 1.5rem;
      font-weight: bold;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }
  }

  .status-monitor-section {
    margin-bottom: 20px;

    .status-indicators {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 20px;
      align-items: center;
      margin-bottom: 15px;

      .status-indicator {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 15px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);

        .status-light {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          transition: all 0.3s ease;

          &.stopped { background: #909399; }
          &.running {
            background: #67c23a;
            box-shadow: 0 0 10px rgba(103, 194, 58, 0.7);
            animation: pulse 2s infinite;
          }
          &.adjusting {
            background: #e6a23c;
            box-shadow: 0 0 10px rgba(230, 162, 60, 0.7);
            animation: pulse 1s infinite;
          }
          &.error {
            background: #f56c6c;
            box-shadow: 0 0 10px rgba(245, 108, 108, 0.7);
            animation: pulse 0.5s infinite;
          }
          &.emergency {
            background: #d32f2f;
            box-shadow: 0 0 15px rgba(211, 47, 47, 0.8);
            animation: pulse 0.3s infinite;
          }
        }

        .status-text {
          font-weight: bold;
          font-size: 0.9rem;
        }
      }

      .speed-display {
        text-align: center;
        padding: 10px;
        background: rgba(0, 0, 0, 0.3);
        border-radius: 8px;
        border: 1px solid #4a5568;

        .speed-value {
          font-size: 1.8rem;
          font-weight: bold;
          color: #48bb78;
          margin-bottom: 5px;

          .speed-unit {
            font-size: 0.9rem;
            color: #a0aec0;
            margin-left: 4px;
          }
        }

        .speed-comparison {
          display: flex;
          justify-content: space-around;
          font-size: 0.8rem;
          color: #a0aec0;

          .target-speed {
            color: #409eff;
          }
          .actual-speed {
            color: #67c23a;
          }
        }
      }
    }

    .device-info {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
      padding: 15px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 8px;

      .info-item {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .label {
          color: #a0aec0;
          font-size: 0.9rem;
        }

        .value {
          font-weight: bold;
          font-size: 0.9rem;

          &.high-temp { color: #f56c6c; }
          &.medium-temp { color: #e6a23c; }
          &.normal-temp { color: #67c23a; }

          &.excellent { color: #67c23a; }
          &.good { color: #e6a23c; }
          &.fair { color: #f56c6c; }
          &.poor { color: #d32f2f; }
        }
      }
    }
  }

  .main-control-section {
    margin-bottom: 20px;

    .control-buttons {
      display: flex;
      gap: 15px;
      justify-content: center;

      .control-button {
        min-width: 160px;
        min-height: 48px;
        font-size: 16px;
        font-weight: bold;
        border-radius: 8px;
        transition: all 0.3s ease;

        &.start-button {
          background: linear-gradient(45deg, #00d2ff, #3a7bd5);
          border: none;
          color: white;

          &:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(58, 123, 213, 0.4);
          }
        }

        &.emergency-button {
          background: #d32f2f;
          border: 3px solid #b71c1c;
          color: white;
          font-size: 16px;
          font-weight: bold;

          &:hover:not(:disabled) {
            background: #b71c1c;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(183, 28, 28, 0.4);
          }
        }
      }
    }
  }

  .parameter-control-section {
    margin-bottom: 20px;

    .speed-control-group,
    .direction-control-group,
    .speed-presets-group {
      margin-bottom: 20px;
      padding: 15px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 8px;

      h4 {
        margin: 0 0 15px 0;
        color: #409eff;
        font-size: 1.1rem;
      }

      .speed-slider {
        .speed-input-precise {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 10px;

          .unit {
            color: #a0aec0;
            font-size: 0.9rem;
          }
        }
      }

      .direction-options {
        display: flex;
        align-items: center;
        gap: 20px;
      }

      .preset-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
    }
  }

  .device-info-section {
    margin-bottom: 20px;
    padding: 15px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;

    h4 {
      margin: 0 0 15px 0;
      color: #409eff;
      font-size: 1.1rem;
    }

    .device-details {
      .device-capability {
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;

        .label {
          color: #a0aec0;
        }
        .value {
          font-weight: bold;
        }
      }

      .speed-recommendations {
        .label {
          color: #a0aec0;
          margin-bottom: 8px;
          display: block;
        }

        .recommendation-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;

          .recommendation-tag {
            cursor: pointer;
            transition: all 0.3s ease;

            &:hover {
              transform: translateY(-2px);
              box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            }
          }
        }
      }
    }
  }

  .safety-control-section {
    .safety-buttons {
      display: flex;
      justify-content: center;
      gap: 10px;
    }
  }

  .alert-section {
    margin-top: 15px;
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

:deep(.emergency-confirm-button) {
  background: #d32f2f !important;
  border-color: #b71c1c !important;
}
</style>