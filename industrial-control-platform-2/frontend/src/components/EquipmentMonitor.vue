<template>
  <div class="equipment-monitor" :class="{ 'fullscreen-mode': isExpanded }">
    <div class="fullscreen-header" v-if="isExpanded">
      <div class="header-left">
        <h2>设备监控中心</h2>
        <el-tag type="success">已连接设备: {{ connectedDevices.length }}</el-tag>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="startScanning" :loading="scanning">
          <el-icon><Search /></el-icon>
          扫描设备
        </el-button>
        <el-button @click="refreshDevices">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-switch
          v-model="autoScan"
          active-text="自动扫描"
          @change="toggleAutoScan"
        />
        <el-button type="success" @click="showPortAssignmentHistory">
          <el-icon><Setting /></el-icon>
          端口分配历史
        </el-button>
        <el-button type="warning" @click="toggleExpand">
          <el-icon><Close /></el-icon>
          退出全屏
        </el-button>
      </div>
    </div>

    <div class="global-monitor-entry" v-if="!isExpanded && devices.length === 0" @click="toggleExpand">
      <div class="entry-header">
        <div class="entry-icon">
          <el-icon :size="32" color="#909399">
            <Cpu />
          </el-icon>
        </div>
        <div class="entry-info">
          <h3>设备监控中心</h3>
          <div class="entry-stats">
            <span class="stat-item">暂无设备</span>
          </div>
        </div>
        <div class="entry-arrow">
          <el-icon :size="24"><ArrowRight /></el-icon>
        </div>
      </div>
      <div class="entry-preview">
        <div class="system-status">
          <el-tag size="small" type="info">
            点击展开添加设备
          </el-tag>
        </div>
      </div>
    </div>

    <div class="global-monitor-entry" v-if="!isExpanded && devices.length > 0" @click="toggleExpand">
      <div class="entry-header">
        <div class="entry-icon">
          <el-icon :size="32" :color="getStatusColor('connected')">
            <Cpu />
          </el-icon>
          <div class="status-dot connected"></div>
        </div>
        <div class="entry-info">
          <h3>设备监控中心</h3>
          <div class="entry-stats">
            <span class="stat-item">
              <el-icon><SuccessFilled /></el-icon>
              已连接: {{ connectedDevices.length }}
            </span>
            <span class="stat-item">
              <el-icon><Cpu /></el-icon>
              总计: {{ devices.length }}
            </span>
          </div>
        </div>
        <div class="entry-arrow">
          <el-icon :size="24"><ArrowRight /></el-icon>
        </div>
      </div>

      <div class="entry-preview">
        <div class="device-icons-preview">
          <div
            v-for="(device, index) in connectedDevices.slice(0, 4)"
            :key="device.device_id"
            class="preview-icon"
            :style="{
              left: `${index * 8}px`,
              zIndex: 4 - index
            }"
          >
            <el-icon :size="16" :color="getStatusColor(device.status)">
              <Cpu />
            </el-icon>
          </div>
          <div v-if="connectedDevices.length > 4" class="more-count">
            +{{ connectedDevices.length - 4 }}
          </div>
        </div>
        <div class="system-status">
          <el-tag
            size="small"
            :type="connectedDevices.length > 0 ? 'success' : 'info'"
          >
            {{ connectedDevices.length > 0 ? '系统运行中' : '无设备连接' }}
          </el-tag>
        </div>
      </div>
    </div>

    <div class="fullscreen-content" v-if="isExpanded">
      <div class="content-layout">
        <div class="left-panel">
          <div class="device-discovery-panel">
            <div class="panel-header">
              <h3>设备发现与配对</h3>
            </div>

            <div v-if="scanning" class="scanning-progress">
              <div class="scanning-animation">
                <div class="radar"></div>
                <div class="radar-pulse"></div>
              </div>
              <p>正在扫描设备...</p>
              <el-progress :percentage="scanProgress" :show-text="false" />
            </div>

            <div v-if="currentMode === 'discovery'" class="device-management">
              <div class="device-groups">
                <div class="device-group connected-devices">
                  <div class="group-header">
                    <h4>
                      <el-icon><SuccessFilled /></el-icon>
                      已连接设备 ({{ connectedDevices.length }})
                    </h4>
                    <el-tag type="success" size="small">运行中</el-tag>
                  </div>
                  <div class="group-content">
                    <div v-for="device in connectedDevices" :key="device.device_id" class="device-card-item">
                      <div class="device-card connected" :class="getDeviceCardClass(device)">
                        <div class="device-main-info">
                          <div class="device-icon-status">
                            <el-icon :size="20" :color="getStatusColor(device.status)">
                              <Cpu />
                            </el-icon>
                            <div class="status-dot" :class="device.status"></div>
                          </div>
                          <div class="device-details">
                            <h5>{{ device.name }}</h5>
                            <p class="device-connection">{{ device.connection_info }}</p>
                            <div class="device-meta">
                              <span class="connection-time">连接时长: {{ formatConnectionTime(device) }}</span>
                              <span class="health-score">健康度: {{ device.health_score || 85 }}%</span>
                            </div>
                          </div>
                        </div>
                        <div class="device-metrics">
                          <div class="metric">
                            <span class="metric-label">温度</span>
                            <el-progress
                              :percentage="getDeviceTemperature(device)"
                              :color="getTemperatureColor(getDeviceTemperature(device))"
                              :show-text="false"
                            />
                            <span class="metric-value">{{ getDeviceTemperature(device) }}°C</span>
                          </div>
                          <div class="metric">
                            <span class="metric-label">负载</span>
                            <el-progress
                              :percentage="getDeviceLoad(device)"
                              status="success"
                              :show-text="false"
                            />
                            <span class="metric-value">{{ getDeviceLoad(device) }}%</span>
                          </div>
                        </div>
                        <div class="device-actions">
                          <el-button
                            type="warning"
                            size="small"
                            @click="disconnectDevice(device)"
                          >
                            <el-icon><SwitchButton /></el-icon>
                            断开
                          </el-button>
                          <el-button
                            type="info"
                            size="small"
                            @click="resetDevice(device)"
                          >
                            <el-icon><Refresh /></el-icon>
                            重置
                          </el-button>
                          <el-button
                            type="primary"
                            size="small"
                            @click="showDeviceDetails(device)"
                          >
                            <el-icon><MoreFilled /></el-icon>
                            详情
                          </el-button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="device-group historical-devices">
                  <div class="group-header">
                    <h4>
                      <el-icon><Clock /></el-icon>
                      历史设备 ({{ historicalDevices.length }})
                    </h4>
                    <el-tag type="info" size="small">未连接</el-tag>
                  </div>
                  <div class="group-content">
                    <div v-for="device in historicalDevices" :key="device.device_id" class="device-card-item">
                      <div class="device-card disconnected" :class="getDeviceCardClass(device)">
                        <div class="device-main-info">
                          <div class="device-icon-status">
                            <el-icon :size="20" :color="getStatusColor(device.status)">
                              <Cpu />
                            </el-icon>
                            <div class="status-dot" :class="device.status"></div>
                          </div>
                          <div class="device-details">
                            <h5>{{ device.name }}</h5>
                            <p class="device-connection">{{ device.connection_info }}</p>
                            <div class="device-meta">
                              <span class="last-connected">上次连接: {{ formatLastConnected(device) }}</span>
                              <span class="pairing-status">已配对</span>
                            </div>
                          </div>
                        </div>
                        <div class="device-metrics">
                          <div class="metric disabled">
                            <span class="metric-label">温度</span>
                            <el-progress
                              :percentage="0"
                              :show-text="false"
                            />
                            <span class="metric-value">--°C</span>
                          </div>
                          <div class="metric disabled">
                            <span class="metric-label">负载</span>
                            <el-progress
                              :percentage="0"
                              :show-text="false"
                            />
                            <span class="metric-value">--%</span>
                          </div>
                        </div>
                        <div class="device-actions">
                          <el-button
                            type="success"
                            size="small"
                            @click="connectDevice(device)"
                          >
                            <el-icon><Connection /></el-icon>
                            连接
                          </el-button>
                          <el-button
                            type="info"
                            size="small"
                            @click="showPortAssignment(device)"
                          >
                            <el-icon><Setting /></el-icon>
                            配置
                          </el-button>
                          <el-button
                            type="danger"
                            size="small"
                            @click="unpairDevice(device)"
                          >
                            <el-icon><Delete /></el-icon>
                            移除
                          </el-button>
                        </div>
                      </div>
                    </div>
                    <div v-if="historicalDevices.length === 0" class="empty-group">
                      <el-empty description="暂无历史设备" :image-size="60" />
                    </div>
                  </div>
                </div>

                <div class="device-group new-devices">
                  <div class="group-header">
                    <h4>
                      <el-icon><Search /></el-icon>
                      新发现设备 ({{ newDevices.length }})
                    </h4>
                    <el-button type="primary" size="small" @click="startScanning" :loading="scanning">
                      <el-icon><Refresh /></el-icon>
                      扫描
                    </el-button>
                  </div>
                  <div class="group-content">
                    <div v-if="scanning" class="scanning-progress-inline">
                      <div class="scanning-animation-small">
                        <div class="radar-small"></div>
                        <div class="radar-pulse-small"></div>
                      </div>
                      <span>扫描中...</span>
                      <el-progress :percentage="scanProgress" :show-text="false" />
                    </div>
                    <div v-for="device in newDevices" :key="device.device_id" class="device-card-item">
                      <div class="device-card new" :class="getDeviceCardClass(device)">
                        <div class="device-main-info">
                          <div class="device-icon-status">
                            <el-icon :size="20" :color="getStatusColor(device.status)">
                              <Cpu />
                            </el-icon>
                            <div class="status-dot" :class="device.status"></div>
                          </div>
                          <div class="device-details">
                            <h5>{{ device.name || '未知设备' }}</h5>
                            <p class="device-connection">{{ device.connection_info }}</p>
                            <div class="device-meta">
                              <span class="signal-strength">信号: {{ getSignalStrength(device) }}</span>
                              <span class="discovery-time">发现时间: {{ formatDiscoveryTime(device) }}</span>
                            </div>
                          </div>
                        </div>
                        <div class="device-actions">
                          <el-button
                            type="primary"
                            size="small"
                            @click="startPairing(device)"
                          >
                            <el-icon><Plus /></el-icon>
                            配对
                          </el-button>
                          <el-button
                            type="info"
                            size="small"
                            @click="showDeviceDetails(device)"
                          >
                            <el-icon><InfoFilled /></el-icon>
                            详情
                          </el-button>
                        </div>
                      </div>
                    </div>
                    <div v-if="newDevices.length === 0 && !scanning" class="empty-group">
                      <el-empty description="暂无新设备" :image-size="60" />
                      <p class="scan-hint">点击扫描按钮发现新设备</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="currentMode === 'pairing'" class="pairing-mode">
              <div class="pairing-header">
                <h4>设备配对</h4>
                <el-button @click="cancelPairing">取消</el-button>
              </div>

              <div class="pairing-content">
                <div class="device-to-pair">
                  <div class="device-preview">
                    <el-icon :size="48"><Cpu /></el-icon>
                    <h5>{{ pairingDevice?.name }}</h5>
                    <p>{{ pairingDevice?.connection_info }}</p>
                  </div>

                  <div class="pairing-options">
                    <h5>选择设备类型</h5>
                    <div class="device-type-selection">
                      <div
                        v-for="type in availableDeviceTypes"
                        :key="type.value"
                        class="type-option"
                        :class="{ selected: selectedDeviceType === type.value }"
                        @click="selectDeviceType(type.value)">
                        <el-icon :size="24"><component :is="type.icon" /></el-icon>
                        <span>{{ type.label }}</span>
                      </div>
                    </div>

                    <div class="pairing-settings">
                      <el-input
                        v-model="customDeviceName"
                        placeholder="自定义设备名称"
                        clearable
                      />
                      <el-checkbox v-model="autoConnect">自动连接</el-checkbox>
                      <el-checkbox v-model="saveToLocal">保存到本地记录</el-checkbox>
                    </div>

                    <el-button
                      type="primary"
                      :disabled="!selectedDeviceType"
                      @click="confirmPairing">
                      确认配对
                    </el-button>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="currentMode === 'connecting'" class="connecting-mode">
              <div class="connection-progress">
                <el-progress
                  type="circle"
                  :percentage="connectionProgress"
                  :status="connectionStatus"
                  :width="100"
                />
                <div class="connection-info">
                  <h4>正在连接设备</h4>
                  <p>{{ connectingDevice?.name }}</p>
                  <p class="connection-message">{{ connectionMessage }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="right-panel">
          <div class="status-panel">
            <h3>设备状态监控</h3>
            <div class="status-grid">
              <div
                v-for="device in connectedDevices"
                :key="device.device_id"
                class="device-status-card"
              >
                <div class="status-card-header">
                  <div class="device-title">
                    <el-icon :size="20" :color="getStatusColor(device.status)">
                      <Cpu />
                    </el-icon>
                    <span class="device-name">{{ device.name }}</span>
                  </div>
                  <el-tag size="small" :type="getStatusTagType(device.status)">
                    {{ getStatusText(device.status) }}
                  </el-tag>
                </div>

                <div class="status-metrics">
                  <div class="metric-item">
                    <span class="metric-label">温度</span>
                    <div class="metric-value">
                      <el-progress
                        :percentage="getDeviceTemperature(device)"
                        :color="getTemperatureColor(getDeviceTemperature(device))"
                        :show-text="false"
                      />
                      <span class="metric-text">{{ getDeviceTemperature(device) }}°C</span>
                    </div>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">负载</span>
                    <div class="metric-value">
                      <el-progress
                        :percentage="getDeviceLoad(device)"
                        status="success"
                        :show-text="false"
                      />
                      <span class="metric-text">{{ getDeviceLoad(device) }}%</span>
                    </div>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">连接时间</span>
                    <span class="metric-text">{{ formatConnectionTime(device) }}</span>
                  </div>
                  <div class="metric-item">
                    <span class="metric-label">健康评分</span>
                    <span class="metric-text">{{ device.health_score || 85 }}%</span>
                  </div>
                </div>

                <div class="status-actions">
                  <el-button
                    size="small"
                    type="warning"
                    @click="disconnectDevice(device)"
                    :disabled="!canDisconnect(device)"
                  >
                    停止
                  </el-button>
                  <el-button
                    size="small"
                    type="info"
                    @click="resetDevice(device)"
                    :disabled="!canReset(device)"
                  >
                    重置
                  </el-button>
                  <el-button
                    size="small"
                    type="primary"
                    @click="showDeviceDetails(device)"
                  >
                    详情
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>


    <el-dialog v-model="showDeviceDetailDialog" title="设备详情" width="600px" :show-close="false">
      <DeviceDetailPanel
        v-if="selectedDevice"
        :device="selectedDevice"
        @close="showDeviceDetailDialog = false"
        @refresh="refreshDeviceDetails"
      />
    </el-dialog>

    <PortAssignmentDialog
      v-model="showPortAssignmentDialog"
      :device="portAssignmentDevice || undefined"
      @assign="handlePortAssignment"
    />

    <el-dialog v-model="showPortAssignmentHistoryDialog" title="端口分配历史" width="800px">
      <div class="port-assignment-history">
        <div v-if="portAssignmentHistory.length === 0" class="empty-state">
          <el-empty description="暂无端口分配记录" />
        </div>
        <div v-else class="history-list">
          <div v-for="record in portAssignmentHistory" :key="record.deviceId" class="history-item">
            <div class="record-header">
              <h5>{{ record.deviceName || '未知设备' }}</h5>
              <el-tag size="small">{{ record.port }}</el-tag>
            </div>
            <div class="record-details">
              <p>设备ID: {{ record.deviceId }}</p>
              <p>波特率: {{ record.baudRate }}</p>
              <p>数据位: {{ record.dataBits }}</p>
              <p>停止位: {{ record.stopBits }}</p>
              <p>校验位: {{ record.parity }}</p>
              <p class="timestamp">分配时间: {{ formatTimestamp(record.assignedAt) }}</p>
            </div>
            <div class="record-actions">
              <el-button type="primary" size="small" @click="applyPortAssignment(record)">
                应用配置
              </el-button>
              <el-button type="danger" size="small" @click="removePortAssignment(record.deviceId)">
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, markRaw } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Refresh,
  SuccessFilled,
  Cpu,
  Setting,
  Connection,
  Monitor,
  Sunny,
  Close,
  ArrowRight,
  VideoPause,
  Refresh as RefreshIcon,
  Clock,
  Plus,
  InfoFilled,
  SwitchButton,
  MoreFilled,
  Delete,
  More
} from '@element-plus/icons-vue'
import { deviceApiService, deviceWebSocketService } from '../api/deviceApi'
import type { DeviceInfo, DeviceType } from '../types/device'
import { PairingStatus, ConnectionStatus } from '../types/device'
import DeviceDetailPanel from './DeviceDetailPanel.vue'
import PortAssignmentDialog from './PortAssignmentDialog.vue'

