import axios from 'axios';
import { io, Socket } from 'socket.io-client';

const API_BASE_URL = 'http://localhost:5000/api';
const WS_BASE_URL = 'http://localhost:5000';

export interface EnergyDetectionResult {
  success: boolean;
  energy_level?: string;
  confidence?: number;
  text?: string;
  coordinates?: number[];
  timestamp: number;
  frame_id: number;
  error?: string;
}

export interface EnergyDetectionStats {
  is_running: boolean;
  fps: number;
  processing_time: number;
  frame_count: number;
  detection_count: number;
  success_count: number;
  error_count: number;
  last_detection?: EnergyDetectionResult;
  camera_status: 'connected' | 'disconnected' | 'error';
  ocr_service_status: 'connected' | 'disconnected' | 'error';
}

export interface EnergyDetectionConfig {
  detection_interval: number;
  confidence_threshold: number;
  camera_source: number;
  enable_simulation: boolean;
  max_frame_skip: number;
}

class EnergyDetectionAPI {
  private socket: Socket | null = null;
  private callbacks: Map<string, Function[]> = new Map();

  constructor() {
    this.setupSocketConnection();
  }

  private setupSocketConnection() {
    console.log('正在连接实时能效检测WebSocket:', WS_BASE_URL);
    this.socket = io(WS_BASE_URL, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    this.socket.on('connect', () => {
      console.log('实时能效检测WebSocket已连接', this.socket?.id);
      this.triggerCallbacks('socket_connected', { status: 'connected', id: this.socket?.id });
    });

    this.socket.on('disconnect', () => {
      console.log('实时能效检测WebSocket已断开');
      this.triggerCallbacks('socket_disconnected', { status: 'disconnected' });
    });

    this.socket.on('connect_error', (error) => {
      console.error('实时能效检测WebSocket连接错误:', error);
      this.triggerCallbacks('socket_error', { error: error.message });
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log('实时能效检测WebSocket重新连接成功，尝试次数:', attemptNumber);
      this.triggerCallbacks('socket_reconnected', { status: 'reconnected', attempts: attemptNumber });
    });

    this.socket.on('energy_detection_started', (data) => {
      this.triggerCallbacks('energy_detection_started', data);
    });

    this.socket.on('energy_detection_stopped', (data) => {
      this.triggerCallbacks('energy_detection_stopped', data);
    });

    this.socket.on('energy_detection_result', (data) => {
      this.triggerCallbacks('energy_detection_result', data);
    });

    this.socket.on('energy_detection_status', (data) => {
      this.triggerCallbacks('energy_detection_status', data);
    });

    this.socket.on('energy_detection_frame', (data) => {
      this.triggerCallbacks('energy_detection_frame', data);
    });

    this.socket.on('energy_detection_error', (data) => {
      this.triggerCallbacks('energy_detection_error', data);
    });
  }

  private triggerCallbacks(event: string, data: any) {
    const callbacks = this.callbacks.get(event) || [];
    callbacks.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`实时能效检测回调函数错误 (${event}):`, error);
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

  async startEnergyDetection(cameraSource: number = 0): Promise<boolean> {
    try {
      if (this.socket) {
        this.socket.emit('start_energy_detection', { camera_source: cameraSource });
      }

      const response = await axios.post(`${API_BASE_URL}/realtime_energy/control`, {
        action: 'start',
        camera_source: cameraSource
      });

      return response.data.success;
    } catch (error) {
      console.error('启动实时能效检测失败:', error);
      return false;
    }
  }

  async stopEnergyDetection(): Promise<boolean> {
    try {
      if (this.socket) {
        this.socket.emit('stop_energy_detection');
      }

      const response = await axios.post(`${API_BASE_URL}/realtime_energy/control`, {
        action: 'stop'
      });

      return response.data.success;
    } catch (error) {
      console.error('停止实时能效检测失败:', error);
      return false;
    }
  }

  async getDetectionStatus(): Promise<EnergyDetectionStats | null> {
    try {
      const response = await axios.get(`${API_BASE_URL}/realtime_energy/status`);
      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (error) {
      console.error('获取实时能效检测状态失败:', error);
      return null;
    }
  }

  async getDetectionStats(): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/realtime_energy/stats`);
      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (error) {
      console.error('获取实时能效检测统计失败:', error);
      return null;
    }
  }

  async configureDetection(config: Partial<EnergyDetectionConfig>): Promise<boolean> {
    try {
      const response = await axios.post(`${API_BASE_URL}/realtime_energy/configure`, config);
      return response.data.success;
    } catch (error) {
      console.error('配置实时能效检测失败:', error);
      return false;
    }
  }

  async getDetectionConfig(): Promise<EnergyDetectionConfig | null> {
    try {
      const response = await axios.get(`${API_BASE_URL}/realtime_energy/config`);
      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (error) {
      console.error('获取实时能效检测配置失败:', error);
      return null;
    }
  }

  async getRecentResults(limit: number = 10): Promise<EnergyDetectionResult[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/realtime_energy/results`, {
        params: { limit }
      });
      if (response.data.success) {
        return response.data.data;
      }
      return [];
    } catch (error) {
      console.error('获取最近检测结果失败:', error);
      return [];
    }
  }

  async triggerSingleDetection(): Promise<EnergyDetectionResult | null> {
    try {
      const response = await axios.post(`${API_BASE_URL}/realtime_energy/detect`);
      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (error) {
      console.error('手动触发检测失败:', error);
      return null;
    }
  }

  async getCurrentFrame(): Promise<string | null> {
    try {
      const response = await axios.get(`${API_BASE_URL}/realtime_energy/frame`);
      if (response.data.success) {
        return response.data.data.frame;
      }
      return null;
    } catch (error) {
      console.error('获取视频帧失败:', error);
      return null;
    }
  }

  async resetStats(): Promise<boolean> {
    try {
      const response = await axios.post(`${API_BASE_URL}/realtime_energy/reset`);
      return response.data.success;
    } catch (error) {
      console.error('重置检测统计失败:', error);
      return false;
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

export const energyDetectionAPI = new EnergyDetectionAPI();

export const startEnergyDetection = (cameraSource: number = 0) => energyDetectionAPI.startEnergyDetection(cameraSource);
export const stopEnergyDetection = () => energyDetectionAPI.stopEnergyDetection();
export const getDetectionStatus = () => energyDetectionAPI.getDetectionStatus();
export const getDetectionStats = () => energyDetectionAPI.getDetectionStats();
export const configureDetection = (config: Partial<EnergyDetectionConfig>) => energyDetectionAPI.configureDetection(config);
export const getDetectionConfig = () => energyDetectionAPI.getDetectionConfig();
export const getRecentResults = (limit: number = 10) => energyDetectionAPI.getRecentResults(limit);
export const triggerSingleDetection = () => energyDetectionAPI.triggerSingleDetection();
export const getCurrentFrame = () => energyDetectionAPI.getCurrentFrame();
export const resetStats = () => energyDetectionAPI.resetStats();

export const onEnergyDetectionStarted = (callback: Function) => energyDetectionAPI.on('energy_detection_started', callback);
export const onEnergyDetectionStopped = (callback: Function) => energyDetectionAPI.on('energy_detection_stopped', callback);
export const onEnergyDetectionResult = (callback: Function) => energyDetectionAPI.on('energy_detection_result', callback);
export const onEnergyDetectionStatus = (callback: Function) => energyDetectionAPI.on('energy_detection_status', callback);
export const onEnergyDetectionFrame = (callback: Function) => energyDetectionAPI.on('energy_detection_frame', callback);
export const onEnergyDetectionError = (callback: Function) => energyDetectionAPI.on('energy_detection_error', callback);