import axios from 'axios';
import { io, Socket } from 'socket.io-client';

const API_BASE_URL = 'http://localhost:5000/api';
const WS_BASE_URL = 'http://localhost:5000';

export interface TrackingObject {
  track_id: number;
  conveyor_x: number;
  conveyor_y: number;
  bbox: number[];
  class_id: number;
  class_name: string;
  confidence: number;
  velocity: number;
  timestamp: number;
}

export interface TrackingStats {
  fps: number;
  processing_time: number;
  frame_count: number;
  detection_count: number;
  active_tracks: number;
  is_running: boolean;
  tracking_enabled: boolean;
  ocr_requests: number;
  ocr_success: number;
}

export interface SystemStatus {
  tracking: boolean;
  ocr: boolean;
  conveyor: boolean;
}

export interface OCRStatus {
  [track_id: number]: {
    status: 'pending' | 'success' | 'failed';
    trigger_time: number;
    object_data: TrackingObject;
    ocr_data?: any;
    energy_label?: {
      level: string;
      confidence: number;
      text: string;
      coordinates: number[];
    };
    error?: string;
  };
}

export interface TrackingData {
  objects: TrackingObject[];
  frame_id: number;
  timestamp: string;
  detections: number;
  fps: number;
  processing_time: number;
}

class TrackingAPI {
  private socket: Socket | null = null;
  private callbacks: Map<string, Function[]> = new Map();

  constructor() {
    this.setupSocketConnection();
  }

  private setupSocketConnection() {
    console.log('正在连接WebSocket:', WS_BASE_URL);
    this.socket = io(WS_BASE_URL, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    this.socket.on('connect', () => {
      console.log('追踪服务WebSocket已连接', this.socket?.id);
      this.triggerCallbacks('socket_connected', { status: 'connected', id: this.socket?.id });
    });

    this.socket.on('disconnect', () => {
      console.log('追踪服务WebSocket已断开');
      this.triggerCallbacks('socket_disconnected', { status: 'disconnected' });
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket连接错误:', error);
      this.triggerCallbacks('socket_error', { error: error.message });
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log('WebSocket重新连接成功，尝试次数:', attemptNumber);
      this.triggerCallbacks('socket_reconnected', { status: 'reconnected', attempts: attemptNumber });
    });

    this.socket.on('object_detected', (data) => {
      this.triggerCallbacks('object_detected', data);
    });

    this.socket.on('object_lost', (data) => {
      this.triggerCallbacks('object_lost', data);
    });

    this.socket.on('frame_processed', (data) => {
      this.triggerCallbacks('frame_processed', data);
    });

    this.socket.on('tracking_status', (data) => {
      this.triggerCallbacks('tracking_status', data);
    });

    this.socket.on('ocr_triggered', (data) => {
      this.triggerCallbacks('ocr_triggered', data);
    });

    this.socket.on('ocr_result', (data) => {
      this.triggerCallbacks('ocr_result', data);
    });

    this.socket.on('conveyor_status', (data) => {
      this.triggerCallbacks('conveyor_status', data);
    });

    this.socket.on('video_frame', (data) => {
      this.triggerCallbacks('video_frame', data);
    });
  }

  private triggerCallbacks(event: string, data: any) {
    const callbacks = this.callbacks.get(event) || [];
    callbacks.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error(`回调函数错误 (${event}):`, error);
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
      if (this.socket) {
        this.socket.emit('start_tracking', { camera_source: cameraSource });
      }

      const response = await axios.post(`${API_BASE_URL}/tracking/control`, {
        action: 'start',
        camera_source: cameraSource
      });

      return response.data.success;
    } catch (error) {
      console.error('启动追踪失败:', error);
      return false;
    }
  }

  async stopTracking(): Promise<boolean> {
    try {
      if (this.socket) {
        this.socket.emit('stop_tracking');
      }

      const response = await axios.post(`${API_BASE_URL}/tracking/control`, {
        action: 'stop'
      });

      return response.data.success;
    } catch (error) {
      console.error('停止追踪失败:', error);
      return false;
    }
  }