const props = defineProps({
  name: {
    type: String,
    default: '设备监控'
  },
  id: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'unknown'
  }
})

const devices = ref<DeviceInfo[]>([])
const scanning = ref(false)
const autoScan = ref(false)
const scanProgress = ref(0)
const currentMode = ref<'discovery' | 'pairing' | 'connecting'>('discovery')
const selectedCategory = ref('all')
const pairingDevice = ref<DeviceInfo | null>(null)
const selectedDeviceType = ref('')
const customDeviceName = ref('')
const autoConnect = ref(true)
const saveToLocal = ref(true)
const connectionProgress = ref(0)
const connectionStatus = ref<'success' | 'exception' | 'warning'>('success')
const connectionMessage = ref('')
const connectingDevice = ref<DeviceInfo | null>(null)
const showDeviceDetailDialog = ref(false)
const selectedDevice = ref<DeviceInfo | null>(null)
const showPortAssignmentDialog = ref(false)
const portAssignmentDevice = ref<DeviceInfo | null>(null)
const showPortAssignmentHistoryDialog = ref(false)
const portAssignmentHistory = ref<any[]>([])
const pairingRecords = ref<any[]>([])
const isExpanded = ref(false)

const deviceCategories = ref([
  { type: 'all', name: '全部设备', icon: markRaw(Cpu), color: '#409EFF' },
  { type: 'robot_arm', name: '机械臂', icon: markRaw(Setting), color: '#67C23A' },
  { type: 'conveyor_belt', name: '传送带', icon: markRaw(Connection), color: '#E6A23C' },
  { type: 'vision_system', name: '视觉系统', icon: markRaw(Monitor), color: '#909399' },
  { type: 'temperature_sensor', name: '传感器', icon: markRaw(Sunny), color: '#F56C6C' },
  { type: 'unknown', name: '未知设备', icon: markRaw(Cpu), color: '#909399' }
])

