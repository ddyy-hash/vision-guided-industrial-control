import { trackingAPI, TrackingObject, TrackingStats, OCRStatus, TrackingData } from './trackingApi';
import {
  mqttService,
  MQTT_TOPICS,
  MQTTVideoFrame,
  MQTTBinaryVideoFrame,
  MQTTObjectData,
  MQTTTrackingStats,
  MQTTControlCommand,
  onMQTTConnected,
  onMQTTDisconnected,
  onMQTTError,
  onMQTTVideoFrame,
  onMQTTVideoFrameBinary,
  onMQTTObjectData,
  onMQTTObjectDetected,
  onMQTTObjectLost,
  onMQTTTrackingStats,
  onMQTTSystemStatus,
  onMQTTOCRTriggered,
  onMQTTOCRResult,
  startMQTTTracking,
  stopMQTTTracking,
  configureMQTTTracking,
  getMQTTConnectionStatus,
  subscribeMQTTTopic
} from './mqttApi';

export enum CommunicationProtocol {
  WEBSOCKET = 'websocket',
  MQTT = 'mqtt',
  HTTP = 'http'
}

export interface UnifiedApiConfig {
  preferredProtocol: CommunicationProtocol;
  enableFallback: boolean;
  mqttEnabled: boolean;
  websocketEnabled: boolean;
  httpEnabled: boolean;
}

const DEFAULT_CONFIG: UnifiedApiConfig = {
  preferredProtocol: CommunicationProtocol.MQTT,
  enableFallback: true,
  mqttEnabled: true,
  websocketEnabled: true,
  httpEnabled: true
};

export interface CommunicationStatus {
  currentProtocol: CommunicationProtocol;
  mqttConnected: boolean;
  websocketConnected: boolean;
  fallbackActive: boolean;
  lastError?: string;
}

class UnifiedCommunicationService {
  private config: UnifiedApiConfig;
  private status: CommunicationStatus;
  private callbacks: Map<string, Function[]> = new Map();
  private currentProtocol: CommunicationProtocol;
  private fallbackActive: boolean = false;

  constructor(config: Partial<UnifiedApiConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.currentProtocol = this.config.preferredProtocol;

    this.status = {
      currentProtocol: this.currentProtocol,
      mqttConnected: false,
      websocketConnected: false,
      fallbackActive: false,
      lastError: undefined
    };

    this.setupProtocols();
    this.setupEventForwarding();
  }

  private setupProtocols() {
    if (this.config.mqttEnabled) {
      onMQTTConnected(() => {
        this.status.mqttConnected = true;
        this.triggerCallbacks('protocol_status', this.status);
        console.log('MQTT协议已连接');

        if (this.config.preferredProtocol === CommunicationProtocol.MQTT && !this.fallbackActive) {
          this.switchToProtocol(CommunicationProtocol.MQTT);
        }
      });

      onMQTTDisconnected(() => {
        this.status.mqttConnected = false;
        this.triggerCallbacks('protocol_status', this.status);
        console.log('MQTT协议已断开');

        if (this.currentProtocol === CommunicationProtocol.MQTT && this.config.enableFallback) {
          this.triggerFallback();
        }
      });

      onMQTTError((error: any) => {
        console.error('MQTT协议错误:', error);
        this.status.lastError = `MQTT: ${error.error || '未知错误'}`;
        this.triggerCallbacks('protocol_error', this.status);

        if (this.currentProtocol === CommunicationProtocol.MQTT && this.config.enableFallback) {
          this.triggerFallback();
        }
      });
    }

    if (this.config.websocketEnabled) {
      trackingAPI.on('socket_connected', () => {
        this.status.websocketConnected = true;
        this.triggerCallbacks('protocol_status', this.status);
        console.log('WebSocket协议已连接');
      });

      trackingAPI.on('socket_disconnected', () => {
        this.status.websocketConnected = false;
        this.triggerCallbacks('protocol_status', this.status);
        console.log('WebSocket协议已断开');

        if (this.currentProtocol === CommunicationProtocol.WEBSOCKET && this.config.enableFallback) {
          this.triggerFallback();
        }
      });

      trackingAPI.on('socket_error', (error: any) => {
        console.error('WebSocket协议错误:', error);
        this.status.lastError = `WebSocket: ${error.error || '未知错误'}`;
        this.triggerCallbacks('protocol_error', this.status);

        if (this.currentProtocol === CommunicationProtocol.WEBSOCKET && this.config.enableFallback) {
          this.triggerFallback();
        }
      });
    }
  }

