<template>
  <div class="device-settings">
    <div class="settings-section">
      <h3 class="section-title">扫描设置</h3>
      <div class="setting-item">
        <label class="setting-label">自动扫描</label>
        <el-switch
          v-model="settings.autoScan"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">扫描间隔 (秒)</label>
        <el-input-number
          v-model="settings.scanInterval"
          :min="1"
          :max="300"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">扫描超时 (秒)</label>
        <el-input-number
          v-model="settings.scanTimeout"
          :min="5"
          :max="120"
          @change="updateSettings"
        />
      </div>
    </div>

    <div class="settings-section">
      <h3 class="section-title">连接设置</h3>
      <div class="setting-item">
        <label class="setting-label">自动重连</label>
        <el-switch
          v-model="settings.autoReconnect"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">最大重试次数</label>
        <el-input-number
          v-model="settings.maxReconnectAttempts"
          :min="1"
          :max="10"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">重连间隔 (秒)</label>
        <el-input-number
          v-model="settings.reconnectInterval"
          :min="1"
          :max="60"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">连接超时 (秒)</label>
        <el-input-number
          v-model="settings.connectionTimeout"
          :min="5"
          :max="120"
          @change="updateSettings"
        />
      </div>
    </div>

    <div class="settings-section">
      <h3 class="section-title">设备发现</h3>
      <div class="setting-item">
        <label class="setting-label">串口扫描</label>
        <el-switch
          v-model="settings.serialScan"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">网络扫描</label>
        <el-switch
          v-model="settings.networkScan"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">蓝牙扫描</label>
        <el-switch
          v-model="settings.bluetoothScan"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">USB扫描</label>
        <el-switch
          v-model="settings.usbScan"
          @change="updateSettings"
        />
      </div>
    </div>

    <div class="settings-section">
      <h3 class="section-title">数据管理</h3>
      <div class="setting-item">
        <label class="setting-label">数据保留天数</label>
        <el-input-number
          v-model="settings.dataRetentionDays"
          :min="1"
          :max="365"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">自动清理历史</label>
        <el-switch
          v-model="settings.autoCleanup"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">最大设备数量</label>
        <el-input-number
          v-model="settings.maxDevices"
          :min="10"
          :max="1000"
          @change="updateSettings"
        />
      </div>
    </div>

    <div class="settings-section">
      <h3 class="section-title">通知设置</h3>
      <div class="setting-item">
        <label class="setting-label">设备连接通知</label>
        <el-switch
          v-model="settings.notifyConnect"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">设备断开通知</label>
        <el-switch
          v-model="settings.notifyDisconnect"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">设备错误通知</label>
        <el-switch
          v-model="settings.notifyError"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">扫描完成通知</label>
        <el-switch
          v-model="settings.notifyScanComplete"
          @change="updateSettings"
        />
      </div>
    </div>

    <div class="settings-section">
      <h3 class="section-title">高级设置</h3>
      <div class="setting-item">
        <label class="setting-label">调试模式</label>
        <el-switch
          v-model="settings.debugMode"
          @change="updateSettings"
        />
      </div>
      <div class="setting-item">
        <label class="setting-label">日志级别</label>
        <el-select
          v-model="settings.logLevel"
          @change="updateSettings"
          placeholder="选择日志级别"
        >
          <el-option label="错误" value="error" />
          <el-option label="警告" value="warn" />
          <el-option label="信息" value="info" />
          <el-option label="调试" value="debug" />
        </el-select>
      </div>
      <div class="setting-item">
        <label class="setting-label">心跳间隔 (秒)</label>
        <el-input-number
          v-model="settings.heartbeatInterval"
          :min="5"
          :max="300"
          @change="updateSettings"
        />
      </div>
    </div>

    <div class="settings-actions">
      <el-button type="primary" @click="saveSettings">
        <el-icon><Check /></el-icon>
        保存设置
      </el-button>
      <el-button @click="resetSettings">
        <el-icon><Refresh /></el-icon>
        恢复默认
      </el-button>
      <el-button type="danger" @click="clearData">
        <el-icon><Delete /></el-icon>
        清除数据
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Refresh, Delete } from '@element-plus/icons-vue'

interface DeviceSettings {
  autoScan: boolean
  scanInterval: number
  scanTimeout: number
  autoReconnect: boolean
  maxReconnectAttempts: number
  reconnectInterval: number
  connectionTimeout: number
  serialScan: boolean
  networkScan: boolean
  bluetoothScan: boolean
  usbScan: boolean
  dataRetentionDays: number
  autoCleanup: boolean
  maxDevices: number
  notifyConnect: boolean
  notifyDisconnect: boolean
  notifyError: boolean
  notifyScanComplete: boolean
  debugMode: boolean
  logLevel: string
  heartbeatInterval: number
}

interface Props {
  settings: DeviceSettings
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update-settings', settings: DeviceSettings): void
}>()

const settings = ref<DeviceSettings>({ ...props.settings })

const defaultSettings: DeviceSettings = {
  autoScan: true,
  scanInterval: 30,
  scanTimeout: 30,
  autoReconnect: true,
  maxReconnectAttempts: 3,
  reconnectInterval: 5,
  connectionTimeout: 30,
  serialScan: true,
  networkScan: true,
  bluetoothScan: true,
  usbScan: true,
  dataRetentionDays: 30,
  autoCleanup: true,
  maxDevices: 100,
  notifyConnect: true,
  notifyDisconnect: true,
  notifyError: true,
  notifyScanComplete: false,
  debugMode: false,
  logLevel: 'info',
  heartbeatInterval: 30
}

watch(() => props.settings, (newSettings) => {
  settings.value = { ...newSettings }
}, { deep: true })

const updateSettings = () => {
  emit('update-settings', settings.value)
}

const saveSettings = () => {
  emit('update-settings', settings.value)
  ElMessage.success('设置已保存')
}

const resetSettings = () => {
  ElMessageBox.confirm(
    '确定要恢复默认设置吗？所有自定义设置将被重置。',
    '恢复默认设置',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    settings.value = { ...defaultSettings }
    emit('update-settings', settings.value)
    ElMessage.success('已恢复默认设置')
  })
}

const clearData = () => {
  ElMessageBox.confirm(
    '确定要清除所有设备数据吗？此操作不可撤销，所有设备信息和历史记录将被删除。',
    '清除设备数据',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'error'
    }
  ).then(() => {
    ElMessage.success('设备数据已清除')
  })
}
</script>

<style scoped>
.device-settings {
  padding: 0;
}

.settings-section {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 16px 0;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 8px 0;
}

.setting-label {
  font-size: 14px;
  color: #4a5568;
  font-weight: 500;
}

.settings-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

@media (max-width: 768px) {
  .setting-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .settings-actions {
    flex-direction: column;
  }
}
</style>