const availableDeviceTypes = ref([
  { value: 'robot_arm', label: '机械臂', icon: markRaw(Setting) },
  { value: 'conveyor_belt', label: '传送带', icon: markRaw(Connection) },
  { value: 'vision_system', label: '视觉系统', icon: markRaw(Monitor) },
  { value: 'temperature_sensor', label: '温度传感器', icon: markRaw(Sunny) }
])

const filteredDevices = computed(() => {
  if (selectedCategory.value === 'all') {
    return devices.value
  }
  return devices.value.filter(device => device.device_type === selectedCategory.value)
})

const connectedDevices = computed(() => {
  return devices.value.filter(device =>
    device.status === ConnectionStatus.CONNECTED
  )
})

const historicalDevices = computed(() => {
  return devices.value.filter(device =>
    device.pairing_status === PairingStatus.PAIRED &&
    device.status === ConnectionStatus.DISCONNECTED
  )
})

const newDevices = computed(() => {
  return devices.value.filter(device =>
    device.pairing_status === PairingStatus.UNPAIRED ||
    device.pairing_status === PairingStatus.PAIRING
  )
})

const getCategoryDeviceCount = (category: string) => {
  if (category === 'all') return devices.value.length
  return devices.value.filter(device => device.device_type === category).length
}

const handleStop = () => {
  ElMessage.success(`设备 ${props.name} 已停止`)
}

