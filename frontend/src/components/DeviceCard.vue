<template>
  <div class="equipment-card" :class="cardClass">
    <div class="header">
      <el-icon :size="20"><Cpu /></el-icon>
      <h3>{{ name }}</h3>
      <el-tag :type="statusType">{{ statusText }}</el-tag>
      <el-tag size="small" :type="platformType">{{ platformLabel }}</el-tag>
    </div>
    <div class="metrics">
      <div class="metric">
        <span>温度</span>
        <el-progress :percentage="temp" :color="tempColor" :show-text="false" />
        <span>{{ tempDisplay }}</span>
      </div>
      <div class="metric">
        <span>负载</span>
        <el-progress :percentage="load" status="success" :show-text="false" />
        <span>{{ loadDisplay }}</span>
      </div>
      <div class="metric" v-if="platformInfo.type === PlatformType.HONGZOS">
        <span>节点ID</span>
        <span>{{ nodeId || 'N/A' }}</span>
      </div>
      <div class="metric" v-if="isKylin">
        <span>麒麟特性</span>
        <span>安全加固</span>
      </div>
      <div class="metric" v-if="isUOS">
        <span>UOS特性</span>
        <span>国产兼容</span>
      </div>
      <div class="metric" v-if="isHarmony">
        <span>鸿蒙特性</span>
        <span>分布式</span>
      </div>
    </div>
    <div class="actions">
      <el-button :type="isRunning ? 'danger' : 'success'" @click="toggleRun" :disabled="!isConnected">
        {{ isRunning ? '停止' : '启动' }}
      </el-button>
      <el-button @click="showDetails">详情</el-button>
      <el-button type="info" @click="showLog">日志</el-button>
    </div>
    <div class="connection-status">
      <el-tag :type="isConnected ? 'success' : 'danger'" size="small">
        {{ isConnected ? '已连接' : '未连接' }}
      </el-tag>
      <el-tag v-if="hasAlert" type="danger" size="small">告警</el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { Cpu } from '@element-plus/icons-vue';
import { SystemAPI } from '../native/system-adapter';
import type { DeviceConnection } from '../native/system-adapter';
import { PlatformType } from '../utils/platform';

const props = defineProps({
  name: String,
  id: String,
  type: String
});

const temp = ref<number>(35);
const load = ref<number>(30);
const isRunning = ref(true);
const isConnected = ref(false);
const nodeId = ref('');
const platformInfo = SystemAPI.getSystemInfo();
const logList = ref<string[]>([]);
const hasAlert = computed(() => temp.value > 70 || load.value > 90);

let deviceConnection: DeviceConnection | null = null;

const isKylin = computed(() => platformInfo.type === PlatformType.KYLIN);
const isUOS = computed(() => platformInfo.type === PlatformType.UOS);
const isHarmony = computed(() => platformInfo.type === PlatformType.HARMONY);

const platformLabel = computed(() => {
  switch (platformInfo.type) {
    case PlatformType.HONGZOS: return '鸿蒙';
    case PlatformType.KYLIN: return '麒麟';
    case PlatformType.UOS: return 'UOS';
    case PlatformType.HARMONY: return 'HarmonyOS';
    case PlatformType.LINUX: return 'Linux';
    case PlatformType.WINDOWS: return 'Windows';
    default: return '未知平台';
  }
});

const cardClass = computed(() => {
  return {
    warning: temp.value > 60,
    kylin: isKylin.value,
    uos: isUOS.value,
    harmony: isHarmony.value
  };
});

const tempDisplay = computed(() => isNaN(temp.value) ? '--' : `${temp.value}°C`);
const loadDisplay = computed(() => isNaN(load.value) ? '--' : `${load.value}%`);

const connectToDevice = async () => {
  try {
    deviceConnection = SystemAPI.connectDevice(props.id!);
    deviceConnection.onData((data) => {
      temp.value = typeof data.temp === 'number' ? parseFloat(data.temp.toFixed(1)) : 0;
      load.value = typeof data.load === 'number' ? parseFloat(data.load.toFixed(1)) : 0;
      if (data.nodeId) nodeId.value = data.nodeId;
      isConnected.value = true;
      logList.value.push(`[${new Date().toLocaleTimeString()}] 数据: 温度${temp.value} 负载${load.value}`);
    });
    logList.value.push(`[${new Date().toLocaleTimeString()}] 设备${props.id}连接成功`);
  } catch (error) {
    logList.value.push(`[${new Date().toLocaleTimeString()}] 设备${props.id}连接失败`);
    isConnected.value = false;
  }
};

const disconnectDevice = () => {
  if (deviceConnection) {
    deviceConnection.disconnect();
    deviceConnection = null;
    isConnected.value = false;
    logList.value.push(`[${new Date().toLocaleTimeString()}] 设备${props.id}断开连接`);
  }
};

const statusType = computed(() => temp.value > 70 ? 'danger' : temp.value > 60 ? 'warning' : 'success');
const statusText = computed(() => temp.value > 70 ? '故障' : temp.value > 60 ? '警告' : '正常');
const tempColor = computed(() => {
  if (temp.value > 70) return '#ff4d4f';
  if (temp.value > 60) return '#faad14';
  return '#52c41a';
});
const platformType = computed(() => {
  switch (platformInfo.type) {
    case PlatformType.HONGZOS: return 'success';
    case PlatformType.KYLIN: return 'info';
    case PlatformType.UOS: return 'primary';
    case PlatformType.HARMONY: return 'success';
    case PlatformType.LINUX: return 'info';
    case PlatformType.WINDOWS: return 'warning';
    default: return 'danger';
  }
});

async function toggleRun() {
  if (!deviceConnection || !isConnected.value) return;
  isRunning.value = !isRunning.value;
  try {
    await deviceConnection.sendCommand(isRunning.value ? 'START' : 'STOP');
    logList.value.push(`[${new Date().toLocaleTimeString()}] 设备${props.id}状态切换为: ${isRunning.value ? '运行' : '停止'}`);
  } catch (error) {
    logList.value.push(`[${new Date().toLocaleTimeString()}] 设备控制失败`);
    isRunning.value = !isRunning.value;
  }
}

function showDetails() {
  logList.value.push(`[${new Date().toLocaleTimeString()}] 查看详情`);
}

function showLog() {
  alert(logList.value.slice(-10).join('\n'));
}

onMounted(() => {
  connectToDevice();
});
onUnmounted(() => {
  disconnectDevice();
});
</script>

<style scoped lang="scss">
.equipment-card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s;
  border: 1px solid rgba(255, 255, 255, 0.1);
  &.warning {
    border-color: #faad14;
    background: rgba(250, 173, 20, 0.1);
  }
  &.kylin {
    box-shadow: 0 0 8px #1e90ff44;
    border-color: #1e90ff;
  }
  &.uos {
    box-shadow: 0 0 8px #00bcd444;
    border-color: #00bcd4;
  }
  &.harmony {
    box-shadow: 0 0 8px #00c85344;
    border-color: #00c853;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    h3 {
      margin: 0;
      font-size: 16px;
      flex-grow: 1;
    }
  }
  .metrics {
    margin-bottom: 16px;
    .metric {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
      span:first-child {
        min-width: 50px;
        font-size: 14px;
      }
      .el-progress {
        flex: 1;
      }
      span:last-child {
        font-weight: bold;
        min-width: 50px;
        text-align: right;
      }
    }
  }
  .actions {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
    button {
      flex: 1;
    }
  }
  .connection-status {
    text-align: center;
  }
}
</style>