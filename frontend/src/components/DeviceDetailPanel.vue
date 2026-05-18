<template>
  <div class="device-detail-panel" v-if="device">
    <div class="panel-header">
      <h2 class="panel-title">设备详情</h2>
      <el-button class="btn-close" @click="closePanel" type="text">
        <el-icon><Close /></el-icon>
      </el-button>
    </div>

    <div class="panel-content">
      <div class="section">
        <h3 class="section-title">基本信息</h3>
        <div class="info-grid">
          <div class="info-item">
            <label class="info-label">设备名称</label>
            <div class="info-value">{{ device.name }}</div>
          </div>
          <div class="info-item">
            <label class="info-label">设备类型</label>
            <div class="info-value">{{ getDeviceTypeText(device.device_type) }}</div>
          </div>
          <div class="info-item">
            <label class="info-label">设备ID</label>
            <div class="info-value code">{{ device.device_id }}</div>
          </div>
          <div class="info-item">
            <label class="info-label">连接方式</label>
            <div class="info-value">{{ getConnectionTypeText(device.connection_type) }}</div>
          </div>
          <div class="info-item">
            <label class="info-label">制造商</label>
            <div class="info-value">{{ device.manufacturer || '未知' }}</div>
          </div>
          <div class="info-item">
            <label class="info-label">型号</label>
            <div class="info-value">{{ device.model || '未知' }}</div>
          </div>
          <div class="info-item">
            <label class="info-label">序列号</label>
            <div class="info-value code">{{ device.serial_number || '未知' }}</div>
          </div>
          <div class="info-item">
            <label class="info-label">固件版本</label>
            <div class="info-value">{{ device.firmware_version || '未知' }}</div>
          </div>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">设备状态</h3>
        <div class="status-grid">
          <div class="status-item">
            <label class="status-label">连接状态</label>
            <div class="status-value">
              <span class="status-badge" :class="`status-${device.status}`">
                {{ getStatusText(device.status) }}
              </span>
            </div>
          </div>
          <div class="status-item">
            <label class="status-label">配对状态</label>
            <div class="status-value">
              <span class="status-badge" :class="`pairing-${device.pairing_status}`">
                {{ getPairingStatusText(device.pairing_status) }}
              </span>
            </div>
          </div>
          <div class="status-item">
            <label class="status-label">健康评分</label>
            <div class="status-value">
              <div class="health-score">
                <div class="score-circle" :class="getHealthClass(device.health_score)">
                  {{ device.health_score || 0 }}%
                </div>
              </div>
            </div>
          </div>
          <div class="status-item">
            <label class="status-label">最后活动</label>
            <div class="status-value">{{ formatDate(device.last_seen) }}</div>
          </div>
          <div class="status-item">
            <label class="status-label">创建时间</label>
            <div class="status-value">{{ formatDate(device.created_at) }}</div>
          </div>
          <div class="status-item">
            <label class="status-label">更新时间</label>
            <div class="status-value">{{ formatDate(device.updated_at) }}</div>
          </div>
        </div>
      </div>

      <div class="section" v-if="device.capabilities && device.capabilities.length">
        <h3 class="section-title">设备能力</h3>
        <div class="capabilities">
          <span
            v-for="capability in device.capabilities"
            :key="capability"
            class="capability-tag"
          >
            {{ capability }}
          </span>
        </div>
      </div>

      <div class="section" v-if="device.connection_params && Object.keys(device.connection_params).length">
        <h3 class="section-title">连接参数</h3>
        <div class="params-grid">
          <div
            v-for="(value, key) in device.connection_params"
            :key="key"
            class="param-item"
          >
            <label class="param-label">{{ key }}</label>
            <div class="param-value code">{{ value }}</div>
          </div>
        </div>
      </div>

      <div class="section" v-if="device.description">
        <h3 class="section-title">设备描述</h3>
        <div class="description">
          {{ device.description }}
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">设备操作</h3>
        <div class="action-buttons">
          <button
            v-if="device.status === 'disconnected' || device.status === 'offline'"
            class="btn btn-primary"
            @click="connectDevice"
            :disabled="connecting"
          >
            <i class="icon-connect"></i>
            {{ connecting ? '连接中...' : '连接设备' }}
          </button>
          <button
            v-else-if="device.status === 'connected'"
            class="btn btn-warning"
            @click="disconnectDevice"
            :disabled="disconnecting"
          >
            <i class="icon-disconnect"></i>
            {{ disconnecting ? '断开中...' : '断开连接' }}
          </button>
          <button
            class="btn btn-secondary"
            @click="refreshDevice"
            :disabled="refreshing"
          >
            <i class="icon-refresh"></i>
            {{ refreshing ? '刷新中...' : '刷新状态' }}
          </button>
          <button
            class="btn btn-danger"
            @click="deleteDevice"
            :disabled="deleting"
          >
            <i class="icon-delete"></i>
            {{ deleting ? '删除中...' : '删除设备' }}
          </button>
        </div>
      </div>

      <div class="section">
        <h3 class="section-title">连接历史</h3>
        <div class="history-list" v-if="connectionHistory.length">
          <div
            v-for="record in connectionHistory"
            :key="record.id"
            class="history-item"
            :class="`event-${record.event_type}`"
          >
            <div class="history-icon">
              <i :class="getHistoryIcon(record.event_type)"></i>
            </div>
            <div class="history-content">
              <div class="history-event">{{ getEventText(record.event_type) }}</div>
              <div class="history-time">{{ formatDate(record.timestamp) }}</div>
              <div class="history-details" v-if="record.details || record.error_message">
                {{ record.details ? JSON.stringify(record.details) : record.error_message }}
              </div>
            </div>
          </div>
        </div>
        <div class="empty-state" v-else>
          暂无连接历史记录
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { DeviceInfo, ConnectionHistory, DeviceType, DeviceStatus, ConnectionType, PairingStatus } from '../types/device'
import { deviceApiService } from '../api/deviceApi'
import { Close } from '@element-plus/icons-vue'