const handleReset = () => {
  ElMessage.success(`设备 ${props.name} 已重置`)
}

const getDeviceTypeDisplayName = (deviceType: string) => {
  const typeMap: Record<string, string> = {
    'robot': '机械臂',
    'conveyor': '传送带',
    'camera': '视觉系统',
    'sensor': '传感器',
    'unknown': '未知设备'
  }
  return typeMap[deviceType] || deviceType
}

const canDisconnect = (device: DeviceInfo) => {
  return device.status === 'connected'
}

const canReset = (device: DeviceInfo) => {
  return device.status !== 'connecting'
}

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'connected': return '#67C23A'
    case 'disconnected': return '#909399'
    case 'error': return '#F56C6C'
    default: return '#E6A23C'
  }
}

const getDeviceTypeName = (deviceType: string) => {
  const typeMap: Record<string, string> = {
    'robot_arm': '机械臂',
    'conveyor_belt': '传送带',
    'vision_system': '视觉系统',
    'temperature_sensor': '温度传感器',
    'unknown': '未知设备'
  }
  return typeMap[deviceType] || deviceType
}

const resetDevice = async (device: DeviceInfo) => {
  try {
    await deviceApiService.disconnectDevice(device.device_id)
    setTimeout(async () => {
      await deviceApiService.connectDevice(device.device_id)
    }, 1000)
    ElMessage.success(`设备 ${device.name} 已重置`)
    loadDevices()
  } catch (error) {
    ElMessage.error(`设备 ${device.name} 重置失败`)
    console.error('设备重置失败:', error)
  }
}

const formatConnectionTime = (device: DeviceInfo) => {
  return '2小时15分钟'
}

const formatLastConnected = (device: DeviceInfo) => {
  return '30分钟前'
}

const getSignalStrength = (device: DeviceInfo) => {
  return '强'
}

const formatDiscoveryTime = (device: DeviceInfo) => {
  return '刚刚'
}

const loadDevices = async (forceReload = false) => {
  try {
    console.log('开始加载设备列表...')
    const devicesList = await deviceApiService.getDevices()
    console.log('从API获取的设备列表:', devicesList)
    devices.value = devicesList

    const connectedDeviceIds = devicesList
      .filter(device => device.status === 'connected')
      .map(device => device.device_id)

    if (connectedDeviceIds.length > 0 && (forceReload || connectedDeviceIds.length !== connectedDevices.value.length)) {
      await loadDevicesRealTimeData(connectedDeviceIds)
    }

    if (import.meta.env.DEV) {
      console.log('当前设备状态:')
      console.log('- 总设备数:', devices.value.length)
      console.log('- 已连接设备:', connectedDevices.value.length)
      console.log('- 历史设备:', historicalDevices.value.length)
      console.log('- 新设备:', newDevices.value.length)

      console.log('模板渲染检查:')
      console.log('- isExpanded:', isExpanded.value)
      console.log('- devices.length:', devices.value.length)
      console.log('- 收起状态显示条件:', !isExpanded.value && devices.value.length > 0)
      console.log('- 全屏模式显示条件:', isExpanded.value)
    }
  } catch (error) {
    ElMessage.error('加载设备列表失败')
    console.error('加载设备列表失败:', error)
  }
}

const loadDevicesRealTimeData = async (deviceIds: string[]) => {
  try {
    const limitedDeviceIds = deviceIds.slice(0, 10)

    const realTimeDataList = await deviceApiService.getDevicesRealTimeData(limitedDeviceIds)

    const updatedDevices = devices.value.map(device => {
      const realTimeData = realTimeDataList.find(data => data.device_id === device.device_id)
      if (realTimeData) {
        return {
          ...device,
          _realtimeData: {
            temperature: realTimeData.temperature,
            load: realTimeData.cpu_usage,
            health_score: (realTimeData as any).health_score || 85,
            signal_strength: realTimeData.signal_strength,
            last_connection_time: realTimeData.last_connection_time
          }
        }
      }
      return device
    })

    devices.value = updatedDevices
  } catch (error) {
    console.error('批量加载设备实时数据失败:', error)
  }
}

const startScanning = async () => {
  scanning.value = true
  scanProgress.value = 0

  const interval = setInterval(() => {
    scanProgress.value += 10
    if (scanProgress.value >= 100) {
      clearInterval(interval)
      setTimeout(() => {
        scanning.value = false
        scanProgress.value = 0
        loadDevices()
      }, 1000)
    }
  }, 200)

  try {
    await deviceApiService.scanDevices()
    ElMessage.success('设备扫描完成')
  } catch (error) {
    ElMessage.error('设备扫描失败')
    scanning.value = false
  }
}

const refreshDevices = () => {
  loadDevices()
  ElMessage.success('设备列表已刷新')
}

