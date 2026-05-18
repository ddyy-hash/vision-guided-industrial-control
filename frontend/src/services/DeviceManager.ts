import { reactive, ref } from 'vue';
import { getPlatformConfig, getPlatformAPIEndpoints } from '../utils/platform';
export interface Device {
  id: string;
  name: string;
  type: 'robot' | 'conveyor' | 'camera' | 'sensor';
  status: 'online' | 'offline' | 'error' | 'maintenance';
  ip: string;
  port: number;
  lastHeartbeat: Date;
  data: any;
}

export interface DeviceCommand {
  deviceId: string;
  command: string;
  parameters: any;
  timestamp: Date;
}

class DeviceManager {
  private devices = reactive<Map<string, Device>>(new Map());
  private websocket: WebSocket | null = null;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor() {
    this.initializeDevices();
    this.connectWebSocket();
    this.startHeartbeat();
  }

  private initializeDevices() {
    const config = getPlatformConfig();

    if (config.features.robotArm) {
      this.addDevice({
        id: 'robot-arm-1',
        name: '机械臂#1',
        type: 'robot',
        status: 'offline',
        ip: import.meta.env.VITE_ROBOT_ARM_IP || '192.168.1.100',
        port: 8080,
        lastHeartbeat: new Date(),
        data: {
          joints: [0, 0, 0, 0, 0, 0],
          position: { x: 0, y: 0, z: 0 },
          status: 'idle'
        }
      });
    }

    if (config.features.conveyor) {
      this.addDevice({
        id: 'conveyor-1',
        name: '传送带#1',
        type: 'conveyor',
        status: 'offline',
        ip: import.meta.env.VITE_CONVEYOR_IP || '192.168.1.101',
        port: 8081,
        lastHeartbeat: new Date(),
        data: {
          speed: 0,
          direction: 'forward',
          load: 0,
          temperature: 25
        }
      });
    }

    if (config.features.vision) {
      this.addDevice({
        id: 'vision-camera-1',
        name: '视觉检测#1',
        type: 'camera',
        status: 'offline',
        ip: import.meta.env.VITE_VISION_CAMERA_IP || '192.168.1.102',
        port: 8082,
        lastHeartbeat: new Date(),
        data: {
          resolution: '1920x1080',
          fps: 30,
          detectionCount: 0,
          passRate: 0
        }
      });
    }

    if (config.features.temperature) {
      this.addDevice({
        id: 'temp-sensor-1',
        name: '温度传感器#1',
        type: 'sensor',
        status: 'offline',
        ip: import.meta.env.VITE_TEMP_SENSOR_IP || '192.168.1.103',
        port: 8083,
        lastHeartbeat: new Date(),
        data: {
          temperature: 0,
          humidity: 0,
          pressure: 0
        }
      });
    }
  }

  private connectWebSocket() {
    const wsUrl = import.meta.env.VITE_WEBSOCKET_URL;

    try {
      this.websocket = new WebSocket(wsUrl);

      this.websocket.onopen = () => {
        console.log('WebSocket连接已建立');
        this.reconnectAttempts = 0;
      };

      this.websocket.onmessage = (event) => {
        this.handleWebSocketMessage(event.data);
      };

      this.websocket.onclose = () => {
        console.log('WebSocket连接已关闭');
        this.attemptReconnect();
      };

      this.websocket.onerror = (error) => {
        console.error('WebSocket错误:', error);
      };
    } catch (error) {
      console.error('WebSocket连接失败:', error);
    }
  }

  private handleWebSocketMessage(data: string) {
    try {
      const message = JSON.parse(data);

      if (message.type === 'device-status') {
        this.updateDeviceStatus(message.deviceId, message.status, message.data);
      } else if (message.type === 'device-data') {
        this.updateDeviceData(message.deviceId, message.data);
      }
    } catch (error) {
      console.error('解析WebSocket消息失败:', error);
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`尝试重连WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        this.connectWebSocket();
      }, 3000 * this.reconnectAttempts);
    }
  }

  private startHeartbeat() {
    const config = getPlatformConfig();

    this.heartbeatInterval = setInterval(() => {
      this.devices.forEach((device) => {
        const now = new Date();
        const timeSinceHeartbeat = now.getTime() - device.lastHeartbeat.getTime();

        if (timeSinceHeartbeat > 30000) {
          device.status = 'offline';
        }
      });
    }, config.apiTimeout || 5000);
  }

  addDevice(device: Device) {
    this.devices.set(device.id, device);
  }

  getDevice(deviceId: string): Device | undefined {
    return this.devices.get(deviceId);
  }

  getAllDevices(): Device[] {
    return Array.from(this.devices.values());
  }

  updateDeviceStatus(deviceId: string, status: Device['status'], data?: any) {
    const device = this.devices.get(deviceId);
    if (device) {
      device.status = status;
      device.lastHeartbeat = new Date();
      if (data) {
        device.data = { ...device.data, ...data };
      }
    }
  }

  updateDeviceData(deviceId: string, data: any) {
    const device = this.devices.get(deviceId);
    if (device) {
      device.data = { ...device.data, ...data };
      device.lastHeartbeat = new Date();
    }
  }

  async sendCommand(command: DeviceCommand): Promise<boolean> {
    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket未连接');
      return false;
    }

    try {
      const message = JSON.stringify({
        type: 'device-command',
        ...command
      });

      this.websocket.send(message);
      return true;
    } catch (error) {
      console.error('发送设备命令失败:', error);
      return false;
    }
  }

  destroy() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    if (this.websocket) {
      this.websocket.close();
    }
  }
}

export const deviceManager = new DeviceManager();
