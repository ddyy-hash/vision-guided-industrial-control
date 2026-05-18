<template>
  <div class="device-statistics">
    <div class="stats-header">
      <h2 class="stats-title">设备统计</h2>
      <div class="stats-actions">
        <button
          class="btn btn-secondary btn-sm"
          @click="refreshStatistics"
          :disabled="refreshing"
        >
          <i class="icon-refresh"></i>
          {{ refreshing ? '刷新中...' : '刷新' }}
        </button>
        <button
          class="btn btn-primary btn-sm"
          @click="scanDevices"
          :disabled="scanning"
        >
          <i class="icon-scan"></i>
          {{ scanning ? '扫描中...' : '扫描设备' }}
        </button>
      </div>
    </div>

    <div class="stats-overview">
      <div class="stat-card">
        <div class="stat-icon total">
          <i class="icon-devices"></i>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.total_devices || 0 }}</div>
          <div class="stat-label">总设备数</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon connected">
          <i class="icon-connected"></i>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.connected_devices || 0 }}</div>
          <div class="stat-label">已连接</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon disconnected">
          <i class="icon-disconnected"></i>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.disconnected_devices || 0 }}</div>
          <div class="stat-label">未连接</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon error">
          <i class="icon-error"></i>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.error_devices || 0 }}</div>
          <div class="stat-label">异常设备</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon health">
          <i class="icon-health"></i>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ statistics.health_score || 0 }}%</div>
          <div class="stat-label">健康评分</div>
        </div>
      </div>
    </div>

    <div class="stats-section">
      <h3 class="section-title">设备类型分布</h3>
      <div class="type-distribution">
        <div
          v-for="(count, type) in statistics.by_type"
          :key="type"
          class="type-item"
          :class="`type-${type}`"
        >
          <div class="type-info">
            <div class="type-name">{{ getDeviceTypeText(type) }}</div>
            <div class="type-count">{{ count }} 台</div>
          </div>
          <div class="type-bar">
            <div
              class="type-fill"
              :style="{ width: getTypePercentage(type) }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <div class="stats-section">
      <h3 class="section-title">连接统计</h3>
      <div class="connection-stats">
        <div class="connection-item">
          <div class="connection-label">总连接次数</div>
          <div class="connection-value">{{ statistics.total_connections || 0 }}</div>
        </div>
        <div class="connection-item">
          <div class="connection-label">成功连接</div>
          <div class="connection-value success">{{ statistics.successful_connections || 0 }}</div>
        </div>
        <div class="connection-item">
          <div class="connection-label">失败连接</div>
          <div class="connection-value error">{{ statistics.failed_connections || 0 }}</div>
        </div>
        <div class="connection-item">
          <div class="connection-label">平均连接时间</div>
          <div class="connection-value">{{ formatDuration(statistics.average_connection_time) }}</div>
        </div>
      </div>
    </div>

    <div class="stats-section">
      <h3 class="section-title">设备状态分布</h3>
      <div class="status-chart">
        <div
          v-for="(count, status) in statistics.by_status"
          :key="status"
          class="status-item"
          :class="`status-${status}`"
        >
          <div class="status-info">
            <div class="status-name">{{ getStatusText(status) }}</div>
            <div class="status-count">{{ count }} 台</div>
          </div>
          <div class="status-bar">
            <div
              class="status-fill"
              :style="{ width: getStatusPercentage(status) }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <div class="stats-section" v-if="statistics.total_errors > 0">
      <h3 class="section-title">错误统计</h3>
      <div class="error-stats">
        <div class="error-item">
          <div class="error-label">总错误数</div>
          <div class="error-value">{{ statistics.total_errors }}</div>
        </div>
        <div class="error-item">
          <div class="error-label">错误率</div>
          <div class="error-value">{{ getErrorRate() }}%</div>
        </div>
      </div>
    </div>

    <div class="stats-section">
      <h3 class="section-title">系统信息</h3>
      <div class="system-info">
        <div class="info-item">
          <label class="info-label">最后更新</label>
          <div class="info-value">{{ formatDate(statistics.last_updated) }}</div>
        </div>
        <div class="info-item">
          <label class="info-label">扫描状态</label>
          <div class="info-value">
            <span class="status-badge" :class="scanStatusClass">
              {{ scanStatusText }}
            </span>
          </div>
        </div>
        <div class="info-item">
          <label class="info-label">WebSocket连接</label>
          <div class="info-value">
            <span class="status-badge" :class="wsStatusClass">
              {{ wsStatusText }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="stats-section">
      <h3 class="section-title">快速操作</h3>
      <div class="quick-actions">
        <button
          class="btn btn-primary"
          @click="connectAllDevices"
          :disabled="connectingAll"
        >
          <i class="icon-connect-all"></i>
          {{ connectingAll ? '连接中...' : '连接所有设备' }}
        </button>
        <button
          class="btn btn-warning"
          @click="disconnectAllDevices"
          :disabled="disconnectingAll"
        >
          <i class="icon-disconnect-all"></i>
          {{ disconnectingAll ? '断开中...' : '断开所有设备' }}
        </button>
        <button
          class="btn btn-secondary"
          @click="cleanupDevices"
          :disabled="cleaning"
        >
          <i class="icon-cleanup"></i>
          {{ cleaning ? '清理中...' : '清理旧设备' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { DeviceStatistics, DeviceType, DeviceStatus } from '../types/device'
import { deviceApiService, deviceWebSocketService } from '../api/deviceApi'

const statistics = ref<DeviceStatistics>({
  total_devices: 0,
  connected_devices: 0,
  disconnected_devices: 0,
  error_devices: 0,
  total_connections: 0,
  successful_connections: 0,
  failed_connections: 0,
  average_connection_time: 0,
  total_errors: 0,
  by_type: {} as Record<DeviceType, number>,
  by_status: {} as Record<DeviceStatus, number>,
  health_score: 0,
  last_updated: ''
})

const refreshing = ref(false)
const scanning = ref(false)
const connectingAll = ref(false)
const disconnectingAll = ref(false)
const cleaning = ref(false)
const scanStatus = ref<'idle' | 'scanning' | 'completed'>('idle')
const wsConnected = ref(false)

const scanStatusClass = computed(() => {
  return `status-${scanStatus.value}`
})

const scanStatusText = computed(() => {
  const statusMap = {
    'idle': '空闲',
    'scanning': '扫描中',
    'completed': '已完成'
  }
  return statusMap[scanStatus.value] || '未知'
})

const wsStatusClass = computed(() => {
  return wsConnected.value ? 'status-connected' : 'status-disconnected'
})

const wsStatusText = computed(() => {
  return wsConnected.value ? '已连接' : '未连接'
})

onMounted(() => {
  loadStatistics()
  setupWebSocket()
})

const loadStatistics = async () => {
  refreshing.value = true
  try {
    const stats = await deviceApiService.getStatistics()
    statistics.value = stats
  } catch (error) {
    console.error('加载统计信息失败:', error)
  } finally {
    refreshing.value = false
  }
}

const setupWebSocket = () => {
  deviceWebSocketService.registerHandlers({
    onDeviceConnected: () => {
      loadStatistics()
    },
    onDeviceDisconnected: () => {
      loadStatistics()
    },
    onDeviceStatusUpdated: () => {
      loadStatistics()
    }
  })

  wsConnected.value = deviceWebSocketService.getConnectionStatus()

  setInterval(() => {
    wsConnected.value = deviceWebSocketService.getConnectionStatus()
  }, 5000)
}

const refreshStatistics = () => {
  loadStatistics()
}

const scanDevices = async () => {
  scanning.value = true
  scanStatus.value = 'scanning'
  try {
    await deviceApiService.scanDevices()
    setTimeout(() => {
      loadStatistics()
      scanStatus.value = 'completed'
    }, 2000)
  } catch (error) {
    console.error('扫描设备失败:', error)
    scanStatus.value = 'idle'
  } finally {
    scanning.value = false
  }
}

const getDeviceTypeText = (type: string): string => {
  const types = {
    [DeviceType.ROBOT_ARM]: '机械臂',
    [DeviceType.CONVEYOR]: '传送带',
    [DeviceType.SENSOR]: '传感器',
    [DeviceType.CAMERA]: '摄像头',
    [DeviceType.PLC]: 'PLC控制器',
    [DeviceType.UNKNOWN]: '未知设备'
  }
  return types[type as DeviceType] || '未知设备'
}

const getStatusText = (status: string): string => {
  const statusMap = {
    [DeviceStatus.CONNECTED]: '已连接',
    [DeviceStatus.DISCONNECTED]: '未连接',
    [DeviceStatus.CONNECTING]: '连接中',
    [DeviceStatus.ERROR]: '错误',
    [DeviceStatus.OFFLINE]: '离线'
  }
  return statusMap[status as DeviceStatus] || '未知状态'
}

const getTypePercentage = (type: string): string => {
  const total = statistics.value.total_devices
  if (total === 0) return '0%'
  const count = statistics.value.by_type[type as DeviceType] || 0
  return `${(count / total * 100).toFixed(1)}%`
}

const getStatusPercentage = (status: string): string => {
  const total = statistics.value.total_devices
  if (total === 0) return '0%'
  const count = statistics.value.by_status[status as DeviceStatus] || 0
  return `${(count / total * 100).toFixed(1)}%`
}

const getErrorRate = (): string => {
  const total = statistics.value.total_connections
  if (total === 0) return '0.0'
  const errors = statistics.value.failed_connections || 0
  return ((errors / total) * 100).toFixed(1)
}

const formatDuration = (seconds: number): string => {
  if (!seconds) return '0秒'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}时${minutes}分`
}

const formatDate = (dateString: string): string => {
  if (!dateString) return '未知'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const connectAllDevices = async () => {
  connectingAll.value = true
  try {
    console.log('连接所有设备')
    await new Promise(resolve => setTimeout(resolve, 2000))
    loadStatistics()
  } catch (error) {
    console.error('连接所有设备失败:', error)
  } finally {
    connectingAll.value = false
  }
}

const disconnectAllDevices = async () => {
  disconnectingAll.value = true
  try {
    console.log('断开所有设备')
    await new Promise(resolve => setTimeout(resolve, 2000))
    loadStatistics()
  } catch (error) {
    console.error('断开所有设备失败:', error)
  } finally {
    disconnectingAll.value = false
  }
}

const cleanupDevices = async () => {
  if (!confirm('确定要清理30天未使用的设备吗？')) {
    return
  }

  cleaning.value = true
  try {
    const result = await deviceApiService.cleanupDevices(30)
    alert(`清理了 ${result.cleaned_count} 个旧设备`)
    loadStatistics()
  } catch (error) {
    console.error('清理设备失败:', error)
    alert('清理设备失败，请重试')
  } finally {
    cleaning.value = false
  }
}
</script>

<style scoped>
.device-statistics {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.stats-title {
  font-size: 20px;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
}

.stats-actions {
  display: flex;
  gap: 8px;
}

.btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-primary {
  background: #4299e1;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #3182ce;
}

.btn-secondary {
  background: #e2e8f0;
  color: #4a5568;
}

.btn-secondary:hover:not(:disabled) {
  background: #cbd5e0;
}

.btn-warning {
  background: #ed8936;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #dd7711;
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f7fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-icon.total {
  background: #4299e1;
  color: white;
}

.stat-icon.connected {
  background: #48bb78;
  color: white;
}

.stat-icon.disconnected {
  background: #a0aec0;
  color: white;
}

.stat-icon.error {
  background: #f56565;
  color: white;
}

.stat-icon.health {
  background: #ed8936;
  color: white;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #2d3748;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #718096;
  font-weight: 500;
}

.stats-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.type-distribution,
.status-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.type-item,
.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f7fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.type-info,
.status-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.type-name,
.status-name {
  font-size: 14px;
  color: #2d3748;
  font-weight: 500;
}

.type-count,
.status-count {
  font-size: 14px;
  color: #718096;
  font-weight: 400;
}

.type-bar,
.status-bar {
  width: 100px;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.type-fill,
.status-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.type-fill {
  background: #4299e1;
}

.status-fill.status-connected {
  background: #48bb78;
}

.status-fill.status-disconnected {
  background: #a0aec0;
}

.status-fill.status-connecting {
  background: #ed8936;
}

.status-fill.status-error {
  background: #f56565;
}

.status-fill.status-offline {
  background: #718096;
}

.connection-stats,
.error-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.connection-item,
.error-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  background: #f7fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.connection-label,
.error-label {
  font-size: 14px;
  color: #718096;
  font-weight: 500;
  margin-bottom: 8px;
  text-align: center;
}

.connection-value,
.error-value {
  font-size: 24px;
  font-weight: 700;
  color: #2d3748;
}

.connection-value.success {
  color: #48bb78;
}

.connection-value.error {
  color: #f56565;
}

.system-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f7fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.info-label {
  font-size: 14px;
  color: #718096;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  color: #2d3748;
  font-weight: 400;
}

.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.status-idle {
  background: #e2e8f0;
  color: #4a5568;
}

.status-badge.status-scanning {
  background: #feebc8;
  color: #c05621;
}

.status-badge.status-completed {
  background: #c6f6d5;
  color: #276749;
}

.status-badge.status-connected {
  background: #c6f6d5;
  color: #276749;
}

.status-badge.status-disconnected {
  background: #fed7d7;
  color: #c53030;
}

.quick-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.icon-refresh::before { content: "🔄"; }
.icon-scan::before { content: "🔍"; }
.icon-devices::before { content: "📱"; }
.icon-connected::before { content: "🔗"; }
.icon-disconnected::before { content: "🔌"; }
.icon-error::before { content: "⚠️"; }
.icon-health::before { content: "❤️"; }
.icon-connect-all::before { content: "🔗"; }
.icon-disconnect-all::before { content: "🔌"; }
.icon-cleanup::before { content: "🧹"; }
</style>