  private setupEventForwarding() {
    if (this.config.mqttEnabled) {
      onMQTTVideoFrame((data: MQTTVideoFrame) => {
        if (window._debugMode) {
          console.log('MQTT视频帧事件收到:', {
            hasFrameData: !!data.frame_data,
            frameLength: data.frame_data?.length,
            frameId: data.frame_id
          })
        }

        if (this.currentProtocol === CommunicationProtocol.MQTT) {
          this.triggerCallbacks('video_frame', {
            frame: data.frame_data,
            frame_id: data.frame_id,
            timestamp: data.timestamp
          });
        }
      });

      onMQTTVideoFrameBinary((data: MQTTBinaryVideoFrame) => {
        if (this.currentProtocol === CommunicationProtocol.MQTT) {
          const base64 = btoa(
            new Uint8Array(data.data).reduce(
              (data, byte) => data + String.fromCharCode(byte), ''
            )
          );
          this.triggerCallbacks('video_frame', {
            frame: `data:image/${data.format};base64,${base64}`,
            frame_id: data.frame_id,
            timestamp: data.timestamp
          });
        }
      });

      onMQTTObjectData((data: MQTTObjectData) => {
        if (this.currentProtocol === CommunicationProtocol.MQTT) {
          this.triggerCallbacks('object_data', data);
        }
      });

      onMQTTObjectDetected((data: any) => {
        if (this.currentProtocol === CommunicationProtocol.MQTT) {
          this.triggerCallbacks('object_detected', data);
        }
      });

      onMQTTObjectLost((data: any) => {
        if (this.currentProtocol === CommunicationProtocol.MQTT) {
          this.triggerCallbacks('object_lost', data);
        }
      });

      onMQTTTrackingStats((data: MQTTTrackingStats) => {
        if (this.currentProtocol === CommunicationProtocol.MQTT) {
          this.triggerCallbacks('tracking_stats', data);
        }
      });

      onMQTTSystemStatus((data: any) => {
        if (this.currentProtocol === CommunicationProtocol.MQTT) {
          this.triggerCallbacks('system_status', data);
        }
      });

      onMQTTOCRTriggered((data: any) => {
        if (this.currentProtocol === CommunicationProtocol.MQTT) {
          this.triggerCallbacks('ocr_triggered', data);
        }
      });

      onMQTTOCRResult((data: any) => {
        if (this.currentProtocol === CommunicationProtocol.MQTT) {
          this.triggerCallbacks('ocr_result', data);
        }
      });
    }

    if (this.config.websocketEnabled) {
      trackingAPI.on('video_frame', (data: any) => {
        if (window._debugMode) {
          console.log('WebSocket视频帧事件收到:', {
            hasFrame: !!data.frame,
            frameLength: data.frame?.length,
            frameId: data.frame_id
          })
        }

        if (this.currentProtocol === CommunicationProtocol.WEBSOCKET) {
          this.triggerCallbacks('video_frame', data);
        }
      });

      trackingAPI.on('object_detected', (data: any) => {
        if (this.currentProtocol === CommunicationProtocol.WEBSOCKET) {
          this.triggerCallbacks('object_detected', data);
        }
      });

      trackingAPI.on('object_lost', (data: any) => {
        if (this.currentProtocol === CommunicationProtocol.WEBSOCKET) {
          this.triggerCallbacks('object_lost', data);
        }
      });

      trackingAPI.on('frame_processed', (data: any) => {
        if (this.currentProtocol === CommunicationProtocol.WEBSOCKET) {
          this.triggerCallbacks('object_data', data.frame_data);
        }
      });

      trackingAPI.on('tracking_status', (data: any) => {
        if (this.currentProtocol === CommunicationProtocol.WEBSOCKET) {
          this.triggerCallbacks('tracking_stats', data);
        }
      });

      trackingAPI.on('ocr_triggered', (data: any) => {
        if (this.currentProtocol === CommunicationProtocol.WEBSOCKET) {
          this.triggerCallbacks('ocr_triggered', data);
        }
      });

      trackingAPI.on('ocr_result', (data: any) => {
        if (this.currentProtocol === CommunicationProtocol.WEBSOCKET) {
          this.triggerCallbacks('ocr_result', data);
        }
      });
    }
  }

