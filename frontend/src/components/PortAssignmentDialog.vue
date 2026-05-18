<template>
  <el-dialog
    v-model="visible"
    title="端口分配"
    width="500px"
    :before-close="handleClose"
  >
    <div class="port-assignment-dialog">
      <div class="device-info">
        <div class="device-icon">
          <el-icon :size="32"><Cpu /></el-icon>
        </div>
        <div class="device-details">
          <h4>{{ device?.name || '未知设备' }}</h4>
          <p>{{ device?.connection_info || '未知连接信息' }}</p>
          <el-tag v-if="device?.device_type" size="small">
            {{ getDeviceTypeName(device.device_type) }}
          </el-tag>
        </div>
      </div>

      <div class="port-selection">
        <h5>选择通信端口</h5>
        <div class="port-options">
          <div
            v-for="port in availablePorts"
            :key="port.name"
            class="port-option"
            :class="{ selected: selectedPort === port.name }"
            @click="selectPort(port.name)"
          >
            <div class="port-icon">
              <el-icon :size="20"><component :is="port.icon" /></el-icon>
            </div>
            <div class="port-info">
              <span class="port-name">{{ port.name }}</span>
              <span class="port-description">{{ port.description }}</span>
            </div>
            <div class="port-status">
              <el-tag
                v-if="port.status === 'available'"
                size="small"
                type="success"
              >
                可用
              </el-tag>
              <el-tag
                v-else-if="port.status === 'occupied'"
                size="small"
                type="warning"
              >
                占用
              </el-tag>
              <el-tag
                v-else
                size="small"
                type="info"
              >
                未知
              </el-tag>
            </div>
          </div>
        </div>

        <div class="custom-port">
          <el-input
            v-model="customPort"
            placeholder="输入自定义端口 (如: /dev/ttyUSB0, COM3)"
            clearable
          >
            <template #prepend>
              <el-icon><Edit /></el-icon>
            </template>
          </el-input>
        </div>
      </div>

      <div class="connection-params">
        <h5>连接参数</h5>
        <div class="params-grid">
          <el-input
            v-model="baudRate"
            placeholder="波特率"
            type="number"
          >
            <template #prepend>波特率</template>
          </el-input>

          <el-select v-model="dataBits" placeholder="数据位">
            <el-option label="5" value="5" />
            <el-option label="6" value="6" />
            <el-option label="7" value="7" />
            <el-option label="8" value="8" />
          </el-select>

          <el-select v-model="stopBits" placeholder="停止位">
            <el-option label="1" value="1" />
            <el-option label="1.5" value="1.5" />
            <el-option label="2" value="2" />
          </el-select>

          <el-select v-model="parity" placeholder="校验位">
            <el-option label="无" value="none" />
            <el-option label="奇校验" value="odd" />
            <el-option label="偶校验" value="even" />
          </el-select>
        </div>
      </div>

      <div class="test-connection">
        <el-button
          type="primary"
          :loading="testing"
          @click="testConnection"
        >
          <el-icon><Connection /></el-icon>
          测试连接
        </el-button>
        <span v-if="testResult" class="test-result" :class="testResult.type">
          {{ testResult.message }}
        </span>
      </div>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          :disabled="!selectedPort && !customPort"
          :loading="assigning"
          @click="handleAssign"
        >
          分配端口
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Cpu,
  Edit,
  Connection,
  Monitor,
  VideoCamera,
  Iphone,
  Platform
} from '@element-plus/icons-vue'
import type { DeviceInfo } from '../types/device'

interface Props {
  modelValue: boolean
  device?: DeviceInfo
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'assign', data: PortAssignmentData): void
}

interface PortAssignmentData {
  deviceId: string
  port: string
  baudRate: number
  dataBits: number
  stopBits: number
  parity: string
}

