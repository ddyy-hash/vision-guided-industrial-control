<template>
  <div class="realtime-energy-detection-container">
    <h1 class="title">实时能效标签识别</h1>

    <div class="app-container">
      <div class="control-panel">
        <div class="control-buttons">
          <el-button
            type="primary"
            @click="startRealtimeDetection"
            :loading="isStarting"
            :disabled="isDetecting"
          >
            <el-icon><VideoPlay /></el-icon>
            开始实时检测
          </el-button>

          <el-button
            type="danger"
            @click="stopRealtimeDetection"
            :disabled="!isDetecting"
          >
            <el-icon><VideoPause /></el-icon>
            停止检测
          </el-button>

          <el-button
            type="info"
            @click="getDetectionStatus"
          >
            <el-icon><Refresh /></el-icon>
            刷新状态
          </el-button>
        </div>

        <div class="status-display" v-if="detectionStatus">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="检测状态">
              <el-tag :type="isDetecting ? 'success' : 'info'">
                {{ isDetecting ? '运行中' : '已停止' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="WebSocket">
              <el-tag :type="webSocketConnected ? 'success' : 'danger'">
                {{ webSocketConnected ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="总帧数">
              {{ detectionStatus.frame_count || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="检测次数">
              {{ detectionStatus.detection_count || 0 }}
            </el-descriptions-item>
            <el-descriptions-item label="检测间隔">
              {{ detectionStatus.detection_interval || 0 }}秒
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <div class="detection-area">
        <div class="video-and-results">
          <div class="video-stream">
            <div class="video-container">
              <div class="video-display" v-if="isDetecting && (currentFrame || videoStreamAvailable)">
                <img
                  :src="currentFrame"
                  alt="实时摄像头画面"
                  class="video-frame"
                  @error="handleVideoError"
                />

                <div class="detection-overlay">
                  <div class="detection-info">
                    <span>实时能效检测中</span>
                    <span class="fps-display" v-if="frameRate > 0">FPS: {{ frameRate.toFixed(1) }}</span>
                    <span class="detection-count">检测次数: {{ detectionCount }}</span>
                    <span v-if="detectionStatus && detectionStatus.simulated" class="simulation-badge">模拟</span>
                  </div>
                </div>
              </div>

              <div class="video-placeholder" v-else>
                <el-icon size="48"><VideoCamera /></el-icon>
                <p>点击"开始实时检测"启动能效标签识别</p>
                <p class="hint">系统将自动从视频流中识别能效等级</p>
              </div>
            </div>
          </div>

          <div class="real-time-results">
            <div class="results-header">
              <h3>实时检测结果</h3>
              <el-button
                size="small"
                @click="clearResults"
                :disabled="detectionResults.length === 0"
              >
                清空结果
              </el-button>
            </div>

            <div class="latest-result" v-if="latestResult">
              <div class="result-card" :class="getEnergyLevelClass(latestResult.energy_level)">
                <div class="result-header">
                  <span class="result-time">{{ formatTime(latestResult.timestamp) }}</span>
                  <el-tag :type="latestResult.success ? 'success' : 'danger'">
                    {{ latestResult.success ? '成功' : '失败' }}
                  </el-tag>
                </div>
                <div class="energy-level">
                  <span class="level-label">能效等级:</span>
                  <span class="level-value">{{ getEnergyLevelDisplay(latestResult.energy_level) }}</span>
                </div>
                <div class="confidence" v-if="latestResult.confidence > 0">
                  置信度: {{ (latestResult.confidence * 100).toFixed(1) }}%
                </div>
                <div class="ocr-text" v-if="latestResult.ocr_text">
                  {{ latestResult.ocr_text }}
                </div>
              </div>
            </div>

            <div class="results-list">
              <el-table
                :data="detectionResults"
                style="width: 100%"
                max-height="300"
                empty-text="暂无检测结果"
              >
                <el-table-column prop="timestamp" label="时间" width="120">
                  <template #default="{ row }">
                    {{ formatTimeShort(row.timestamp) }}
                  </template>
                </el-table-column>
                <el-table-column prop="energy_level" label="能效等级" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getEnergyLevelTagType(row.energy_level)">
                      {{ getEnergyLevelDisplay(row.energy_level) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="confidence" label="置信度" width="100">
                  <template #default="{ row }">
                    <el-progress
                      v-if="row.confidence > 0"
                      :percentage="row.confidence * 100"
                      :stroke-width="6"
                      :color="getConfidenceColor(row.confidence)"
                      :show-text="false"
                    />
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="ocr_text" label="识别文本" min-width="150" show-overflow-tooltip>
                  <template #default="{ row }">
                    {{ row.ocr_text || '-' }}
                  </template>
                </el-table-column>
                <el-table-column label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.success ? 'success' : 'danger'">
                      {{ row.success ? '成功' : '失败' }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </div>

      <div class="statistics-panel" v-if="detectionResults.length > 0">
        <h3>检测统计</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-value">{{ detectionResults.length }}</div>
            <div class="stat-label">总检测次数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ successfulDetections }}</div>
            <div class="stat-label">成功检测</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ successRate }}%</div>
            <div class="stat-label">成功率</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ latestEnergyLevel }}</div>
            <div class="stat-label">最新等级</div>
          </div>
        </div>

        <div class="energy-distribution">
          <h4>能效等级分布</h4>
          <div class="distribution-bars">
            <div
              v-for="(count, level) in energyLevelDistribution"
              :key="level"
              class="distribution-bar"
            >
              <div class="bar-label">{{ getEnergyLevelDisplay(level) }}</div>
              <div class="bar-container">
                <div
                  class="bar-fill"
                  :style="{ width: getDistributionPercentage(count) + '%' }"
                  :class="getEnergyLevelClass(level)"
                ></div>
              </div>
              <div class="bar-count">{{ count }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="event-log">
      <h4>事件日志</h4>
      <div class="log-container">
        <div
          v-for="(event, index) in eventLog"
          :key="index"
          class="log-item"
          :class="`log-${event.type}`"
        >
          <span class="log-time">{{ formatTime(event.timestamp) }}</span>
          <span class="log-message">{{ event.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import {
  VideoPlay, VideoPause, Refresh, VideoCamera
} from '@element-plus/icons-vue';
import { ElMessage, ElNotification } from 'element-plus';

const isDetecting = ref(false);
const isStarting = ref(false);
const detectionStatus = ref<any>(null);
const detectionResults = ref<any[]>([]);
const eventLog = ref<any[]>([]);
const currentFrame = ref<string>('');
const videoStreamAvailable = ref(false);
const webSocketConnected = ref(false);
const frameRate = ref(0);
const detectionCount = ref(0);

const latestResult = computed(() => {
  return detectionResults.value.length > 0 ? detectionResults.value[detectionResults.value.length - 1] : null;
});

const successfulDetections = computed(() => {
  return detectionResults.value.filter(r => r.success).length;
});

const successRate = computed(() => {
  return detectionResults.value.length > 0
    ? Math.round((successfulDetections.value / detectionResults.value.length) * 100)
    : 0;
});

const latestEnergyLevel = computed(() => {
  return latestResult.value ? getEnergyLevelDisplay(latestResult.value.energy_level) : '-';
});

const energyLevelDistribution = computed(() => {
  const distribution: { [key: string]: number } = {};
  detectionResults.value
    .filter(r => r.success)
    .forEach(r => {
      const level = r.energy_level || '未知';
      distribution[level] = (distribution[level] || 0) + 1;
    });
  return distribution;
});

const addLog = (type: string, message: string) => {
  const timestamp = new Date().toLocaleTimeString('zh-CN');
  eventLog.value.unshift({
    type,
    message,
    timestamp
  });

  if (eventLog.value.length > 50) {
    eventLog.value = eventLog.value.slice(0, 50);
  }
};

const startRealtimeDetection = async () => {
  try {
    isStarting.value = true;

    const response = await fetch('http://localhost:5000/api/realtime/control', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        action: 'start',
        camera_source: 0
      })
    });

    const result = await response.json();

    if (result.success) {
      isDetecting.value = true;
      addLog('success', '实时能效检测已启动');
      ElMessage.success('实时检测服务已启动');
    } else {
      addLog('error', '检测启动失败: ' + result.message);
      ElMessage.error('检测启动失败');
    }
  } catch (error) {
    addLog('error', `启动错误: ${error}`);
    ElMessage.error('启动实时检测失败');
  } finally {
    isStarting.value = false;
  }
};

const stopRealtimeDetection = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/realtime/control', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        action: 'stop'
      })
    });

    const result = await response.json();

    if (result.success) {
      isDetecting.value = false;
      addLog('info', '实时能效检测已停止');
      ElMessage.info('检测服务已停止');
    } else {
      addLog('error', '停止检测失败: ' + result.message);
      ElMessage.error('停止检测失败');
    }
  } catch (error) {
    addLog('error', `停止错误: ${error}`);
    ElMessage.error('停止实时检测失败');
  }
};