  async getCurrentObjects(): Promise<TrackingObject[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracking/objects`);
      if (response.data.success) {
        return response.data.data.objects;
      }
      return [];
    } catch (error) {
      console.error('获取追踪物体失败:', error);
      return [];
    }
  }

  async getTrackingStatus(): Promise<TrackingStats | null> {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracking/status`);
      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (error) {
      console.error('获取追踪状态失败:', error);
      return null;
    }
  }

  async getTrackingStats(): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracking/stats`);
      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (error) {
      console.error('获取追踪统计失败:', error);
      return null;
    }
  }

  async configureTracking(config: any): Promise<boolean> {
    try {
      const response = await axios.post(`${API_BASE_URL}/tracking/control`, {
        action: 'configure',
        config: config
      });

      return response.data.success;
    } catch (error) {
      console.error('配置追踪失败:', error);
      return false;
    }
  }

  async uploadCalibration(calibrationParams: any): Promise<boolean> {
    try {
      const response = await axios.post(`${API_BASE_URL}/tracking/calibration`, {
        calibration_params: calibrationParams
      });

      return response.data.success;
    } catch (error) {
      console.error('上传标定参数失败:', error);
      return false;
    }
  }

  async getTrackingData(): Promise<TrackingData> {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracking/data`);
      if (response.data.success) {
        return response.data.data;
      }
      return {
        objects: [],
        frame_id: 0,
        timestamp: '',
        detections: 0,
        fps: 0,
        processing_time: 0
      };
    } catch (error) {
      console.error('获取追踪数据失败:', error);
      return {
        objects: [],
        frame_id: 0,
        timestamp: '',
        detections: 0,
        fps: 0,
        processing_time: 0
      };
    }
  }

  async getOCRStatus(): Promise<OCRStatus> {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracking/ocr-status`);
      if (response.data.success) {
        return response.data.data;
      }
      return {};
    } catch (error) {
      console.error('获取OCR状态失败:', error);
      return {};
    }
  }

  async getTrackingDataBackup(): Promise<TrackingData> {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracking/data`);
      if (response.data.success) {
        return response.data.data;
      }
      return {
        objects: [],
        frame_id: 0,
        timestamp: '',
        detections: 0,
        fps: 0,
        processing_time: 0
      };
    } catch (error) {
      console.error('获取追踪数据失败:', error);
      return {
        objects: [],
        frame_id: 0,
        timestamp: '',
        detections: 0,
        fps: 0,
        processing_time: 0
      };
    }
  }

  async getSystemStatus(): Promise<SystemStatus> {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracking/system-status`);
      if (response.data.success) {
        return response.data.data;
      }
      return {
        tracking: false,
        ocr: false,
        conveyor: false
      };
    } catch (error) {
      console.error('获取系统状态失败:', error);
      return {
        tracking: false,
        ocr: false,
        conveyor: false
      };
    }
  }

  async setOCRTrigger(position: number): Promise<boolean> {
    try {
      const response = await axios.post(`${API_BASE_URL}/tracking/configure`, {
        ocr_trigger_x: position
      });
      return response.data.success;
    } catch (error) {
      console.error('设置OCR触发位置失败:', error);
      return false;
    }
  }

  async reset(): Promise<boolean> {
    try {
      const response = await axios.post(`${API_BASE_URL}/tracking/reset`);
      return response.data.success;
    } catch (error) {
      console.error('重置追踪系统失败:', error);
      return false;
    }
  }

  async getCurrentFrame(type: 'raw' | 'detections' = 'raw'): Promise<string | null> {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracking/frame`, {
        params: { type }
      });
      if (response.data.success) {
        return response.data.data.frame;
      }
      return null;
    } catch (error) {
      console.error('获取视频帧失败:', error);
      return null;
    }
  }

  async getStats(): Promise<TrackingStats> {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracking/stats`);
      if (response.data.success) {
        return response.data.data;
      }
      return {
        fps: 0,
        processing_time: 0,
        frame_count: 0,
        detection_count: 0,
        active_tracks: 0,
        is_running: false,
        tracking_enabled: false,
        ocr_requests: 0,
        ocr_success: 0
      };
    } catch (error) {
      console.error('获取统计数据失败:', error);
      return {
        fps: 0,
        processing_time: 0,
        frame_count: 0,
        detection_count: 0,
        active_tracks: 0,
        is_running: false,
        tracking_enabled: false,
        ocr_requests: 0,
        ocr_success: 0
      };
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}

export const trackingAPI = new TrackingAPI();

export const startTracking = (cameraSource: number = 0) => trackingAPI.startTracking(cameraSource);
export const stopTracking = () => trackingAPI.stopTracking();
export const getCurrentObjects = () => trackingAPI.getCurrentObjects();
export const getTrackingStatus = () => trackingAPI.getTrackingStatus();
export const getTrackingStats = () => trackingAPI.getTrackingStats();
export const configureTracking = (config: any) => trackingAPI.configureTracking(config);
export const uploadCalibration = (calibrationParams: any) => trackingAPI.uploadCalibration(calibrationParams);

export const onObjectDetected = (callback: Function) => trackingAPI.on('object_detected', callback);
export const onObjectLost = (callback: Function) => trackingAPI.on('object_lost', callback);
export const onFrameProcessed = (callback: Function) => trackingAPI.on('frame_processed', callback);
export const onTrackingStatus = (callback: Function) => trackingAPI.on('tracking_status', callback);
export const onVideoFrame = (callback: Function) => trackingAPI.on('video_frame', callback);