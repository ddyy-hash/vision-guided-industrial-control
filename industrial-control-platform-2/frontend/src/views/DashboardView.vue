<template>
  <div class="dashboard">
    <div class="status-bar">
      <div class="system-info">
        <span>HongZOS v2.1.4</span>
        <el-icon><Cpu /></el-icon>
        <span>CPU: 42%</span>
        <span>内存: 1.2G/4G</span>
      </div>

      <div class="time-info">
        <span>{{ currentTime }}</span>
        <el-icon><User /></el-icon>
        <span>操作员</span>
      </div>
    </div>

    <div class="main-content">
      <div class="equipment-panel">
        <h2><el-icon><Menu /></el-icon> 设备监控</h2>

        <EquipmentMonitor />

        <div class="quick-actions">
          <el-button type="danger" @click="emergencyStop">
            <el-icon><SwitchButton /></el-icon> 紧急停止
          </el-button>
          <el-button type="warning" @click="systemReset">
            <el-icon><Refresh /></el-icon> 系统复位
          </el-button>
        </div>
      </div>

      <div class="control-panel">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="机械臂控制" name="robot">
            <RobotArmController />
          </el-tab-pane>

          <el-tab-pane label="物体追踪" name="tracking">
            <ConveyorTracking />
          </el-tab-pane>

          <el-tab-pane label="传送带控制" name="conveyor">
            <ConveyorControlPanel />
          </el-tab-pane>

          <el-tab-pane label="视觉检测" name="vision">
            <div class="vision-control">
              <h3>实时能耗标签检测</h3>

              <div class="control-panel">
                <el-button
                  type="primary"
                  :icon="VideoPlay"
                  @click="startCamera"
                  :disabled="isCameraActive"
                >
                  开启摄像头
                </el-button>
                <el-button
                  type="danger"
                  :icon="VideoPause"
                  @click="stopCamera"
                  :disabled="!isCameraActive"
                >
                  关闭摄像头
                </el-button>
                <el-button
                  type="success"
                  :icon="Refresh"
                  @click="captureAndRecognize"
                  :disabled="!isCameraActive"
                >
                  单次识别
                </el-button>
                <el-button
                  type="warning"
                  :icon="VideoCamera"
                  @click="toggleAutoRecognition"
                  :class="{ 'auto-recognizing': isAutoRecognizing }"
                >
                  {{ isAutoRecognizing ? '停止自动识别' : '开始自动识别' }}
                </el-button>
              </div>

              <div class="video-container">
                <div class="video-feed">
                  <video
                    ref="videoElement"
                    autoplay
                    playsinline
                    :class="{ 'video-active': isCameraActive }"
                    @loadedmetadata="onVideoLoaded"
                  >
                    您的浏览器不支持视频播放
                  </video>
                  <div v-if="!isCameraActive" class="video-placeholder">
                    <el-icon :size="48"><VideoCamera /></el-icon>
                    <p>点击"开启摄像头"启动实时检测</p>
                  </div>

                  <div v-if="isCameraActive" class="detection-overlay">
                    <div class="detection-info">
                      <el-tag :type="detectionStatus.type">
                        {{ detectionStatus.message }}
                      </el-tag>
                      <div class="fps-counter" v-if="isAutoRecognizing">
                        自动识别中...
                      </div>
                    </div>
                  </div>
                </div>

                <div class="result-panel">
                  <h4>识别结果</h4>
                  <div v-if="currentResult" class="current-result">
                    <div class="result-card" :class="currentResult.confidence > 0.8 ? 'high-confidence' : 'medium-confidence'">
                      <div class="result-header">
                        <span class="confidence">置信度: {{ (currentResult.confidence * 100).toFixed(1) }}%</span>
                        <el-tag :type="currentResult.confidence > 0.8 ? 'success' : 'warning'">
                          {{ currentResult.confidence > 0.8 ? '高置信度' : '中置信度' }}
                        </el-tag>
                      </div>
                      <div class="result-content">
                        <div class="energy-level">
                          <strong>能效等级:</strong> {{ currentResult.energyLevel }}
                        </div>
                        <div class="product-info">
                          <strong>产品型号:</strong> {{ currentResult.model }}
                        </div>
                        <div class="manufacturer">
                          <strong>生产厂家:</strong> {{ currentResult.manufacturer }}
                        </div>
                        <div class="detection-time">
                          <strong>检测时间:</strong> {{ currentResult.detectionTime }}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="no-result">
                    <el-empty description="暂无识别结果" :image-size="80" />
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="自动化控制" name="automation">
            <AutomationController />
          </el-tab-pane>

        </el-tabs>
      </div>
    </div>

    <div class="data-bar">
      <div class="metric">
        <span>系统状态</span>
        <el-tag type="success">运行中</el-tag>
      </div>
      <div class="metric">
        <span>生产总数</span>
        <span>1,248</span>
      </div>
      <div class="metric">
        <span>合格率</span>
        <span>92.7%</span>
      </div>
      <div class="metric">
        <span>平均能耗</span>
        <span>3.2kW/h</span>
      </div>
      <div class="metric">
        <span>当前报警</span>
        <el-tag type="warning">传送带#1温度偏高</el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import {
  Cpu, User, Menu, SwitchButton, Refresh,
  VideoPlay, VideoPause, VideoCamera, Aim,
  Check, Warning, Close, Box
} from '@element-plus/icons-vue';
import EquipmentMonitor from '../components/EquipmentMonitor.vue';
import RobotArmController from '../components/RobotArmController.vue';
import AutomationController from '../components/AutomationController.vue';
import ConveyorTracking from '../components/ConveyorTracking.vue';
import ConveyorControlPanel from '../components/ConveyorControlPanel.vue';
import { ElMessageBox, ElNotification, ElMessage } from 'element-plus';