const toggleAutoScan = async (enabled: boolean) => {
  autoScan.value = enabled
  if (enabled) {
    await deviceApiService.startAutoScan()
    ElMessage.success('已开启自动扫描')
  } else {
    await deviceApiService.stopAutoScan()
    ElMessage.info('已关闭自动扫描')
  }
}

const selectCategory = (category: string) => {
  selectedCategory.value = category
}

const getDeviceCardClass = (device: DeviceInfo) => {
  return {
    'paired': device.pairing_status === 'paired',
    'connected': device.status === 'connected',
    'disconnected': device.status === 'disconnected',
    'error': device.status === 'error'
  }
}

const getStatusTagType = (status: string) => {
  switch (status) {
    case 'connected': return 'success'
    case 'disconnected': return 'info'
    case 'error': return 'danger'
    default: return 'warning'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'connected': return '已连接'
    case 'disconnected': return '未连接'
    case 'error': return '错误'
    default: return status
  }
}

const startPairing = (device: DeviceInfo) => {
  pairingDevice.value = device
  selectedDeviceType.value = device.device_type !== 'unknown' ? device.device_type : ''
  customDeviceName.value = device.name
  currentMode.value = 'pairing'
}

const cancelPairing = () => {
  pairingDevice.value = null
  selectedDeviceType.value = ''
  customDeviceName.value = ''
  currentMode.value = 'discovery'
}

const selectDeviceType = (type: string) => {
  selectedDeviceType.value = type
}

const confirmPairing = async () => {
  if (!pairingDevice.value || !selectedDeviceType.value) {
    ElMessage.warning('请选择设备类型')
    return
  }

  try {
    console.log('开始设备配对流程...')
    console.log('设备信息:', pairingDevice.value)
    console.log('选择的设备类型:', selectedDeviceType.value)

    const pairingResult = await deviceApiService.createPairingRequest(pairingDevice.value.device_id)
    console.log('配对请求创建结果:', pairingResult)

    if (!pairingResult || !pairingResult.pairing_id) {
      ElMessage.error('创建设备配对请求失败')
      return
    }

    await deviceApiService.confirmPairing(
      pairingResult.pairing_id,
      selectedDeviceType.value,
      customDeviceName.value || pairingDevice.value.name,
      autoConnect.value
    )

    ElMessage.success('设备配对成功')

    if (saveToLocal.value) {
      const pairingRecord = {
        device_id: pairingDevice.value.device_id,
        device_name: customDeviceName.value || pairingDevice.value.name,
        device_type: selectedDeviceType.value,
        connection_info: pairingDevice.value.connection_info,
        paired_at: new Date().toISOString(),
        auto_connect: autoConnect.value,
        last_connected: null,
        connection_count: 0,
        custom_name: customDeviceName.value || pairingDevice.value.name,
        status: 'active'
      }
      savePairingRecord(pairingRecord)
    }

    currentMode.value = 'discovery'
    loadDevices()
  } catch (error) {
    ElMessage.error('设备配对失败')
    console.error('设备配对失败详情:', error)
    console.error('配对设备:', pairingDevice.value)
    console.error('选择的类型:', selectedDeviceType.value)
  }
}

const connectDevice = async (device: DeviceInfo) => {
  currentMode.value = 'connecting'
  connectingDevice.value = device
  connectionProgress.value = 0
  connectionMessage.value = '正在连接设备...'

  try {
    const progressInterval = setInterval(() => {
      connectionProgress.value += 10
      if (connectionProgress.value >= 100) {
        clearInterval(progressInterval)
        connectionStatus.value = 'success'
        connectionMessage.value = '连接成功'

        setTimeout(() => {
          currentMode.value = 'discovery'
          loadDevices()
        }, 1000)
      } else if (connectionProgress.value === 50) {
        connectionMessage.value = '设备握手...'
      }
    }, 200)

    await deviceApiService.connectDevice(device.device_id)
    ElMessage.success(`设备 ${device.name} 连接成功`)

  } catch (error) {
    connectionStatus.value = 'exception'
    connectionMessage.value = '连接失败'
    ElMessage.error(`设备 ${device.name} 连接失败`)
    console.error('设备连接失败:', error)
  }
}

const disconnectDevice = async (device: DeviceInfo) => {
  try {
    await deviceApiService.disconnectDevice(device.device_id)
    ElMessage.success(`设备 ${device.name} 已断开`)
    loadDevices()
  } catch (error) {
    ElMessage.error(`设备 ${device.name} 断开失败`)
    console.error('设备断开失败:', error)
  }
}

const unpairDevice = async (device: DeviceInfo) => {
  try {
    await ElMessageBox.confirm(
      `确定要取消设备 "${device.name}" 的配对吗？`,
      '取消配对',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deviceApiService.unpairDevice(device.device_id)

    removePairingRecord(device.device_id)

    removePortAssignment(device.device_id)

    ElMessage.success(`设备 ${device.name} 已取消配对`)
    loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`取消设备配对失败`)
      console.error('取消设备配对失败:', error)
    }
  }
}

const getDeviceTemperature = (device: DeviceInfo) => {
  const baseTemps: Record<string, number> = {
    'robot_arm': 45,
    'conveyor_belt': 35,
    'vision_system': 50,
    'temperature_sensor': 25
  }
  return baseTemps[device.device_type] || 30
}

const getDeviceLoad = (device: DeviceInfo) => {
  const baseLoads: Record<string, number> = {
    'robot_arm': 65,
    'conveyor_belt': 40,
    'vision_system': 75,
    'temperature_sensor': 10
  }
  return baseLoads[device.device_type] || 20
}

const getTemperatureColor = (temp: number) => {
  if (temp > 70) return '#ff4d4f'
  if (temp > 60) return '#faad14'
  return '#52c41a'
}

const showDeviceDetails = (device: DeviceInfo) => {
  selectedDevice.value = device
  showDeviceDetailDialog.value = true
}

const refreshDeviceDetails = () => {
  loadDevices()
}

const showPortAssignment = (device: DeviceInfo) => {
  portAssignmentDevice.value = device
  showPortAssignmentDialog.value = true
}