interface Props {
  device: DeviceInfo | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'connect', device: DeviceInfo): void
  (e: 'disconnect', device: DeviceInfo): void
  (e: 'delete', device: DeviceInfo): void
  (e: 'refresh', device: DeviceInfo): void
}>()

const connecting = ref(false)
const disconnecting = ref(false)
const deleting = ref(false)
const refreshing = ref(false)
const connectionHistory = ref<ConnectionHistory[]>([])

const device = computed(() => props.device)

watch(device, (newDevice) => {
  if (newDevice) {
    loadConnectionHistory(newDevice.device_id)
  }
})

onMounted(() => {
  if (device.value) {
    loadConnectionHistory(device.value.device_id)
  }
})

const closePanel = () => {
  emit('close')
}

const getDeviceTypeText = (type: DeviceType): string => {
  const types = {
    [DeviceType.ROBOT_ARM]: '机械臂',
    [DeviceType.CONVEYOR_BELT]: '传送带',
    [DeviceType.VISION_SYSTEM]: '视觉系统',
    [DeviceType.TEMPERATURE_SENSOR]: '温度传感器',
    [DeviceType.PLC]: 'PLC控制器',
    [DeviceType.UNKNOWN]: '未知设备'
  }
  return types[type] || '未知设备'
}

const getConnectionTypeText = (type: ConnectionType): string => {
  const types = {
    [ConnectionType.SERIAL]: '串口',
    [ConnectionType.ETHERNET]: '以太网',
    [ConnectionType.USB]: 'USB',
    [ConnectionType.BLUETOOTH]: '蓝牙',
    [ConnectionType.WIFI]: 'WiFi'
  }
  return types[type] || '未知'
}

const getStatusText = (status: DeviceStatus): string => {
  const statusMap = {
    [DeviceStatus.CONNECTED]: '已连接',
    [DeviceStatus.DISCONNECTED]: '未连接',
    [DeviceStatus.CONNECTING]: '连接中',
    [DeviceStatus.ERROR]: '错误',
    [DeviceStatus.OFFLINE]: '离线'
  }
  return statusMap[status] || '未知状态'
}

const getHealthClass = (score: number | undefined): string => {
  const healthScore = score || 0
  if (healthScore >= 80) return 'health-good'
  if (healthScore >= 60) return 'health-warning'
  return 'health-critical'
}

const getPairingStatusText = (status: PairingStatus): string => {
  const statusMap = {
    [PairingStatus.UNPAIRED]: '未配对',
    [PairingStatus.PAIRED]: '已配对',
    [PairingStatus.PAIRING]: '配对中'
  }
  return statusMap[status] || '未知状态'
}

