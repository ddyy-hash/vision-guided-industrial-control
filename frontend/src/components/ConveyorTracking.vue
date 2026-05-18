<template>
  <div class="conveyor-tracking">
    <div class="tracking-control">
      <h3>传送带物体追踪</h3>

      <div class="control-buttons">
        <el-button
          type="primary"
          @click="startTracking"
          :loading="isStarting"
          :disabled="isTracking"
        >
          <el-icon><VideoPlay /></el-icon>
          开始追踪
        </el-button>

        <el-button
          type="danger"
          @click="stopTracking"
          :disabled="!isTracking"
        >
          <el-icon><VideoPause /></el-icon>
          停止追踪
        </el-button>

        <el-button
          type="info"
          @click="getCurrentStatus"
        >
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>

        <el-button
          type="warning"
          @click="testVideoStream"
          :disabled="!isTracking"
        >
          <el-icon><VideoCamera /></el-icon>
          测试视频流
        </el-button>
      </div>

      <div class="status-display" v-if="trackingStatus">
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="追踪状态">
            <el-tag :type="isTracking ? 'success' : 'info'">
              {{ isTracking ? '运行中' : '已停止' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="WebSocket">
            <el-tag :type="webSocketConnected ? 'success' : 'danger'">
              {{ webSocketConnected ? '已连接' : '未连接' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="功能状态">
            <el-tag :type="trackingStatus.tracking_enabled ? 'success' : 'warning'">
              {{ trackingStatus.tracking_enabled ? '可用' : '模拟模式' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="FPS">
            {{ trackingStatus.fps.toFixed(1) }}
          </el-descriptions-item>
          <el-descriptions-item label="处理时间">
            {{ trackingStatus.processing_time.toFixed(1) }}ms
          </el-descriptions-item>
          <el-descriptions-item label="追踪物体数">
            {{ trackingStatus.active_tracks }}
          </el-descriptions-item>
          <el-descriptions-item label="总帧数">
            {{ trackingStatus.frame_count }}
          </el-descriptions-item>
          <el-descriptions-item label="检测总数">
            {{ trackingStatus.detection_count }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>

    <div class="video-stream">
      <div class="video-container">
        <div class="video-display" v-if="isTracking && (currentFrame || videoStreamAvailable)">
          <img
            :src="currentFrame"
            alt="摄像头画面"
            class="video-frame"
            @error="handleVideoError"
          />

          <div class="detection-overlay">
            <div class="detection-info">
              <span>实时检测中</span>
              <span>{{ trackedObjects.length }} 个物体</span>
              <span class="fps-display" v-if="frameRate > 0">FPS: {{ frameRate.toFixed(1) }}</span>
              <span v-if="trackingStatus && !trackingStatus.tracking_enabled" class="simulation-badge">模拟</span>
            </div>
          </div>
        </div>

        <div class="video-simulation" v-else-if="isTracking && !currentFrame && !videoStreamAvailable">
          <div class="conveyor-belt">
            <div
              v-for="obj in trackedObjects"
              :key="obj.track_id"
              class="tracked-object"
              :style="getObjectStyle(obj)"
              :class="getObjectClass(obj)"
            >
              <div class="object-id">ID: {{ obj.track_id }}</div>
              <div class="object-type">{{ getObjectTypeText(obj) }}</div>
              <div class="object-info">
                X: {{ obj.conveyor_x.toFixed(2) }}m
              </div>
            </div>
          </div>

          <div class="belt-frame"></div>

          <div class="simulation-notice" v-if="trackingStatus && !trackingStatus.tracking_enabled">
            <el-alert
              title="模拟模式"
              description="当前为模拟数据演示"
              type="warning"
              :closable="false"
              show-icon
            />
          </div>
        </div>

        <div class="video-placeholder" v-else>
          <el-icon size="48"><VideoCamera /></el-icon>
          <p>点击"开始追踪"启动物体检测</p>
          <div class="feature-status" v-if="trackingStatus && !trackingStatus.tracking_enabled">
            <el-alert
              title="追踪功能当前不可用"
              description="系统正在使用模拟模式进行演示"
              type="warning"
              :closable="false"
              show-icon
            />
          </div>
        </div>
      </div>
    </div>

    <div class="objects-panel" v-if="trackedObjects.length > 0">
      <h4>追踪物体列表</h4>
      <el-table :data="trackedObjects" style="width: 100%" max-height="300">
        <el-table-column prop="track_id" label="ID" width="60" />
        <el-table-column prop="class_name" label="类别" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="getClassTagType(row.class_name)">
              {{ getClassDisplayName(row.class_name) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="conveyor_x" label="X坐标(m)" width="100">
          <template #default="{ row }">
            {{ row.conveyor_x.toFixed(3) }}
          </template>
        </el-table-column>
        <el-table-column prop="conveyor_y" label="Y坐标(m)" width="100">
          <template #default="{ row }">
            {{ row.conveyor_y.toFixed(3) }}
          </template>
        </el-table-column>
        <el-table-column prop="velocity" label="速度(m/s)" width="100">
          <template #default="{ row }">
            {{ row.velocity.toFixed(3) }}
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            <el-progress
              :percentage="row.confidence * 100"
              :stroke-width="6"
              :color="getConfidenceColor(row.confidence)"
            />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="getObjectStatusType(row)">
              {{ getObjectStatus(row) }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
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
import { ref, onMounted, onBeforeUnmount } from 'vue';
import {
  VideoPlay, VideoPause, Refresh, VideoCamera
} from '@element-plus/icons-vue';
import { ElMessage, ElNotification } from 'element-plus';
import {
  startTracking,
  stopTracking,
  getCurrentObjects,
  getTrackingStatus,
  onObjectDetected,
  onObjectLost,
  onFrameProcessed,
  onTrackingStatus
} from '../api/trackingApi';

const isTracking = ref(false);
const isStarting = ref(false);
const trackedObjects = ref<any[]>([]);
const trackingStatus = ref<any>(null);
const eventLog = ref<any[]>([]);
const currentFrame = ref<string>('');
const showVideoStream = ref(false);
const videoStreamAvailable = ref(false);
const webSocketConnected = ref(false);

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

const startTrackingHandler = async () => {
  try {
    isStarting.value = true;
    const success = await startTracking(0);

    if (success) {
      isTracking.value = true;
      addLog('success', '物体追踪已启动');
      ElMessage.success('追踪服务已启动');
    } else {
      addLog('error', '追踪启动失败');
      ElMessage.error('追踪服务启动失败');
    }
  } catch (error) {
    addLog('error', `启动错误: ${error}`);
    ElMessage.error('启动追踪失败');
  } finally {
    isStarting.value = false;
  }
};

const stopTrackingHandler = async () => {
  try {
    const success = await stopTracking();

    if (success) {
      isTracking.value = false;
      trackedObjects.value = [];
      addLog('info', '物体追踪已停止');
      ElMessage.info('追踪服务已停止');
    } else {
      addLog('error', '停止追踪失败');
      ElMessage.error('停止追踪失败');
    }
  } catch (error) {
    addLog('error', `停止错误: ${error}`);
    ElMessage.error('停止追踪失败');
  }
};

const getCurrentStatus = async () => {
  try {
    const status = await getTrackingStatus();
    if (status) {
      trackingStatus.value = status;
      isTracking.value = status.is_running;
    }

    const objects = await getCurrentObjects();
    trackedObjects.value = objects;

    addLog('info', '状态已刷新');
  } catch (error) {
    addLog('error', `刷新状态失败: ${error}`);
  }
};

const testVideoStream = async () => {
  try {
    addLog('info', '正在测试视频流...');
    const response = await fetch('http://localhost:5000/api/tracking/frame?type=raw');
    const result = await response.json();

    if (result.success && result.data.frame) {
      currentFrame.value = result.data.frame;
      videoStreamAvailable.value = true;
      addLog('success', `视频流测试成功 - 帧大小: ${result.data.frame.length} 字符`);
      ElMessage.success('视频流测试成功');
    } else {
      addLog('error', '视频流测试失败: ' + (result.message || '无数据'));
      ElMessage.error('视频流测试失败');
    }
  } catch (error) {
    addLog('error', `视频流测试错误: ${error}`);
    ElMessage.error('视频流测试失败');
  }
};

const getObjectStyle = (obj: any) => {
  const left = (obj.conveyor_x / 0.6) * 100;
  const top = (obj.conveyor_y / 0.4) * 100;

  return {
    left: `${left}%`,
    top: `${top}%`,
    transform: 'translate(-50%, -50%)'
  };
};

const getObjectClass = (obj: any) => {
  return {
    [obj.class_name || 'unknown']: true,
    'high-confidence': obj.confidence > 0.8,
    'medium-confidence': obj.confidence > 0.5 && obj.confidence <= 0.8,
    'low-confidence': obj.confidence <= 0.5
  };
};

const getConfidenceColor = (confidence: number) => {
  if (confidence > 0.8) return '#67c23a';
  if (confidence > 0.5) return '#e6a23c';
  return '#f56c6c';
};

const getObjectStatusType = (obj: any) => {
  if (obj.velocity > 0.1) return 'warning';
  if (obj.confidence < 0.5) return 'danger';
  return 'success';
};

const getObjectStatus = (obj: any) => {
  if (obj.velocity > 0.1) return '运动中';
  if (obj.confidence < 0.5) return '低置信';
  return '稳定';
};

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN');
};

const handleVideoError = () => {
  addLog('error', '视频流加载失败，切换到模拟模式');
  currentFrame.value = '';
};

const getObjectTypeText = (obj: any) => {
  return getClassDisplayName(obj.class_name);
};

const getClassDisplayName = (className: string) => {
  const nameMap: { [key: string]: string } = {
    'brick': '砖块',
    'arm': '机械臂',
    'unknown': '未知'
  };
  return nameMap[className] || className;
};

const getClassTagType = (className: string) => {
  const typeMap: { [key: string]: string } = {
    'brick': 'success',
    'arm': 'warning',
    'unknown': 'info'
  };
  return typeMap[className] || 'info';
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

    trackingAPI.on('socket_reconnected', (data) => {
      addLog('success', `WebSocket重新连接成功 - 尝试次数: ${data.attempts}`);
      webSocketConnected.value = true;
    });
  }).catch(error => {
    addLog('error', `注册WebSocket连接事件失败: ${error}`);
  });

  onObjectDetected((data: any) => {
    const obj = data.object;
    const className = obj.class_name || '未知';
    addLog('success', `检测到新${getClassDisplayName(className)}: ID ${obj.track_id}`);
  });

  onObjectLost((data: any) => {
    const obj = data.object;
    const className = obj.class_name || '未知';
    addLog('warning', `${getClassDisplayName(className)}丢失: ID ${obj.track_id}`);
  });

  onFrameProcessed((data: any) => {
    addLog('info', `收到帧处理事件 - 帧ID: ${data.frame_data?.frame_id || '未知'}`);
    if (data.frame_data && data.frame_data.tracked_objects) {
      trackedObjects.value = data.frame_data.tracked_objects;
      addLog('info', `更新追踪物体 - 数量: ${data.frame_data.tracked_objects.length}`);
    }
  });


  onTrackingStatus((data: any) => {
    if (data.status === 'error') {
      addLog('error', `追踪错误: ${data.message}`);
    }
  });

  addLog('info', 'WebSocket事件处理设置完成');
};

const handleVideoFrame = (data: any) => {
  if (data.frame) {
    requestAnimationFrame(() => {
      currentFrame.value = data.frame;
      videoStreamAvailable.value = true;
      updateLastFrameTime();

      if (Math.random() < 0.05) {
        addLog('info', `收到视频帧 - 大小: ${data.frame.length} 字符`);
      }
    });
  } else {
    addLog('warning', '收到视频帧事件但无帧数据');
    videoStreamAvailable.value = false;
  }
};

const lastFrameTime = ref(Date.now());

const updateLastFrameTime = () => {
  lastFrameTime.value = Date.now();
};

const frameRate = ref(0);
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

  import('../api/trackingApi').then(({ onVideoFrame }) => {
    onVideoFrame(handleVideoFrame);
    addLog('info', '视频帧事件监听器已注册');
  }).catch(error => {
    addLog('error', `注册视频帧事件监听器失败: ${error}`);
  });

  getCurrentStatus();

  const interval = setInterval(() => {
    if (isTracking.value) {
      getCurrentStatus();
    }
  }, 2000);

  const videoCheckInterval = setInterval(() => {
    if (isTracking.value && !currentFrame.value && Date.now() - lastFrameTime.value > 3000) {
      addLog('warning', '视频流超过3秒未更新，可能存在问题');
      testVideoStream();
    }

    if (isTracking.value && currentFrame.value) {
      updateFrameRate();
    }
  }, 5000);

  onBeforeUnmount(() => {
    clearInterval(interval);
    clearInterval(videoCheckInterval);
  });
});
</script>

<style scoped lang="scss">
.conveyor-tracking {
  padding: 20px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  height: 100%;
  display: flex;
  flex-direction: column;

  .tracking-control {
    margin-bottom: 20px;

    h3 {
      margin-top: 0;
      color: #409eff;
      margin-bottom: 15px;
    }

    .control-buttons {
      display: flex;
      gap: 10px;
      margin-bottom: 15px;
    }

    .status-display {
      background: rgba(0, 0, 0, 0.2);
      padding: 10px;
      border-radius: 4px;
    }
  }

  .video-stream {
    flex: 1;
    margin-bottom: 20px;

    .video-container {
      position: relative;
      width: 100%;
      height: 300px;
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
          image-rendering: -webkit-optimize-contrast;
          image-rendering: crisp-edges;
          transform: translateZ(0);
        }
      }

      .video-simulation {
        position: relative;
        width: 100%;
        height: 100%;

        .conveyor-belt {
          position: absolute;
          top: 10%;
          left: 10%;
          width: 80%;
          height: 80%;
          background: linear-gradient(90deg, #333 0%, #555 50%, #333 100%);
          border: 2px solid #666;
          border-radius: 4px;
        }

        .belt-frame {
          position: absolute;
          top: 10%;
          left: 10%;
          width: 80%;
          height: 80%;
          border: 3px solid #409eff;
          border-radius: 4px;
          pointer-events: none;
        }

        .tracked-object {
          position: absolute;
          width: 50px;
          height: 50px;
          background: #67c23a;
          border: 2px solid #fff;
          border-radius: 8px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 10px;
          font-weight: bold;
          transition: all 0.3s ease;

          &.brick {
            background: #67c23a;
            border-color: #85ce61;
            &.high-confidence {
              background: #67c23a;
              box-shadow: 0 0 15px rgba(103, 194, 58, 0.7);
            }
            &.medium-confidence {
              background: #e6a23c;
              box-shadow: 0 0 10px rgba(230, 162, 60, 0.5);
            }
            &.low-confidence {
              background: #f56c6c;
              box-shadow: 0 0 10px rgba(245, 108, 108, 0.5);
            }
          }

          &.arm {
            background: #409eff;
            border-color: #79bbff;
            border-radius: 25px;
            &.high-confidence {
              background: #409eff;
              box-shadow: 0 0 15px rgba(64, 158, 255, 0.7);
            }
            &.medium-confidence {
              background: #e6a23c;
              box-shadow: 0 0 10px rgba(230, 162, 60, 0.5);
            }
            &.low-confidence {
              background: #f56c6c;
              box-shadow: 0 0 10px rgba(245, 108, 108, 0.5);
            }
          }

          .object-id {
            font-size: 11px;
            margin-bottom: 2px;
          }

          .object-type {
            font-size: 9px;
            margin-bottom: 2px;
            font-weight: normal;
            opacity: 0.9;
          }

          .object-info {
            font-size: 8px;
            opacity: 0.8;
          }
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
        }
      }

      .feature-status {
        margin-top: 10px;
        width: 100%;
      }

      .simulation-notice {
        position: absolute;
        top: 10px;
        right: 10px;
        width: 200px;
      }
    }
  }

  .objects-panel {
    margin-bottom: 20px;

    h4 {
      margin-top: 0;
      margin-bottom: 10px;
      color: #67c23a;
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
</style>