const getDetectionStatus = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/realtime/status');
    const result = await response.json();

    if (result.success) {
      detectionStatus.value = result.data.status;
      isDetecting.value = result.data.status.is_running;
    }

    addLog('info', '状态已刷新');
  } catch (error) {
    addLog('error', `刷新状态失败: ${error}`);
  }
};

const clearResults = () => {
  detectionResults.value = [];
  detectionCount.value = 0;
  addLog('info', '检测结果已清空');
};

const handleVideoError = () => {
  addLog('error', '视频流加载失败');
  currentFrame.value = '';
};

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN');
};

const formatTimeShort = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

const getEnergyLevelDisplay = (level: string) => {
  const levelMap: { [key: string]: string } = {
    '1': '一级',
    '2': '二级',
    '3': '三级',
    '未知': '未知'
  };
  return levelMap[level] || level;
};

const getEnergyLevelClass = (level: string) => {
  const classMap: { [key: string]: string } = {
    '1': 'level-1',
    '2': 'level-2',
    '3': 'level-3'
  };
  return classMap[level] || 'level-unknown';
};

const getEnergyLevelTagType = (level: string) => {
  const typeMap: { [key: string]: string } = {
    '1': 'success',
    '2': 'warning',
    '3': 'danger'
  };
  return typeMap[level] || 'info';
};