const handlePortAssignment = async (assignmentData: any) => {
  try {
    const portAssignments = getLocalStorageItem('device_port_assignments') || {}
    portAssignments[assignmentData.deviceId] = {
      ...assignmentData,
      deviceName: portAssignmentDevice.value?.name,
      assignedAt: new Date().toISOString()
    }
    setLocalStorageItem('device_port_assignments', portAssignments)

    ElMessage.success('端口分配信息已保存')
    loadPortAssignmentHistory()
    loadDevices()
  } catch (error) {
    ElMessage.error('端口分配保存失败')
    console.error('端口分配保存失败:', error)
  }
}

const showPortAssignmentHistory = () => {
  loadPortAssignmentHistory()
  showPortAssignmentHistoryDialog.value = true
}

const loadPortAssignmentHistory = () => {
  const assignments = getLocalStorageItem('device_port_assignments') || {}
  portAssignmentHistory.value = Object.entries(assignments).map(([deviceId, config]: [string, any]) => ({
    deviceId,
    ...config
  }))
}

const applyPortAssignment = async (record: any) => {
  try {
    await deviceApiService.updatePairingInfo(record.deviceId, {
      port: record.port,
      baud_rate: record.baudRate,
      data_bits: record.dataBits,
      stop_bits: record.stopBits,
      parity: record.parity
    })

    ElMessage.success('端口配置已应用到设备')
  } catch (error) {
    ElMessage.error('应用端口配置失败')
    console.error('应用端口配置失败:', error)
  }
}

const removePortAssignment = (deviceId: string) => {
  const assignments = getLocalStorageItem('device_port_assignments') || {}
  delete assignments[deviceId]
  setLocalStorageItem('device_port_assignments', assignments)
  loadPortAssignmentHistory()
  ElMessage.success('端口分配记录已删除')
}

const formatTimestamp = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('zh-CN')
}

const getLocalStorageItem = (key: string) => {
  try {
    const item = localStorage.getItem(key)
    return item ? JSON.parse(item) : null
  } catch (error) {
    console.error('读取本地存储失败:', error)
    return null
  }
}

const setLocalStorageItem = (key: string, value: any) => {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (error) {
    console.error('保存到本地存储失败:', error)
  }
}

const loadPairingRecords = () => {
  pairingRecords.value = getLocalStorageItem('device_pairing_records') || []
}

const savePairingRecord = (record: any) => {
  const records = getLocalStorageItem('device_pairing_records') || []
  const existingIndex = records.findIndex((r: any) => r.device_id === record.device_id)

  if (existingIndex >= 0) {
    records[existingIndex] = { ...records[existingIndex], ...record }
  } else {
    records.push(record)
  }

  setLocalStorageItem('device_pairing_records', records)
  pairingRecords.value = records
}

const removePairingRecord = (deviceId: string) => {
  const records = getLocalStorageItem('device_pairing_records') || []
  const filteredRecords = records.filter((r: any) => r.device_id !== deviceId)
  setLocalStorageItem('device_pairing_records', filteredRecords)
  pairingRecords.value = filteredRecords
}

const autoConnectPairedDevices = async () => {
  const records = getLocalStorageItem('device_pairing_records') || []
  for (const record of records) {
    if (record.auto_connect && record.status === 'active') {
      try {
        await deviceApiService.connectDevice(record.device_id)
        console.log(`自动连接设备: ${record.device_name}`)
      } catch (error) {
        console.error(`自动连接设备失败: ${record.device_name}`, error)
      }
    }
  }
}

let statusPollingInterval: any = null

const startStatusPolling = () => {
  if (statusPollingInterval) {
    clearInterval(statusPollingInterval)
  }

  statusPollingInterval = setInterval(async () => {
    if (isExpanded.value || connectedDevices.value.length > 0) {
      await loadDevices(false)
    }
  }, 5000)
}

const stopStatusPolling = () => {
  if (statusPollingInterval) {
    clearInterval(statusPollingInterval)
    statusPollingInterval = null
  }
}

const setupWebSocket = () => {
  deviceWebSocketService.registerHandlers({
    onDeviceConnected: (data) => {
      ElMessage.success(`设备 ${data.name} 已连接`)
      loadDevices(true)
    },
    onDeviceDisconnected: (data) => {
      ElMessage.warning(`设备 ${data.name} 已断开连接`)
      loadDevices(true)
    },
    onDeviceError: (data) => {
      ElMessage.error(`设备错误: ${data.error}`)
      updateDeviceStatus(data.device_id, ConnectionStatus.ERROR)
    },
    onDeviceStatusUpdated: (data) => {
      if (data.device_id) {
        const status = convertStringToConnectionStatus(data.status)
        updateDeviceStatus(data.device_id, status)
      } else {
        setTimeout(() => loadDevices(false), 1000)
      }
    }
  })

  deviceWebSocketService.connect()

  const checkWebSocketConnection = setInterval(() => {
    if (!deviceWebSocketService.getConnectionStatus()) {
      console.warn('WebSocket连接断开，尝试重新连接...')
      deviceWebSocketService.connect()
    }
  }, 10000)

  onUnmounted(() => {
    clearInterval(checkWebSocketConnection)
  })
}

const convertStringToConnectionStatus = (status: string): ConnectionStatus => {
  switch (status) {
    case 'connected':
      return ConnectionStatus.CONNECTED
    case 'disconnected':
      return ConnectionStatus.DISCONNECTED
    case 'connecting':
      return ConnectionStatus.CONNECTING
    case 'error':
      return ConnectionStatus.ERROR
    default:
      return ConnectionStatus.DISCONNECTED
  }
}

const updateDeviceStatus = (deviceId: string, status: ConnectionStatus) => {
  const deviceIndex = devices.value.findIndex(device => device.device_id === deviceId)
  if (deviceIndex !== -1) {
    devices.value[deviceIndex].status = status
    devices.value = [...devices.value]
  }
}

onMounted(() => {
  console.log('EquipmentMonitor 组件已挂载')
  loadDevices(true)
  loadPairingRecords()
  loadPortAssignmentHistory()
  setupWebSocket()

  startStatusPolling()

  setTimeout(() => {
    autoConnectPairedDevices()
  }, 2000)

  if (import.meta.env.DEV) {
    setTimeout(() => {
      console.log('当前设备数据状态检查:')
      console.log('devices:', devices.value)
      console.log('connectedDevices:', connectedDevices.value)
      console.log('newDevices:', newDevices.value)
      console.log('historicalDevices:', historicalDevices.value)
    }, 1000)
  }
})

