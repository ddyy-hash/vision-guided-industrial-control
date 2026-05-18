<template>
  <div class="device-manager">
    <EquipmentMonitor
      name="设备监控中心"
      id="device-monitor-main"
      type="monitor"
    />

    <div class="statistics-panel" v-if="showStatisticsPanel">
      <DeviceStatistics />
    </div>

    <el-dialog v-model="settingsDialogVisible" title="设备管理设置" width="500px">
      <DeviceSettings
        :settings="deviceSettings"
        @update-settings="updateSettings"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  Setting
} from '@element-plus/icons-vue'
import EquipmentMonitor from './EquipmentMonitor.vue'
import DeviceStatistics from './DeviceStatistics.vue'
import DeviceSettings from './DeviceSettings.vue'

const showStatisticsPanel = ref(false)
const settingsDialogVisible = ref(false)
const deviceSettings = ref({
  autoScan: true,
  scanInterval: 5,
  autoReconnect: true,
  maxReconnectAttempts: 3
})

const showStatistics = () => {
  showStatisticsPanel.value = !showStatisticsPanel.value
}

const showSettings = () => {
  settingsDialogVisible.value = true
}

const updateSettings = async (newSettings: any) => {
  deviceSettings.value = newSettings
  ElMessage.success('设置已更新')
  settingsDialogVisible.value = false
}

onMounted(() => {
  console.log('DeviceManager 组件已挂载，现在使用EquipmentMonitor显示真实设备数据')
})
</script>

<style scoped lang="scss">
.device-manager {
  height: 100%;
  background: #0f1325;
  color: #e0e0e0;

  .statistics-panel {
    position: fixed;
    top: 80px;
    right: 20px;
    width: 500px;
    height: calc(100vh - 100px);
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    overflow-y: auto;
    padding: 20px;
    z-index: 1000;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  }
}

@media (max-width: 768px) {
  .device-manager {
    .statistics-panel {
      width: 100%;
      right: 0;
      left: 0;
      height: 50vh;
    }
  }
}
</style>