const getConfidenceColor = (confidence: number) => {
  if (confidence > 0.8) return '#67c23a';
  if (confidence > 0.5) return '#e6a23c';
  return '#f56c6c';
};

const getDistributionPercentage = (count: number) => {
  const total = Object.values(energyLevelDistribution.value).reduce((sum, c) => sum + c, 0);
  return total > 0 ? (count / total) * 100 : 0;
};

const setupWebSocketHandlers = () => {
  addLog('info', '正在设置WebSocket事件处理...');

  import('../api/trackingApi').then(({ trackingAPI }) => {
    trackingAPI.on('socket_connected', (data) => {
      addLog('success', `WebSocket已连接 - ID: ${data.id}`);
      webSocketConnected.value = true;
    });

    trackingAPI.on('socket_disconnected', (data) => {
      addLog('warning', 'WebSocket已断开');
      webSocketConnected.value = false;
    });

    trackingAPI.on('socket_error', (data) => {
      addLog('error', `WebSocket错误: ${data.error}`);
      webSocketConnected.value = false;
    });
  }).catch(error => {
    addLog('error', `注册WebSocket连接事件失败: ${error}`);
  });

  import('../api/trackingApi').then(({ onRealtimeEnergyDetected, onRealtimeFrameCaptured }) => {
    onRealtimeEnergyDetected((data: any) => {
      const result = data.detection_result;
      detectionResults.value.push(result);
      detectionCount.value++;

      if (detectionResults.value.length > 100) {
        detectionResults.value = detectionResults.value.slice(-100);
      }

      addLog('success', `能效检测成功: ${getEnergyLevelDisplay(result.energy_level)}`);
    });

    onRealtimeFrameCaptured((data: any) => {
      if (data.frame_data && data.frame_data.has_frame) {
        updateLastFrameTime();
      }
    });

  }).catch(error => {
    addLog('error', `注册实时检测事件失败: ${error}`);
  });
};

const lastFrameTime = ref(Date.now());

const updateLastFrameTime = () => {
  lastFrameTime.value = Date.now();
};

const frameCount = ref(0);
const frameRateStartTime = ref(Date.now());

const updateFrameRate = () => {
  frameCount.value++;
  const currentTime = Date.now();
  const elapsed = (currentTime - frameRateStartTime.value) / 1000;

  if (elapsed >= 1) {
    frameRate.value = frameCount.value / elapsed;
    frameCount.value = 0;
    frameRateStartTime.value = currentTime;
  }
};

onMounted(() => {
  setupWebSocketHandlers();
  getDetectionStatus();

  const interval = setInterval(() => {
    if (isDetecting.value) {
      getDetectionStatus();
    }
  }, 3000);

  const videoCheckInterval = setInterval(() => {
    if (isDetecting.value && Date.now() - lastFrameTime.value > 5000) {
      addLog('warning', '视频流超过5秒未更新');
    }

    if (isDetecting.value) {
      updateFrameRate();
    }
  }, 1000);

  onBeforeUnmount(() => {
    clearInterval(interval);
    clearInterval(videoCheckInterval);

    if (isDetecting.value) {
      stopRealtimeDetection();
    }
  });
});
</script>