const currentTime = ref('');
const activeTab = ref('robot');

const detectionResult = ref(true);
const totalDetected = ref(1248);
const passRate = ref(92.7);

const videoElement = ref<HTMLVideoElement>();
const isCameraActive = ref(false);
const isAutoRecognizing = ref(false);
const currentResult = ref<any>(null);
const detectionStatus = ref({
  type: 'info',
  message: '系统就绪'
});

let videoStream: MediaStream | null = null;
let autoRecognitionInterval: ReturnType<typeof setInterval> | null = null;

const startCamera = async () => {
  try {
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'environment'
      }
    });

    if (videoElement.value) {
      videoElement.value.srcObject = videoStream;
      isCameraActive.value = true;
      detectionStatus.value = {
        type: 'success',
        message: '摄像头已开启'
      };

      ElNotification({
        title: '摄像头启动成功',
        message: '实时视频流已连接',
        type: 'success'
      });
    }
  } catch (error) {
    console.error('摄像头启动失败:', error);
    detectionStatus.value = {
      type: 'error',
      message: '摄像头启动失败'
    };

    ElNotification({
      title: '摄像头启动失败',
      message: '请检查摄像头权限和设备连接',
      type: 'error'
    });
  }
};

const stopCamera = () => {
  if (videoStream) {
    videoStream.getTracks().forEach(track => track.stop());
    videoStream = null;
  }

  if (videoElement.value) {
    videoElement.value.srcObject = null;
  }

  isCameraActive.value = false;
  isAutoRecognizing.value = false;
  currentResult.value = null;

  if (autoRecognitionInterval) {
    clearInterval(autoRecognitionInterval);
    autoRecognitionInterval = null;
  }

  detectionStatus.value = {
    type: 'info',
    message: '摄像头已关闭'
  };
};

const onVideoLoaded = () => {
  console.log('视频流已加载');
};

const captureAndRecognize = async () => {
  if (!videoElement.value || !isCameraActive.value) {
    ElMessage.warning('请先开启摄像头');
    return;
  }

  try {
    detectionStatus.value = {
      type: 'warning',
      message: '识别中...'
    };

    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) throw new Error('无法创建画布上下文');

    canvas.width = videoElement.value.videoWidth;
    canvas.height = videoElement.value.videoHeight;
    context.drawImage(videoElement.value, 0, 0);

    canvas.toBlob(async (blob) => {
      if (!blob) {
        throw new Error('无法捕获图像');
      }

      const formData = new FormData();
      formData.append('file', blob, 'capture.jpg');

      const response = await fetch('http://localhost:5000/api/energy/combined', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        currentResult.value = {
          energyLevel: result.energy_level || '未知',
          model: result.model || '未知',
          manufacturer: result.manufacturer || '未知',
          confidence: result.confidence || 0,
          detectionTime: new Date().toLocaleTimeString('zh-CN')
        };

        detectionStatus.value = {
          type: 'success',
          message: '识别成功'
        };

        ElNotification({
          title: '识别成功',
          message: `能效等级: ${currentResult.value.energyLevel}`,
          type: 'success'
        });
      } else {
        throw new Error(result.message || '识别失败');
      }
    }, 'image/jpeg', 0.8);

  } catch (error) {
    console.error('识别失败:', error);
    detectionStatus.value = {
      type: 'error',
      message: '识别失败'
    };

    ElNotification({
      title: '识别失败',
      message: error.message || '请检查后端服务',
      type: 'error'
    });
  }
};

