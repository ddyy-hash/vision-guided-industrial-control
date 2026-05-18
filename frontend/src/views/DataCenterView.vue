<template>
  <div class="datacenter-screen">
    <div class="header">
      <div class="title">
        <h1>工业数采控制平台数据中心</h1>
        <div class="subtitle">工业控制系统参赛队 | 基于HongZOS国产工业操作系统</div>
      </div>
      <div class="info">
        <span>系统运行: 124小时</span>
        <span>最后更新: {{ currentTime }}</span>
      </div>
    </div>

    <div class="main-grid">
      <div class="card full-width">
        <h2><el-icon><DataLine /></el-icon> 生产流程全景</h2>
        <div class="production-flow">
          <div class="stage" v-for="stage in productionStages" :key="stage.id">
            <div class="icon" :class="stage.status">
              <el-icon :size="30"><component :is="stage.icon" /></el-icon>
            </div>
            <div class="name">{{ stage.name }}</div>
            <div class="metric">{{ stage.metric }}</div>
          </div>
          <div class="flow-connector" v-for="n in 3" :key="`connector-${n}`"></div>
        </div>
      </div>

      <div class="card">
        <h2><el-icon><Monitor /></el-icon> 设备健康监测</h2>
        <div class="health-matrix">
          <div
            v-for="device in devices"
            :key="device.id"
            class="health-cell"
            :class="device.status"
          >
            <div class="name">{{ device.name }}</div>
            <div class="status-indicator"></div>
          </div>
        </div>
      </div>

      <div class="card">
        <h2><el-icon><PieChart /></el-icon> 质量分析</h2>
        <div class="chart-container">
          <div class="chart-placeholder">
            <el-icon size="48"><PieChart /></el-icon>
            <p>质量分析图表</p>
            <p class="chart-subtitle">合格率: 92.7%</p>
          </div>
        </div>
      </div>

      <div class="card">
        <h2><el-icon><DataAnalysis /></el-icon> 能耗监测</h2>
        <div class="chart-container">
          <div class="chart-placeholder">
            <el-icon size="48"><DataAnalysis /></el-icon>
            <p>能耗监测图表</p>
            <p class="chart-subtitle">总功耗: 9.2 kW/h</p>
          </div>
        </div>
      </div>

      <div class="card full-width">
        <h2><el-icon><Bell /></el-icon> 实时报警</h2>
        <el-table :data="alerts" height="200" style="width: 100%">
          <el-table-column prop="time" label="时间" width="120" />
          <el-table-column prop="device" label="设备" width="120" />
          <el-table-column prop="message" label="报警信息" />
          <el-table-column label="级别" width="100">
            <template #default="{ row }">
              <el-tag :type="row.level === 'high' ? 'danger' : 'warning'">
                {{ row.level === 'high' ? '严重' : '警告' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="footer">
      <div class="logo">
        <img src="../assets/logo.png" alt="工业控制平台" height="40">
        <span>国产工业操作系统创新实验室</span>
      </div>
      <div class="contact">
        <span>技术支持: 平台维护团队</span>
        <span>系统版本: v1.0.0</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import {
  DataLine, Monitor, PieChart, DataAnalysis, Bell
} from '@element-plus/icons-vue';

const currentTime = ref('');

const productionStages = ref([
  { id: 1, name: '机械臂组装', icon: 'Cpu', metric: '24件/小时', status: 'normal' },
  { id: 2, name: '传送运输', icon: 'Promotion', metric: '98% 正常', status: 'normal' },
  { id: 3, name: '视觉检测', icon: 'Camera', metric: '92.7% 合格', status: 'normal' },
  { id: 4, name: '产品入库', icon: 'Box', metric: '1200件', status: 'normal' }
]);

const devices = ref([
  { id: 1, name: '机械臂#1', status: 'normal' },
  { id: 2, name: '传送带#1', status: 'normal' },
  { id: 3, name: '视觉#1', status: 'normal' },
  { id: 4, name: '温度#1', status: 'normal' },
  { id: 5, name: '机械臂#2', status: 'warning' },
  { id: 6, name: 'PLC主控', status: 'normal' },
  { id: 7, name: '压力#1', status: 'normal' },
  { id: 8, name: '传送带#2', status: 'normal' }
]);

const alerts = ref([
  { id: 1, time: '09:23:45', device: '传送带#1', message: '电机温度过高 (68°C)', level: 'high' },
  { id: 2, time: '09:15:30', device: '视觉#1', message: '检测置信度低于阈值', level: 'medium' },
  { id: 3, time: '08:56:12', device: '机械臂#2', message: '关节3响应延迟', level: 'medium' }
]);

function updateTime() {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  });
}

function simulateDeviceStatus() {
  devices.value.forEach(device => {
    if (Math.random() > 0.9) {
      device.status = 'warning';
    } else if (Math.random() > 0.95) {
      device.status = 'danger';
    } else {
      device.status = 'normal';
    }
  });
}