onUnmounted(() => {
  stopStatusPolling()
  deviceWebSocketService.disconnect()
})
</script>

<style scoped lang="scss">
.equipment-monitor {
  width: 100%;
  height: 100%;

  .global-monitor-entry {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.1) 0%, rgba(64, 158, 255, 0.05) 100%);
    border: 1px solid rgba(64, 158, 255, 0.4);
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    cursor: pointer;

    &:hover {
      border-color: rgba(64, 158, 255, 0.7);
      box-shadow: 0 6px 24px rgba(64, 158, 255, 0.2);
      transform: translateY(-2px);
    }

    .entry-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;

      .entry-icon {
        position: relative;
        margin-right: 16px;

        .status-dot {
          position: absolute;
          bottom: 4px;
          right: 4px;
          width: 10px;
          height: 10px;
          border-radius: 50%;
          border: 2px solid #0f1325;

          &.connected {
            background: #67C23A;
            box-shadow: 0 0 8px rgba(103, 194, 58, 0.8);
          }
        }
      }

      .entry-info {
        flex: 1;

        h3 {
          margin: 0;
          font-size: 18px;
          color: #e0e0e0;
          font-weight: 600;
          margin-bottom: 6px;
        }

        .entry-stats {
          display: flex;
          gap: 16px;

          .stat-item {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 13px;
            color: #909399;

            .el-icon {
              font-size: 14px;
            }
          }
        }
      }

      .entry-arrow {
        color: #409EFF;
        font-size: 20px;
      }
    }

    .entry-preview {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.1);

      .device-icons-preview {
        position: relative;
        height: 24px;
        display: flex;
        align-items: center;

        .preview-icon {
          position: absolute;
          width: 24px;
          height: 24px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid rgba(255, 255, 255, 0.2);

          .el-icon {
            font-size: 12px;
          }
        }

        .more-count {
          margin-left: 40px;
          font-size: 12px;
          color: #909399;
          background: rgba(255, 255, 255, 0.1);
          padding: 2px 6px;
          border-radius: 10px;
        }
      }

      .system-status {
        .el-tag {
          font-size: 12px;
        }
      }
    }
  }

  &.fullscreen-mode {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1000;
    padding: 0;
    background: #0a0e1a;

    .fullscreen-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      background: rgba(255, 255, 255, 0.05);
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);

      .header-left {
        display: flex;
        align-items: center;
        gap: 16px;

        h2 {
          margin: 0;
          color: #409EFF;
        }
      }

      .header-actions {
        display: flex;
        gap: 12px;
        align-items: center;
      }
    }

    .fullscreen-content {
      flex: 1;
      padding: 24px;
      overflow: auto;

      .content-layout {
        display: grid;
        grid-template-columns: 1fr 400px;
        gap: 24px;
        height: 100%;

        .left-panel {
          .device-discovery-panel {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 20px;
            height: 100%;
            overflow-y: auto;

            .panel-header {
              margin-bottom: 20px;

              h3 {
                margin: 0;
                color: #409EFF;
              }
            }
          }
        }

        .right-panel {
          .status-panel {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 20px;
            height: 100%;
            overflow-y: auto;

            h3 {
              margin: 0 0 20px 0;
              color: #409EFF;
            }

            .status-grid {
              display: flex;
              flex-direction: column;
              gap: 16px;

              .device-status-card {
                background: rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 16px;

                .status-card-header {
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                  margin-bottom: 12px;

                  .device-title {
                    display: flex;
                    align-items: center;
                    gap: 8px;

                    .device-name {
                      font-weight: 500;
                    }
                  }
                }

                .status-metrics {
                  display: grid;
                  grid-template-columns: 1fr 1fr;
                  gap: 12px;
                  margin-bottom: 12px;

                  .metric-item {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;

                    .metric-label {
                      font-size: 12px;
                      color: #909399;
                    }

                    .metric-value {
                      display: flex;
                      align-items: center;
                      gap: 8px;

                      .el-progress {
                        flex: 1;
                      }

                      .metric-text {
                        font-size: 12px;
                        font-weight: bold;
                        min-width: 40px;
                      }
                    }

                    .metric-text {
                      font-size: 14px;
                      font-weight: 500;
                    }
                  }
                }

                .status-actions {
                  display: flex;
                  gap: 8px;

                  .el-button {
                    flex: 1;
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  .sidebar-mode {
    width: 280px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 16px;
    transition: all 0.3s ease;
    flex-shrink: 0;

    &.expanded {
      width: 320px;
    }

    .sidebar-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);

      h3 {
        margin: 0;
        color: #409EFF;
        font-size: 16px;
      }

      .expand-btn {
        color: #409EFF;
        padding: 4px 8px;
        font-size: 12px;
      }
    }

    .connected-devices-sidebar {
      .devices-count {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
        padding: 8px 12px;
        background: rgba(64, 158, 255, 0.1);
        border-radius: 6px;
        font-size: 14px;
        color: #409EFF;

        .el-icon {
          font-size: 16px;
        }
      }

      .devices-list {
        max-height: 300px;
        overflow-y: auto;

        .device-item-sidebar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px;
          margin-bottom: 8px;
          background: rgba(255, 255, 255, 0.08);
          border-radius: 6px;
          transition: all 0.3s;

          &:hover {
            background: rgba(255, 255, 255, 0.12);
          }

          .device-info {
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;

            .device-icon-status {
              position: relative;
              display: flex;
              align-items: center;

              .status-dot {
                position: absolute;
                bottom: -2px;
                right: -2px;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                border: 1px solid #0f1325;

                &.connected {
                  background: #67C23A;
                }

                &.disconnected {
                  background: #909399;
                }

                &.error {
                  background: #F56C6C;
                }
              }
            }

            .device-details {
              .device-name {
                font-size: 14px;
                font-weight: 500;
                margin-bottom: 2px;
              }

              .device-type {
                font-size: 12px;
                color: #909399;
              }
            }
          }

          .device-actions {
            display: flex;
            gap: 4px;

            .el-button {
              padding: 4px 8px;
              font-size: 12px;
            }
          }
        }
      }
    }

    .status-parameters {
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.1);

      .parameters-header {
        margin-bottom: 12px;

        h4 {
          margin: 0;
          font-size: 14px;
          color: #409EFF;
        }
      }

      .parameters-list {
        .device-parameters {
          margin-bottom: 12px;
          padding: 12px;
          background: rgba(255, 255, 255, 0.08);
          border-radius: 6px;

          .parameter-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;

            .device-name {
              font-size: 13px;
              font-weight: 500;
            }
          }

          .parameter-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;

            .parameter-item {
              display: flex;
              flex-direction: column;
              gap: 4px;

              .param-label {
                font-size: 12px;
                color: #909399;
              }

              .param-value {
                display: flex;
                align-items: center;
                gap: 6px;

                .el-progress {
                  flex: 1;
                }

                .param-text {
                  font-size: 12px;
                  font-weight: bold;
                  min-width: 40px;
                  text-align: right;
                }
              }
            }
          }
        }
      }
    }
  }

  .full-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .device-discovery-panel {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 20px;

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;

      h3 {
        margin: 0;
        color: #409EFF;
      }

      .header-actions {
        display: flex;
        gap: 12px;
        align-items: center;
      }
    }

    .scanning-progress {
      text-align: center;
      padding: 20px;

      .scanning-animation {
        position: relative;
        width: 80px;
        height: 80px;
        margin: 0 auto 16px;

        .radar {
          width: 100%;
          height: 100%;
          border: 2px solid #409EFF;
          border-radius: 50%;
          position: relative;
          animation: rotate 2s linear infinite;
        }

        .radar-pulse {
          position: absolute;
          top: 50%;
          left: 50%;
          width: 0;
          height: 0;
          border-radius: 50%;
          background: #409EFF;
          animation: pulse 2s linear infinite;
        }
      }

      @keyframes rotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }

      @keyframes pulse {
        0% {
          width: 0;
          height: 0;
          opacity: 1;
          transform: translate(-50%, -50%);
        }
        100% {
          width: 80px;
          height: 80px;
          opacity: 0;
          transform: translate(-50%, -50%);
        }
      }
    }

    .discovery-mode {
      .device-categories {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 20px;

        .category-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 16px;
          background: rgba(255, 255, 255, 0.08);
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s;
          border: 1px solid transparent;

          &:hover {
            background: rgba(255, 255, 255, 0.12);
          }

          &.active {
            border-color: #409EFF;
            background: rgba(64, 158, 255, 0.1);
          }

          .category-name {
            margin: 8px 0 4px;
            font-weight: 500;
          }

          .device-count {
            font-size: 12px;
            color: #909399;
          }
        }
      }

      .device-list {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 16px;

        .device-item {
          .device-card {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 16px;
            transition: all 0.3s;
            border: 1px solid transparent;

            &.paired {
              border-color: #67C23A;
            }

            &.connected {
              border-color: #409EFF;
            }

            &.error {
              border-color: #F56C6C;
            }

            .device-header {
              display: flex;
              align-items: center;
              gap: 12px;
              margin-bottom: 12px;

              .device-icon {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 40px;
                height: 40px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
              }

              .device-info {
                flex: 1;

                h4 {
                  margin: 0 0 4px;
                  font-size: 16px;
                }

                p {
                  margin: 0 0 8px;
                  font-size: 12px;
                  color: #909399;
                }

                .device-tags {
                  display: flex;
                  gap: 6px;
                }
              }
            }

            .device-actions {
              display: flex;
              gap: 8px;
              flex-wrap: wrap;
            }
          }
        }
      }
    }

    .pairing-mode {
      .pairing-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
      }

      .pairing-content {
        .device-to-pair {
          display: flex;
          gap: 30px;
          align-items: flex-start;

          .device-preview {
            text-align: center;
            padding: 20px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            min-width: 150px;

            h5 {
              margin: 12px 0 4px;
            }

            p {
              margin: 0;
              color: #909399;
              font-size: 12px;
            }
          }

          .pairing-options {
            flex: 1;

            h5 {
              margin: 0 0 12px;
            }

            .device-type-selection {
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
              gap: 12px;
              margin-bottom: 20px;

              .type-option {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 16px;
                background: rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s;
                border: 1px solid transparent;

                &:hover {
                  background: rgba(255, 255, 255, 0.12);
                }

                &.selected {
                  border-color: #409EFF;
                  background: rgba(64, 158, 255, 0.1);
                }

                span {
                  margin-top: 8px;
                  font-size: 14px;
                }
              }
            }

            .pairing-settings {
              margin-bottom: 20px;

              .el-input {
                margin-bottom: 12px;
              }
            }
          }
        }
      }
    }

    .connecting-mode {
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 40px;

      .connection-progress {
        display: flex;
        align-items: center;
        gap: 20px;

        .connection-info {
          h4 {
            margin: 0 0 8px;
          }

          p {
            margin: 0 0 4px;
          }

          .connection-message {
            color: #909399;
            font-size: 14px;
          }
        }
      }
    }
  }

}