  private triggerFallback() {
    if (!this.config.enableFallback) return;

    console.log('触发协议降级，寻找备用协议...');

    const availableProtocols = this.getAvailableProtocols();
    if (availableProtocols.length > 0) {
      const fallbackProtocol = availableProtocols[0];
      console.log(`切换到备用协议: ${fallbackProtocol}`);
      this.switchToProtocol(fallbackProtocol);
      this.fallbackActive = true;
      this.status.fallbackActive = true;

      this.triggerCallbacks('protocol_fallback', {
        from: this.currentProtocol,
        to: fallbackProtocol,
        reason: '主协议连接失败'
      });
    } else {
      console.error('无可用备用协议');
      this.triggerCallbacks('protocol_unavailable', {
        error: '所有通信协议均不可用'
      });
    }
  }

  private getAvailableProtocols(): CommunicationProtocol[] {
    const available: CommunicationProtocol[] = [];

    if (this.config.mqttEnabled && this.status.mqttConnected) {
      available.push(CommunicationProtocol.MQTT);
    }

    if (this.config.websocketEnabled && this.status.websocketConnected) {
      available.push(CommunicationProtocol.WEBSOCKET);
    }

    if (this.config.httpEnabled) {
      available.push(CommunicationProtocol.HTTP);
    }

    return available.filter(p => p !== this.currentProtocol);
  }

  private switchToProtocol(protocol: CommunicationProtocol) {
    const oldProtocol = this.currentProtocol;
    this.currentProtocol = protocol;
    this.status.currentProtocol = protocol;

    console.log(`通信协议切换: ${oldProtocol} -> ${protocol}`);
    this.triggerCallbacks('protocol_switched', {
      from: oldProtocol,
      to: protocol
    });
  }

  private triggerCallbacks(event: string, data: any) {
    const callbacks = this.callbacks.get(event) || [];

    if (window._debugMode && callbacks.length > 0) {
      console.log(`触发回调事件: ${event}, 回调数量: ${callbacks.length}`)
    }

    callbacks.forEach((callback, index) => {
      try {
        callback(data);
      } catch (error) {
        console.error(`统一通信服务回调错误 (${event}):`, error);
      }
    });
  }


  on(event: string, callback: Function) {
    if (!this.callbacks.has(event)) {
      this.callbacks.set(event, []);
    }
    this.callbacks.get(event)!.push(callback);
  }