function addRandomAlert() {
  if (Math.random() > 0.7) {
    const devices = ['机械臂#1', '传送带#1', '视觉#1', '温度#1'];
    const messages = [
      '电机温度过高 (68°C)',
      '检测置信度低于阈值',
      '关节3响应延迟',
      '传送带速度异常'
    ];

    const newAlert = {
      id: Date.now(),
      time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'}),
      device: devices[Math.floor(Math.random() * devices.length)],
      message: messages[Math.floor(Math.random() * messages.length)],
      level: Math.random() > 0.7 ? 'high' : 'medium'
    };

    alerts.value.unshift(newAlert);
    if (alerts.value.length > 10) {
      alerts.value.pop();
    }
  }
}

onMounted(() => {
  console.log('DataCenterView 组件已挂载');
  updateTime();
  setInterval(updateTime, 60000);

  setInterval(() => {
    simulateDeviceStatus();
    addRandomAlert();
  }, 5000);
});
</script>

<style scoped lang="scss">
.datacenter-screen {
  min-height: 100vh;
  background: #0a0e23;
  color: #fff;
  font-family: 'Microsoft YaHei', sans-serif;
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow: auto;

  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 20px;
    flex-shrink: 0;

    .title {
      h1 {
        margin: 0;
        font-size: 28px;
        background: linear-gradient(90deg, #1a6dff, #00e0ff);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
      }

      .subtitle {
        font-size: 16px;
        color: rgba(255, 255, 255, 0.7);
      }
    }

    .info {
      display: flex;
      gap: 20px;
      font-size: 16px;
      color: rgba(255, 255, 255, 0.7);
    }
  }

  .main-grid {
    flex: 1;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    grid-template-rows: auto auto auto;
    gap: 20px;
    min-height: 0;

    .card {
      background: rgba(255, 255, 255, 0.03);
      border-radius: 8px;
      padding: 15px;
      border: 1px solid rgba(255, 255, 255, 0.05);
      min-height: 0;
      overflow: hidden;

      &.full-width {
        grid-column: span 4;
      }

      h2 {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 0;
        margin-bottom: 15px;
        font-size: 18px;
        color: #1a9fff;

        .el-icon {
          color: #1a9fff;
        }
      }
    }

    .production-flow {
      display: flex;
      justify-content: space-around;
      align-items: center;
      min-height: 120px;
      position: relative;

      .stage {
        display: flex;
        flex-direction: column;
        align-items: center;
        z-index: 2;

        .icon {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(26, 159, 255, 0.1);
          border: 2px solid #1a9fff;

          &.warning {
            background: rgba(250, 173, 20, 0.1);
            border-color: #faad14;
          }

          &.danger {
            background: rgba(255, 77, 79, 0.1);
            border-color: #ff4d4f;
          }
        }

        .name {
          margin-top: 8px;
          font-size: 14px;
        }

        .metric {
          margin-top: 4px;
          font-size: 12px;
          color: rgba(255, 255, 255, 0.7);
        }
      }

      .flow-connector {
        position: absolute;
        height: 2px;
        width: 18%;
        background: linear-gradient(90deg, #1a9fff, transparent);
        top: 30px;

        &:nth-child(5) { left: 10%; }
        &:nth-child(6) { left: 36%; }
        &:nth-child(7) { left: 62%; }
      }
    }

    .health-matrix {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;

      .health-cell {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 12px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 80px;
        position: relative;
        overflow: hidden;

        &::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 4px;
        }

        &.normal::before {
          background: #52c41a;
        }

        &.warning::before {
          background: #faad14;
        }

        &.danger::before {
          background: #ff4d4f;
        }

        .name {
          font-size: 14px;
          margin-bottom: 8px;
        }

        .status-indicator {
          width: 10px;
          height: 10px;
          border-radius: 50%;
        }

        &.normal .status-indicator {
          background: #52c41a;
          box-shadow: 0 0 8px #52c41a;
        }

        &.warning .status-indicator {
          background: #faad14;
          box-shadow: 0 0 8px #faad14;
        }

        &.danger .status-indicator {
          background: #ff4d4f;
          box-shadow: 0 0 8px #ff4d4f;
        }
      }
    }

    .chart-container {
      min-height: 200px;
      display: flex;
      align-items: center;
      justify-content: center;

      .chart-placeholder {
        text-align: center;
        color: rgba(255, 255, 255, 0.6);

        .el-icon {
          margin-bottom: 10px;
        }

        p {
          margin: 5px 0;
          font-size: 14px;
        }

        .chart-subtitle {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.4);
        }
      }
    }
  }

  .footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 15px;
    margin-top: 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.6);
    font-size: 14px;
    flex-shrink: 0;

    .logo {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .contact {
      display: flex;
      gap: 20px;
    }
  }
}

:deep(.el-table) {
  background: transparent;

  th, tr {
    background: transparent !important;
  }

  th {
    color: rgba(255, 255, 255, 0.7);
    font-weight: normal;
  }

  td {
    color: #fff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  &::before {
    display: none;
  }

  .el-table__inner-wrapper::before {
    display: none;
  }
}
</style>