const toggleAutoRecognition = () => {
  if (isAutoRecognizing.value) {
    if (autoRecognitionInterval) {
      clearInterval(autoRecognitionInterval);
      autoRecognitionInterval = null;
    }
    isAutoRecognizing.value = false;
    detectionStatus.value = {
      type: 'success',
      message: '自动识别已停止'
    };
  } else {
    if (!isCameraActive.value) {
      ElMessage.warning('请先开启摄像头');
      return;
    }

    isAutoRecognizing.value = true;
    detectionStatus.value = {
      type: 'warning',
      message: '自动识别中...'
    };

    autoRecognitionInterval = setInterval(() => {
      captureAndRecognize();
    }, 3000);

    ElNotification({
      title: '自动识别已启动',
      message: '每3秒自动识别一次',
      type: 'success'
    });
  }
};

onBeforeUnmount(() => {
  stopCamera();
});

function updateTime() {
  const now = new Date();
  currentTime.value = now.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

const updateConveyor = async () => {
  try {
    const result = await controlConveyor(conveyorSpeed.value, direction.value);
    if (!result.success) {
      throw new Error(result.message);
    }
    await fetchConveyorStatus();
  } catch (error) {
    errorMessage.value = error.message || '控制指令发送失败';
    console.error('控制传送带失败:', error);
  }
};

const fetchConveyorStatus = async () => {
  try {
    const status = await getConveyorStatus();
    if (status) {
      load.value = status.load || 0;
      temperature.value = status.temperature || 0;
      conveyorSpeed.value = status.speed || conveyorSpeed.value;
      direction.value = status.direction || direction.value;
    }
  } catch (error) {
    console.error('获取传送带状态失败:', error);
  }
};

const emergencyStop = () => {
  ElMessageBox.confirm('确定要紧急停止所有设备吗？', '警告', {
    confirmButtonText: '确认停止',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    conveyorSpeed.value = 0;
    await updateConveyor();
    ElNotification({
      title: '系统已紧急停止',
      message: '所有设备已停止运行',
      type: 'success'
    });
  });
};

const systemReset = () => {
  ElMessageBox.confirm('确定要复位系统吗？所有设备将恢复初始状态', '确认', {
    confirmButtonText: '确认复位',
    cancelButtonText: '取消',
    type: 'info'
  }).then(async () => {
    conveyorSpeed.value = 50;
    direction.value = 'forward';
    await updateConveyor();
    ElMessage.success('系统已复位');
  });
};

const getSpeedTagType = () => {
  if (conveyorSpeed.value > 80) return 'danger';
  if (conveyorSpeed.value > 50) return 'warning';
  return 'success';
};

const getTempColor = () => {
  if (temperature.value > 70) return '#f56c6c';
  if (temperature.value > 50) return '#e6a23c';
  return '#67c23a';
};

const getLoadColor = () => {
  if (load.value > 80) return '#f56c6c';
  if (load.value > 50) return '#e6a23c';
  return '#67c23a';
};

const formatTemp = () => {
  return `${temperature.value}°C`;
};

let dataInterval: ReturnType<typeof setInterval>;

onMounted(() => {
  updateTime();
  setInterval(updateTime, 1000);

  dataInterval = setInterval(() => {
    if (Math.random() > 0.8) {
      detectionResult.value = !detectionResult.value;
      totalDetected.value += 1;

      if (detectionResult.value) {
        passRate.value = parseFloat(
          ((passRate.value * (totalDetected.value - 1) + 100) / totalDetected.value).toFixed(1)
        );
      } else {
        passRate.value = parseFloat(
          ((passRate.value * (totalDetected.value - 1)) / totalDetected.value).toFixed(1)
        );
      }
    }
  }, 3000);
});

onBeforeUnmount(() => {
  clearInterval(dataInterval);
});


const getEnergyLevelType = (level: string) => {
  switch (level) {
    case '1级': return 'success';
    case '2级': return 'primary';
    case '3级': return 'warning';
    case '4级': return 'danger';
    case '5级': return 'info';
    default: return 'info';
  }
};
</script>

<style scoped lang="scss">
.dashboard {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0f1325;
  color: #e0e0e0;
  font-family: 'Microsoft YaHei', sans-serif;

  .status-bar {
    display: flex;
    justify-content: space-between;
    padding: 8px 20px;
    background: rgba(0, 0, 0, 0.3);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 14px;

    .system-info, .time-info {
      display: flex;
      align-items: center;
      gap: 15px;
    }
  }

  .main-content {
    display: flex;
    flex: 1;
    overflow: hidden;
    padding: 20px;
    gap: 20px;

    .equipment-panel {
      width: 320px;
      display: flex;
      flex-direction: column;

      h2 {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 0;
        font-size: 18px;
      }

      .equipment-monitor-container {
        flex: 1;
        overflow-y: auto;
        margin-bottom: 15px;
      }

      .quick-actions {
        display: flex;
        gap: 10px;

        button {
          flex: 1;
        }
      }
    }

    .control-panel {
      flex: 1;
      background: rgba(255, 255, 255, 0.03);
      border-radius: 8px;
      overflow: hidden;

      :deep(.el-tabs) {
        height: 100%;
        display: flex;
        flex-direction: column;

        .el-tabs__header {
          margin: 0;
          background: rgba(0, 0, 0, 0.2);
        }

        .el-tabs__content {
          flex: 1;
          padding: 20px;
          overflow: auto;
        }
      }

      .conveyor-control {
        h3 {
          margin-top: 0;
          color: #409eff;
        }

        .control-row {
          display: flex;
          align-items: center;
          margin: 20px 0;

          .label {
            width: 100px;
            font-size: 14px;
          }

          .el-slider {
            flex: 1;
            margin-left: 20px;
          }
        }

        .status-panel {
          margin-top: 30px;

          h4 {
            color: #67c23a;
            margin-bottom: 15px;
          }
        }
      }

      .vision-control {
        h3 {
          margin-top: 0;
          color: #409eff;
          text-align: center;
          margin-bottom: 20px;
        }

        .control-panel {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
          flex-wrap: wrap;

          .el-button.auto-recognizing {
            background-color: #e6a23c;
            border-color: #e6a23c;
          }
        }

        .video-container {
          display: flex;
          gap: 20px;
          margin-bottom: 20px;

          .video-feed {
            flex: 2;
            position: relative;
            background: #000;
            border-radius: 8px;
            overflow: hidden;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;

            video {
              width: 100%;
              height: auto;
              max-height: 400px;
              object-fit: contain;

              &.video-active {
                display: block;
              }
            }

            .video-placeholder {
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: center;
              color: rgba(255, 255, 255, 0.5);
              padding: 40px;

              .el-icon {
                margin-bottom: 16px;
              }
            }

            .detection-overlay {
              position: absolute;
              top: 10px;
              left: 10px;
              right: 10px;
              display: flex;
              justify-content: space-between;
              align-items: center;

              .detection-info {
                display: flex;
                gap: 10px;
                align-items: center;

                .fps-counter {
                  color: #67c23a;
                  font-size: 14px;
                  font-weight: bold;
                }
              }
            }
          }

          .result-panel {
            flex: 1;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 20px;
            min-height: 400px;

            h4 {
              margin-top: 0;
              color: #67c23a;
              margin-bottom: 16px;
              text-align: center;
            }

            .current-result {
              .result-card {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 16px;
                border-left: 4px solid #e6a23c;

                &.high-confidence {
                  border-left-color: #67c23a;
                }

                .result-header {
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                  margin-bottom: 12px;

                  .confidence {
                    font-size: 14px;
                    color: rgba(255, 255, 255, 0.8);
                  }
                }

                .result-content {
                  div {
                    margin-bottom: 8px;
                    font-size: 14px;

                    strong {
                      color: #409eff;
                      margin-right: 8px;
                    }
                  }
                }
              }
            }

            .no-result {
              display: flex;
              align-items: center;
              justify-content: center;
              height: 200px;
            }
          }
        }

        @media (max-width: 1200px) {
          .video-container {
            flex-direction: column;

            .video-feed, .result-panel {
              flex: none;
            }
          }
        }
      }
    }
  }

  .data-bar {
    display: flex;
    padding: 10px 20px;
    background: rgba(0, 0, 0, 0.3);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    gap: 30px;

    .metric {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;

      span:first-child {
        color: rgba(255, 255, 255, 0.7);
      }
    }
  }
}

</style>