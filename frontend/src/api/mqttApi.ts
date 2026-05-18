
const MQTT_CONFIG = {
  host: "localhost",
  port: 1883,
  username: "",
  password: "",
  clientId: `web_client_${Math.random().toString(16).substr(2, 8)}`
};

export const MQTT_TOPICS = {
  VIDEO_FRAME: 'camera/video_frame',
  VIDEO_FRAME_BINARY: 'camera/video_frame_binary',
  OBJECT_DATA: 'tracking/object_data',
  OBJECT_DETECTED: 'tracking/object_detected',
  OBJECT_LOST: 'tracking/object_lost',
  TRACKING_STATS: 'tracking/stats',
  SYSTEM_STATUS: 'system/status',
  OCR_TRIGGERED: 'ocr/triggered',
  OCR_RESULT: 'ocr/result',
  CONTROL_COMMAND: 'control/command'
};

export interface MQTTVideoFrame {
  frame_data: string;
  frame_id: string;
  timestamp: number;
}

export interface MQTTBinaryVideoFrame {
  data: ArrayBuffer;
  frame_id: string;
  timestamp: number;
  format: string;
}

export interface MQTTObjectData {
  objects: Array<{
    id: number;
    class_name: string;
    confidence: number;
    bbox: [number, number, number, number];
    timestamp: number;
  }>;
  frame_id: string;
}

export interface MQTTTrackingStats {
  fps: number;
  object_count: number;
  processing_time: number;
  timestamp: number;
}

export interface MQTTControlCommand {
  command: string;
  parameters: any;
  timestamp: number;
}

class MockMqttClient {
  private connected: boolean = false;
  private callbacks: { [event: string]: Function[] } = {};
  private subscriptions: Set<string> = new Set();

  constructor() {
    console.log('使用模拟MQTT客户端');
    setTimeout(() => {
      this.connected = true;
      this.emit('connect');
    }, 100);
  }

  on(event: string, callback: Function) {
    if (!this.callbacks[event]) {
      this.callbacks[event] = [];
    }
    this.callbacks[event].push(callback);
    return this;
  }

  emit(event: string, ...args: any[]) {
    if (this.callbacks[event]) {
      this.callbacks[event].forEach(cb => cb(...args));
    }
  }

  subscribe(topic: string | string[], callback?: Function) {
    const topics = Array.isArray(topic) ? topic : [topic];
    topics.forEach(t => {
      this.subscriptions.add(t);
      console.log(`模拟订阅主题: ${t}`);
    });

    if (callback) {
      callback(null, topics.map(t => ({ topic: t, qos: 0 })));
    }
    return this;
  }

  unsubscribe(topic: string | string[], callback?: Function) {
    const topics = Array.isArray(topic) ? topic : [topic];
    topics.forEach(t => {
      this.subscriptions.delete(t);
      console.log(`模拟取消订阅主题: ${t}`);
    });

    if (callback) {
      callback();
    }
    return this;
  }

  publish(topic: string, message: string, options?: any, callback?: Function) {
    console.log(`模拟发布消息 - 主题: ${topic}, 消息: ${message}`);
    if (callback) {
      callback(null);
    }
    return this;
  }

  end(force?: boolean, callback?: Function) {
    this.connected = false;
    this.emit('close');
    if (callback) {
      callback();
    }
    return this;
  }

  reconnect() {
    console.log('模拟重新连接');
    return this;
  }

  get isConnected(): boolean {
    return this.connected;
  }
}

let mqttClient: MockMqttClient | null = null;
let connectionCallbacks: Function[] = [];
let disconnectCallbacks: Function[] = [];
let errorCallbacks: Function[] = [];
let videoFrameCallbacks: Function[] = [];
let videoFrameBinaryCallbacks: Function[] = [];
let objectDataCallbacks: Function[] = [];
let objectDetectedCallbacks: Function[] = [];
let objectLostCallbacks: Function[] = [];
let trackingStatsCallbacks: Function[] = [];
let systemStatusCallbacks: Function[] = [];
let ocrTriggeredCallbacks: Function[] = [];
let ocrResultCallbacks: Function[] = [];