.port-assignment-history {
  .empty-state {
    text-align: center;
    padding: 40px 0;
  }

  .history-list {
    max-height: 400px;
    overflow-y: auto;

    .history-item {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 12px;
      border: 1px solid #e9ecef;

      .record-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;

        h5 {
          margin: 0;
          color: #303133;
        }
      }

      .record-details {
        p {
          margin: 4px 0;
          color: #606266;
          font-size: 14px;

          &.timestamp {
            color: #909399;
            font-size: 12px;
          }
        }
      }

      .record-actions {
        display: flex;
        gap: 8px;
        margin-top: 12px;
      }
    }
  }
}

@media (max-width: 768px) {
  .equipment-monitor {
    padding: 12px;
    flex-direction: column;

    .sidebar-mode {
      width: 100%;
      margin-bottom: 20px;

      &.expanded {
        width: 100%;
      }
    }

    .full-content {
      width: 100%;
    }

    .device-discovery-panel {
      .panel-header {
        flex-direction: column;
        gap: 12px;
        align-items: flex-start;
      }

      .discovery-mode {
        .device-categories {
          grid-template-columns: repeat(2, 1fr);
        }

        .device-list {
          grid-template-columns: 1fr;
        }
      }

      .pairing-mode {
        .pairing-content {
          .device-to-pair {
            flex-direction: column;
          }
        }
      }

      .connecting-mode {
        .connection-progress {
          flex-direction: column;
          text-align: center;
        }
      }
    }
  }
}
</style>