const formatDate = (dateString: string): string => {
  if (!dateString) return '未知'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const getHistoryIcon = (eventType: string): string => {
  const icons = {
    'connect': 'icon-connect',
    'disconnect': 'icon-disconnect',
    'error': 'icon-error',
    'scan': 'icon-scan'
  }
  return icons[eventType] || 'icon-unknown'
}

const getEventText = (eventType: string): string => {
  const events = {
    'connect': '设备连接',
    'disconnect': '设备断开',
    'error': '设备错误',
    'scan': '设备扫描'
  }
  return events[eventType] || '未知事件'
}

const loadConnectionHistory = async (deviceId: string) => {
  try {
    const history = await deviceApiService.getDeviceHistory(deviceId, 10)
    connectionHistory.value = history
  } catch (error) {
    console.error('加载连接历史失败:', error)
    connectionHistory.value = []
  }
}

const connectDevice = async () => {
  if (!device.value) return

  connecting.value = true
  try {
    await deviceApiService.connectDevice(device.value.device_id)
    emit('connect', device.value)
  } catch (error) {
    console.error('连接设备失败:', error)
  } finally {
    connecting.value = false
  }
}

const disconnectDevice = async () => {
  if (!device.value) return

  disconnecting.value = true
  try {
    await deviceApiService.disconnectDevice(device.value.device_id)
    emit('disconnect', device.value)
  } catch (error) {
    console.error('断开设备连接失败:', error)
  } finally {
    disconnecting.value = false
  }
}

const refreshDevice = async () => {
  if (!device.value) return

  refreshing.value = true
  try {
    await deviceApiService.getDeviceDetails(device.value.device_id)
    emit('refresh', device.value)
  } catch (error) {
    console.error('刷新设备状态失败:', error)
  } finally {
    refreshing.value = false
  }
}

const deleteDevice = async () => {
  if (!device.value) return

  if (!confirm(`确定要删除设备 "${device.value.name}" 吗？此操作不可撤销。`)) {
    return
  }

  deleting.value = true
  try {
    await deviceApiService.deleteDevice(device.value.device_id)
    emit('delete', device.value)
  } catch (error) {
    console.error('删除设备失败:', error)
    alert('删除设备失败，请重试')
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.device-detail-panel {
  background: white;
  border-left: 1px solid #e2e8f0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f7fafc;
}

.panel-title {
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
}

.btn-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #718096;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.btn-close:hover {
  background: #e2e8f0;
  color: #4a5568;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.section {
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

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: #718096;
  font-weight: 500;
  text-transform: uppercase;
}

.info-value {
  font-size: 14px;
  color: #2d3748;
  font-weight: 400;
}

.info-value.code {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  background: #f7fafc;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-label {
  font-size: 12px;
  color: #718096;
  font-weight: 500;
  text-transform: uppercase;
}

.status-value {
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

.status-badge.status-connected {
  background: #c6f6d5;
  color: #276749;
}

.status-badge.status-disconnected {
  background: #edf2f7;
  color: #4a5568;
}

.status-badge.status-connecting {
  background: #fed7d7;
  color: #c53030;
}

.status-badge.status-error {
  background: #fed7d7;
  color: #c53030;
}

.status-badge.status-offline {
  background: #feebc8;
  color: #c05621;
}

.status-badge.status-online {
  background: #c6f6d5;
  color: #276749;
}

.health-score {
  display: flex;
  align-items: center;
}

.score-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.score-circle.health-good {
  background: #48bb78;
}

.score-circle.health-warning {
  background: #ed8936;
}

.score-circle.health-critical {
  background: #f56565;
}

.capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.capability-tag {
  background: #4299e1;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.param-label {
  font-size: 12px;
  color: #718096;
  font-weight: 500;
  text-transform: uppercase;
}

.param-value {
  font-size: 14px;
  color: #2d3748;
  font-weight: 400;
  background: #f7fafc;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.description {
  font-size: 14px;
  color: #4a5568;
  line-height: 1.5;
  background: #f7fafc;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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

.btn-danger {
  background: #f56565;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #e53e3e;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.history-item:hover {
  background: #f7fafc;
}

.history-item.event-connect {
  border-left: 4px solid #48bb78;
}

.history-item.event-disconnect {
  border-left: 4px solid #a0aec0;
}

.history-item.event-error {
  border-left: 4px solid #f56565;
}

.history-item.event-scan {
  border-left: 4px solid #4299e1;
}

.history-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  background: #e2e8f0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.history-content {
  flex: 1;
  min-width: 0;
}

.history-event {
  font-size: 14px;
  font-weight: 500;
  color: #2d3748;
  margin-bottom: 2px;
}

.history-time {
  font-size: 12px;
  color: #718096;
  margin-bottom: 4px;
}

.history-details {
  font-size: 12px;
  color: #4a5568;
  background: #f7fafc;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  word-break: break-all;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #718096;
  font-size: 14px;
  background: #f7fafc;
  border-radius: 6px;
  border: 1px dashed #cbd5e0;
}

.icon-close::before { content: "✕"; }
.icon-connect::before { content: "🔗"; }
.icon-disconnect::before { content: "🔌"; }
.icon-refresh::before { content: "🔄"; }
.icon-delete::before { content: "🗑️"; }
.icon-error::before { content: "⚠️"; }
.icon-scan::before { content: "🔍"; }
.icon-unknown::before { content: "❓"; }
</style>