  off(event: string, callback: Function) {
    if (this.callbacks.has(event)) {
      const callbacks = this.callbacks.get(event)!;
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  async startTracking(cameraSource: number = 0): Promise<boolean> {
    try {
      let success = false;

      switch (this.currentProtocol) {
        case CommunicationProtocol.MQTT:
          success = startMQTTTracking(cameraSource);
          break;

        case CommunicationProtocol.WEBSOCKET:
          success = await trackingAPI.startTracking(cameraSource);
          break;

        case CommunicationProtocol.HTTP:
          success = await trackingAPI.startTracking(cameraSource);
          break;
      }

      if (success) {
        this.triggerCallbacks('tracking_started', { protocol: this.currentProtocol });
      } else {
        if (this.config.enableFallback) {
          console.log('追踪启动失败，尝试协议降级...');
          this.triggerFallback();
          return this.startTracking(cameraSource);
        }
      }

      return success;
    } catch (error) {
      console.error('启动追踪失败:', error);

      if (this.config.enableFallback) {
        console.log('追踪启动异常，尝试协议降级...');
        this.triggerFallback();
        return this.startTracking(cameraSource);
      }

      return false;
    }
  }

  async stopTracking(): Promise<boolean> {
    try {
      let success = false;

      switch (this.currentProtocol) {
        case CommunicationProtocol.MQTT:
          success = stopMQTTTracking();
          break;

        case CommunicationProtocol.WEBSOCKET:
          success = await trackingAPI.stopTracking();
          break;

        case CommunicationProtocol.HTTP:
          success = await trackingAPI.stopTracking();
          break;
      }

      if (success) {
        this.triggerCallbacks('tracking_stopped', { protocol: this.currentProtocol });
      }

      return success;
    } catch (error) {
      console.error('停止追踪失败:', error);
      return false;
    }
  }

  async configureTracking(config: any): Promise<boolean> {
    try {
      switch (this.currentProtocol) {
        case CommunicationProtocol.MQTT:
          return configureMQTTTracking(config);

        case CommunicationProtocol.WEBSOCKET:
        case CommunicationProtocol.HTTP:
          return await trackingAPI.configureTracking(config);

        default:
          return false;
      }
    } catch (error) {
      console.error('配置追踪失败:', error);
      return false;
    }
  }

  async getTrackingStatus(): Promise<TrackingStats | null> {
    return await trackingAPI.getTrackingStatus();
  }

  async getCurrentObjects(): Promise<TrackingObject[]> {
    return await trackingAPI.getCurrentObjects();
  }

  async getOCRStatus(): Promise<OCRStatus> {
    return await trackingAPI.getOCRStatus();
  }

  async getTrackingData(): Promise<TrackingData> {
    return await trackingAPI.getTrackingData();
  }

  getCommunicationStatus(): CommunicationStatus {
    return { ...this.status };
  }

  isConnected(): boolean {
    return this.status.mqttConnected || this.status.websocketConnected;
  }

  switchProtocol(protocol: CommunicationProtocol): boolean {
    if (!this.config.enableFallback) {
      console.warn('协议降级功能已禁用，无法手动切换协议');
      return false;
    }

    const availableProtocols = this.getAvailableProtocols();
    if (availableProtocols.includes(protocol)) {
      this.switchToProtocol(protocol);
      this.fallbackActive = false;
      this.status.fallbackActive = false;
      return true;
    } else {
      console.warn(`协议 ${protocol} 当前不可用`);
      return false;
    }
  }

  connect() {
    if (this.config.mqttEnabled) {
      mqttService.connect();
    }

    if (this.config.websocketEnabled) {
      console.log('WebSocket连接已初始化');
    }
  }

  disconnect() {
    if (this.config.mqttEnabled) {
      mqttService.disconnect();
    }

    if (this.config.websocketEnabled) {
      trackingAPI.disconnect();
    }

    this.status.mqttConnected = false;
    this.status.websocketConnected = false;
    this.fallbackActive = false;
    this.status.fallbackActive = false;
  }

  async executeRobotArmActions(actions: Array<{
    type: string;
    joint?: number;
    angle?: number;
    speed?: number;
    x?: number;
    y?: number;
    z?: number;
  }>): Promise<{ success: boolean; message?: string }> {
    try {
      const response = await fetch('http://localhost:5000/api/robot_arm/execute_sequence', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          actions: actions,
          protocol: this.currentProtocol
        })
      });

      if (response.ok) {
        const result = await response.json();
        return {
          success: result.success || false,
          message: result.message || '机械臂动作执行完成'
        };
      } else {
        return {
          success: false,
          message: `机械臂控制失败: HTTP ${response.status}`
        };
      }
    } catch (error) {
      console.error('机械臂控制异常:', error);
      return {
        success: false,
        message: `机械臂控制异常: ${error}`
      };
    }
  }

  async getRobotArmStatus(): Promise<{
    connected: boolean;
    position: number[];
    temperature: number;
    busy: boolean;
  }> {
    try {
      const response = await fetch('http://localhost:5000/api/robot_arm/status');

      if (response.ok) {
        const result = await response.json();
        return {
          connected: result.connected || false,
          position: result.position || [0, 0, 0, 0, 0],
          temperature: result.temperature || 32.5,
          busy: result.busy || false
        };
      } else {
        return {
          connected: false,
          position: [0, 0, 0, 0, 0],
          temperature: 32.5,
          busy: false
        };
      }
    } catch (error) {
      console.error('获取机械臂状态失败:', error);
      return {
        connected: false,
        position: [0, 0, 0, 0, 0],
        temperature: 32.5,
        busy: false
      };
    }
  }
}