interface TestResult {
  type: 'success' | 'error' | 'warning'
  message: string
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const selectedPort = ref('')
const customPort = ref('')
const baudRate = ref(9600)
const dataBits = ref(8)
const stopBits = ref(1)
const parity = ref('none')
const testing = ref(false)
const assigning = ref(false)
const testResult = ref<TestResult | null>(null)

const availablePorts = ref([
  {
    name: 'COM1',
    description: '串行端口1',
    icon: VideoCamera,
    status: 'available' as const
  },
  {
    name: 'COM2',
    description: '串行端口2',
    icon: VideoCamera,
    status: 'available' as const
  },
  {
    name: 'COM3',
    description: '串行端口3',
    icon: VideoCamera,
    status: 'occupied' as const
  },
  {
    name: '/dev/ttyUSB0',
    description: 'USB串行设备',
    icon: Platform,
    status: 'available' as const
  },
  {
    name: '/dev/ttyUSB1',
    description: 'USB串行设备',
    icon: Platform,
    status: 'available' as const
  },
  {
    name: '蓝牙设备',
    description: '蓝牙通信',
    icon: Monitor,
    status: 'available' as const
  },
  {
    name: '网络端口',
    description: 'TCP/IP连接',
    icon: Iphone,
    status: 'available' as const
  }
])

const getDeviceTypeName = (type: string) => {
  const typeMap: Record<string, string> = {
    'robot_arm': '机械臂',
    'conveyor_belt': '传送带',
    'vision_system': '视觉系统',
    'temperature_sensor': '温度传感器',
    'unknown': '未知设备'
  }
  return typeMap[type] || type
}

const selectPort = (port: string) => {
  selectedPort.value = port
  customPort.value = ''
}

const testConnection = async () => {
  if (!selectedPort.value && !customPort.value) {
    ElMessage.warning('请先选择或输入端口')
    return
  }

  testing.value = true
  testResult.value = null

  try {
    await new Promise(resolve => setTimeout(resolve, 2000))

    const success = Math.random() > 0.3
    if (success) {
      testResult.value = {
        type: 'success',
        message: '连接测试成功！设备响应正常。'
      }
      ElMessage.success('连接测试成功')
    } else {
      testResult.value = {
        type: 'error',
        message: '连接测试失败：无法建立通信连接'
      }
      ElMessage.error('连接测试失败')
    }
  } catch (error) {
    testResult.value = {
      type: 'error',
      message: `连接测试异常：${error}`
    }
    ElMessage.error('连接测试异常')
  } finally {
    testing.value = false
  }
}

const handleAssign = async () => {
  if (!props.device) {
    ElMessage.error('设备信息缺失')
    return
  }

  const port = selectedPort.value || customPort.value
  if (!port) {
    ElMessage.warning('请选择或输入端口')
    return
  }

  assigning.value = true

  try {
    const assignmentData: PortAssignmentData = {
      deviceId: props.device.device_id,
      port: port,
      baudRate: baudRate.value,
      dataBits: dataBits.value,
      stopBits: stopBits.value,
      parity: parity.value
    }

    await new Promise(resolve => setTimeout(resolve, 1000))

    emit('assign', assignmentData)
    ElMessage.success('端口分配成功')
    visible.value = false
  } catch (error) {
    ElMessage.error('端口分配失败')
  } finally {
    assigning.value = false
  }
}

const handleClose = () => {
  visible.value = false
  selectedPort.value = ''
  customPort.value = ''
  baudRate.value = 9600
  dataBits.value = 8
  stopBits.value = 1
  parity.value = 'none'
  testResult.value = null
}

watch(visible, (newVal) => {
  if (newVal) {
    testResult.value = null
  }
})
</script>

<style scoped lang="scss">
.port-assignment-dialog {
  .device-info {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px;
    background: rgba(64, 158, 255, 0.05);
    border-radius: 8px;
    margin-bottom: 20px;

    .device-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      background: rgba(64, 158, 255, 0.1);
      border-radius: 8px;
    }

    .device-details {
      flex: 1;

      h4 {
        margin: 0 0 4px;
        color: #303133;
      }

      p {
        margin: 0 0 8px;
        color: #606266;
        font-size: 14px;
      }
    }
  }

  .port-selection {
    margin-bottom: 20px;

    h5 {
      margin: 0 0 12px;
      color: #303133;
      font-size: 16px;
    }

    .port-options {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      margin-bottom: 16px;

      .port-option {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        border: 1px solid #e4e7ed;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.3s;

        &:hover {
          border-color: #409eff;
          background: rgba(64, 158, 255, 0.05);
        }

        &.selected {
          border-color: #409eff;
          background: rgba(64, 158, 255, 0.1);
        }

        .port-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          background: #f5f7fa;
          border-radius: 6px;
        }

        .port-info {
          flex: 1;
          display: flex;
          flex-direction: column;

          .port-name {
            font-weight: 500;
            color: #303133;
          }

          .port-description {
            font-size: 12px;
            color: #909399;
          }
        }

        .port-status {
          flex-shrink: 0;
        }
      }
    }

    .custom-port {
      .el-input {
        width: 100%;
      }
    }
  }

  .connection-params {
    margin-bottom: 20px;

    h5 {
      margin: 0 0 12px;
      color: #303133;
      font-size: 16px;
    }

    .params-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;

      .el-input,
      .el-select {
        width: 100%;
      }
    }
  }

  .test-connection {
    display: flex;
    align-items: center;
    gap: 12px;

    .test-result {
      font-size: 14px;
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
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .port-assignment-dialog {
    .connection-params {
      .params-grid {
        grid-template-columns: 1fr;
      }
    }
  }
}
</style>