export const mqttService = {
  connect: (config = MQTT_CONFIG) => {
    if (mqttClient) {
      console.log('MQTT客户端已存在，重新连接');
      mqttClient.end();
    }

    mqttClient = new MockMqttClient();

    mqttClient.on('connect', () => {
      console.log('MQTT模拟连接成功');
      connectionCallbacks.forEach(cb => cb());
    });

    mqttClient.on('close', () => {
      console.log('MQTT模拟连接关闭');
      disconnectCallbacks.forEach(cb => cb());
    });

    mqttClient.on('error', (error: any) => {
      console.error('MQTT模拟连接错误:', error);
      errorCallbacks.forEach(cb => cb(error));
    });

    return mqttClient;
  },

  disconnect: () => {
    if (mqttClient) {
      mqttClient.end();
      mqttClient = null;
    }
  },

  getClient: () => mqttClient,

  isConnected: () => mqttClient?.isConnected || false
};

export const onMQTTConnected = (callback: Function) => {
  connectionCallbacks.push(callback);
};

export const onMQTTDisconnected = (callback: Function) => {
  disconnectCallbacks.push(callback);
};

export const onMQTTError = (callback: Function) => {
  errorCallbacks.push(callback);
};

export const onMQTTVideoFrame = (callback: Function) => {
  videoFrameCallbacks.push(callback);
};

export const onMQTTVideoFrameBinary = (callback: Function) => {
  videoFrameBinaryCallbacks.push(callback);
};

export const onMQTTObjectData = (callback: Function) => {
  objectDataCallbacks.push(callback);
};

export const onMQTTObjectDetected = (callback: Function) => {
  objectDetectedCallbacks.push(callback);
};

export const onMQTTObjectLost = (callback: Function) => {
  objectLostCallbacks.push(callback);
};

export const onMQTTTrackingStats = (callback: Function) => {
  trackingStatsCallbacks.push(callback);
};

export const onMQTTSystemStatus = (callback: Function) => {
  systemStatusCallbacks.push(callback);
};

export const onMQTTOCRTriggered = (callback: Function) => {
  ocrTriggeredCallbacks.push(callback);
};

export const onMQTTOCRResult = (callback: Function) => {
  ocrResultCallbacks.push(callback);
};

export const startMQTTTracking = (cameraSource: number = 0): boolean => {
  console.log(`模拟启动MQTT追踪，摄像头源: ${cameraSource}`);
  if (mqttClient) {
    mqttClient.publish(MQTT_TOPICS.CONTROL_COMMAND, JSON.stringify({
      command: 'start_tracking',
      parameters: { camera_source: cameraSource },
      timestamp: Date.now()
    }));
    return true;
  }
  return false;
};

export const stopMQTTTracking = (): boolean => {
  console.log('模拟停止MQTT追踪');
  if (mqttClient) {
    mqttClient.publish(MQTT_TOPICS.CONTROL_COMMAND, JSON.stringify({
      command: 'stop_tracking',
      parameters: {},
      timestamp: Date.now()
    }));
    return true;
  }
  return false;
};

export const configureMQTTTracking = (config: any): boolean => {
  console.log('模拟配置MQTT追踪:', config);
  if (mqttClient) {
    mqttClient.publish(MQTT_TOPICS.CONTROL_COMMAND, JSON.stringify({
      command: 'configure_tracking',
      parameters: config,
      timestamp: Date.now()
    }));
    return true;
  }
  return false;
};

export const getMQTTConnectionStatus = (): boolean => {
  return mqttService.isConnected();
};

export const subscribeMQTTTopic = (topic: string, callback?: Function): boolean => {
  if (mqttClient) {
    mqttClient.subscribe(topic, callback);
    return true;
  }
  return false;
};

export const generateMockMQTTData = () => {
  if (!mqttClient) return;

  const mockVideoFrame: MQTTVideoFrame = {
    frame_data: 'mock_base64_data',
    frame_id: `frame_${Date.now()}`,
    timestamp: Date.now()
  };

  const mockObjectData: MQTTObjectData = {
    objects: [
      {
        id: 1,
        class_name: 'product',
        confidence: 0.95,
        bbox: [100, 100, 200, 200],
        timestamp: Date.now()
      }
    ],
    frame_id: `frame_${Date.now()}`
  };

  const mockTrackingStats: MQTTTrackingStats = {
    fps: 30,
    object_count: 1,
    processing_time: 16.5,
    timestamp: Date.now()
  };

  videoFrameCallbacks.forEach(cb => cb(mockVideoFrame));
  objectDataCallbacks.forEach(cb => cb(mockObjectData));
  trackingStatsCallbacks.forEach(cb => cb(mockTrackingStats));
};

export { MQTT_CONFIG };

setTimeout(() => {
  mqttService.connect();
}, 500);