export const unifiedApi = new UnifiedCommunicationService();

export const startUnifiedTracking = (cameraSource: number = 0) =>
  unifiedApi.startTracking(cameraSource);

export const stopUnifiedTracking = () =>
  unifiedApi.stopTracking();

export const configureUnifiedTracking = (config: any) =>
  unifiedApi.configureTracking(config);

export const getUnifiedTrackingStatus = () =>
  unifiedApi.getTrackingStatus();

export const getUnifiedCurrentObjects = () =>
  unifiedApi.getCurrentObjects();

export const getUnifiedOCRStatus = () =>
  unifiedApi.getOCRStatus();

export const getUnifiedTrackingData = () =>
  unifiedApi.getTrackingData();

export const getUnifiedCommunicationStatus = () =>
  unifiedApi.getCommunicationStatus();

export const switchUnifiedProtocol = (protocol: CommunicationProtocol) =>
  unifiedApi.switchProtocol(protocol);

export const disconnectUnified = () =>
  unifiedApi.disconnect();

export const connectUnified = () =>
  unifiedApi.connect();

export const onUnifiedVideoFrame = (callback: Function) =>
  unifiedApi.on('video_frame', callback);

export const onUnifiedObjectDetected = (callback: Function) =>
  unifiedApi.on('object_detected', callback);

export const onUnifiedObjectLost = (callback: Function) =>
  unifiedApi.on('object_lost', callback);

export const onUnifiedObjectData = (callback: Function) =>
  unifiedApi.on('object_data', callback);

export const onUnifiedTrackingStats = (callback: Function) =>
  unifiedApi.on('tracking_stats', callback);

export const onUnifiedOCRTriggered = (callback: Function) =>
  unifiedApi.on('ocr_triggered', callback);

export const onUnifiedOCRResult = (callback: Function) =>
  unifiedApi.on('ocr_result', callback);

export const onUnifiedProtocolStatus = (callback: Function) =>
  unifiedApi.on('protocol_status', callback);

export const onUnifiedProtocolError = (callback: Function) =>
  unifiedApi.on('protocol_error', callback);

export const onUnifiedProtocolSwitched = (callback: Function) =>
  unifiedApi.on('protocol_switched', callback);

export const onUnifiedProtocolFallback = (callback: Function) =>
  unifiedApi.on('protocol_fallback', callback);

export const onUnifiedProtocolUnavailable = (callback: Function) =>
  unifiedApi.on('protocol_unavailable', callback);

export const onUnifiedTrackingStarted = (callback: Function) =>
  unifiedApi.on('tracking_started', callback);

export const onUnifiedTrackingStopped = (callback: Function) =>
  unifiedApi.on('tracking_stopped', callback);