<style scoped lang="scss">
.realtime-energy-detection-container {
  padding: 20px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  height: 100%;
  display: flex;
  flex-direction: column;

  .title {
    margin-top: 0;
    margin-bottom: 20px;
    color: #409eff;
    text-align: center;
  }

  .app-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    flex: 1;
  }

  .control-panel {
    background: rgba(0, 0, 0, 0.2);
    padding: 15px;
    border-radius: 8px;

    .control-buttons {
      display: flex;
      gap: 10px;
      margin-bottom: 15px;
    }

    .status-display {
      background: rgba(0, 0, 0, 0.3);
      padding: 10px;
      border-radius: 4px;
    }
  }

  .detection-area {
    flex: 1;

    .video-and-results {
      display: flex;
      gap: 20px;
      height: 400px;

      .video-stream {
        flex: 2;

        .video-container {
          position: relative;
          width: 100%;
          height: 100%;
          background: #000;
          border-radius: 4px;
          overflow: hidden;

          .video-placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: rgba(255, 255, 255, 0.5);

            p {
              margin-top: 10px;
              font-size: 14px;
            }

            .hint {
              font-size: 12px;
              color: rgba(255, 255, 255, 0.4);
            }
          }

          .video-display {
            position: relative;
            width: 100%;
            height: 100%;

            .video-frame {
              width: 100%;
              height: 100%;
              object-fit: contain;
              background: #000;
            }
          }

          .detection-overlay {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;

            .detection-info {
              display: flex;
              gap: 15px;
              align-items: center;

              .simulation-badge {
                background: #e6a23c;
                color: white;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
              }

              .fps-display {
                color: #67c23a;
                font-weight: bold;
              }

              .detection-count {
                color: #409eff;
                font-weight: bold;
              }
            }
          }
        }
      }

      .real-time-results {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 15px;

        .results-header {
          display: flex;
          justify-content: space-between;
          align-items: center;

          h3 {
            margin: 0;
            color: #67c23a;
          }
        }

        .latest-result {
          .result-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid #6c757d;

            &.level-1 {
              border-left-color: #67c23a;
              background: rgba(103, 194, 58, 0.1);
            }

            &.level-2 {
              border-left-color: #e6a23c;
              background: rgba(230, 162, 60, 0.1);
            }

            &.level-3 {
              border-left-color: #f56c6c;
              background: rgba(245, 108, 108, 0.1);
            }

            .result-header {
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 10px;

              .result-time {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.6);
              }
            }

            .energy-level {
              display: flex;
              align-items: center;
              gap: 10px;
              margin-bottom: 8px;

              .level-label {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
              }

              .level-value {
                font-size: 18px;
                font-weight: bold;
                color: #fff;
              }
            }

            .confidence {
              font-size: 12px;
              color: rgba(255, 255, 255, 0.6);
              margin-bottom: 8px;
            }

            .ocr-text {
              font-size: 12px;
              color: rgba(255, 255, 255, 0.7);
              word-break: break-all;
            }
          }
        }

        .results-list {
          flex: 1;
        }
      }
    }
  }

  .statistics-panel {
    background: rgba(0, 0, 0, 0.2);
    padding: 15px;
    border-radius: 8px;

    h3 {
      margin-top: 0;
      margin-bottom: 15px;
      color: #409eff;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 15px;
      margin-bottom: 20px;

      .stat-item {
        text-align: center;
        padding: 10px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 6px;

        .stat-value {
          font-size: 24px;
          font-weight: bold;
          color: #409eff;
          margin-bottom: 5px;
        }

        .stat-label {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
        }
      }
    }

    .energy-distribution {
      h4 {
        margin-top: 0;
        margin-bottom: 10px;
        color: #67c23a;
      }

      .distribution-bars {
        .distribution-bar {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 8px;

          .bar-label {
            width: 60px;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.8);
          }

          .bar-container {
            flex: 1;
            height: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            overflow: hidden;

            .bar-fill {
              height: 100%;
              border-radius: 10px;
              transition: width 0.3s ease;

              &.level-1 {
                background: #67c23a;
              }

              &.level-2 {
                background: #e6a23c;
              }

              &.level-3 {
                background: #f56c6c;
              }

              &.level-unknown {
                background: #909399;
              }
            }
          }

          .bar-count {
            width: 30px;
            text-align: right;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.6);
          }
        }
      }
    }
  }

  .event-log {
    flex: 0 0 150px;

    h4 {
      margin-top: 0;
      margin-bottom: 10px;
      color: #e6a23c;
    }

    .log-container {
      height: 120px;
      overflow-y: auto;
      background: rgba(0, 0, 0, 0.3);
      border-radius: 4px;
      padding: 10px;

      .log-item {
        font-size: 12px;
        margin-bottom: 5px;
        display: flex;
        gap: 10px;

        .log-time {
          color: rgba(255, 255, 255, 0.6);
          white-space: nowrap;
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

@media (max-width: 768px) {
  .realtime-energy-detection-container {
    .detection-area .video-and-results {
      flex-direction: column;
      height: auto;
    }

    .statistics-panel .stats-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}
</style>