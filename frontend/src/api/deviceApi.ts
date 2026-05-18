import axios from 'axios';
import { io, Socket } from 'socket.io-client';
import { DeviceInfo, DeviceStatus, ConnectionHistory, DeviceConfig, DeviceStatistics, DeviceStatusDetail } from '../types/device';

const API_BASE_URL = 'http://localhost:5000/api';

const RETRY_CONFIG = {
  maxRetries: 3,
  retryDelay: 1000,
  timeout: 15000,
};

const requestCache = new Map();

const deviceApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: RETRY_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

const retryRequest = async (config: any, retries: number = RETRY_CONFIG.maxRetries): Promise<any> => {
  try {
    return await deviceApi(config);
  } catch (error: any) {
    if (retries > 0 && error.code !== 'ECONNABORTED' && error.response?.status !== 401) {
      console.log(`[Device API] 请求失败，${RETRY_CONFIG.retryDelay}ms后重试 (剩余${retries}次)`);
      await new Promise(resolve => setTimeout(resolve, RETRY_CONFIG.retryDelay));
      return retryRequest(config, retries - 1);
    }
    throw error;
  }
};

deviceApi.interceptors.request.use(
  (config) => {
    if (config.method?.toLowerCase() === 'get') {
      const cacheKey = `${config.url}${JSON.stringify(config.params || {})}`;
      config.cacheKey = cacheKey;

      if (requestCache.has(cacheKey)) {
        const cachedData = requestCache.get(cacheKey);
        if (Date.now() - cachedData.timestamp < 5000) {
          console.log(`[Device API] 使用缓存: ${config.url}`);
          return Promise.reject({
            __CACHED_RESPONSE__: true,
            data: cachedData.data
          });
        }
      }
    }

    console.log(`[Device API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

deviceApi.interceptors.response.use(
  (response) => {
    if (response.config.method?.toLowerCase() === 'get' && response.config.cacheKey) {
      requestCache.set(response.config.cacheKey, {
        data: response.data,
        timestamp: Date.now()
      });
    }
    return response;
  },
  (error) => {
    if (error.__CACHED_RESPONSE__) {
      return Promise.resolve({
        data: error.data,
        status: 200,
        statusText: 'OK',
        headers: {},
        config: error.config
      });
    }

    console.error('[Device API] 请求失败:', error);
    return Promise.reject(error);
  }
);

export const deviceApiService = {
  async getDevices(): Promise<DeviceInfo[]> {
    try {
      const response = await retryRequest({
        method: 'get',
        url: '/devices'
      });

      console.log('[Device API] 获取设备列表响应:', response);

      let devices = [];
      const responseData = response.data;

      if (responseData && responseData.data) {
        if (responseData.data.data && Array.isArray(responseData.data.data)) {
          devices = responseData.data.data;
        } else if (Array.isArray(responseData.data)) {
          devices = responseData.data;
        }
      } else if (Array.isArray(responseData)) {
        devices = responseData;
      }

      console.log('[Device API] 解析后的设备列表:', devices);

      return devices.map((device: any) => ({
        device_id: device.device_id || `unknown_${Date.now()}`,
        name: device.name || '未知设备',
        device_type: device.device_type || 'unknown',
        model: device.model || '未知型号',
        manufacturer: device.manufacturer || '未知厂商',
        serial_number: device.serial_number || `SN_${device.device_id}`,
        firmware_version: device.firmware_version || '1.0.0',
        connection_type: device.connection_type || 'serial',
        connection_info: device.connection_info || '',
        connection_params: device.connection_params || {},
        last_seen: device.last_seen || new Date().toISOString(),
        created_at: device.created_at || new Date().toISOString(),
        updated_at: device.updated_at || new Date().toISOString(),
        is_online: device.is_online || false,
        status: device.status || 'disconnected',
        pairing_status: device.pairing_status || 'unpaired',
        description: device.description || '',
        tags: device.tags || [],
        capabilities: device.capabilities || [],
        health_score: device.health_score || 85,
        port: device.port || '',
        auto_connect: device.auto_connect || false,
        last_connection_time: device.last_connection_time || null,
        connection_count: device.connection_count || 0
      }));
    } catch (error) {
      console.error('获取设备列表失败:', error);
      return [];
    }
  },

  async getConnectedDevices(): Promise<DeviceInfo[]> {
    try {
      const response = await deviceApi.get('/devices/connected');
      return response.data?.data?.data || response.data?.data || [];
    } catch (error) {
      console.error('获取已连接设备列表失败:', error);
      throw error;
    }
  },

  async connectDevice(deviceId: string): Promise<void> {
    try {
      await retryRequest({
        method: 'post',
        url: `/devices/${deviceId}/connect`,
        timeout: 20000
      });
    } catch (error) {
      console.error(`连接设备 ${deviceId} 失败:`, error);
      throw error;
    }
  },

  async disconnectDevice(deviceId: string): Promise<void> {
    try {
      await deviceApi.post(`/devices/${deviceId}/disconnect`);
    } catch (error) {
      console.error(`断开设备 ${deviceId} 连接失败:`, error);
      throw error;
    }
  },

  async scanDevices(): Promise<void> {
    try {
      await deviceApi.post('/devices/scan');
    } catch (error) {
      console.error('手动扫描设备失败:', error);
      throw error;
    }
  },

  async startAutoScan(): Promise<void> {
    try {
      await deviceApi.post('/devices/scan/start');
    } catch (error) {
      console.error('启动自动扫描失败:', error);
      throw error;
    }
  },

  async stopAutoScan(): Promise<void> {
    try {
      await deviceApi.post('/devices/scan/stop');
    } catch (error) {
      console.error('停止自动扫描失败:', error);
      throw error;
    }
  },

  async getDeviceDetails(deviceId: string): Promise<DeviceInfo> {
    try {
      const response = await deviceApi.get(`/devices/${deviceId}`);
      return response.data?.data?.data?.device_info || response.data?.data?.device_info;
    } catch (error) {
      console.error(`获取设备 ${deviceId} 详情失败:`, error);
      throw error;
    }
  },

  async getDeviceHistory(deviceId: string, limit: number = 50): Promise<ConnectionHistory[]> {
    try {
      const response = await deviceApi.get(`/devices/${deviceId}/history`, {
        params: { limit }
      });
      return response.data?.data || response.data || [];
    } catch (error) {
      console.error(`获取设备 ${deviceId} 连接历史失败:`, error);
      throw error;
    }
  },

  async getDeviceConfig(deviceId: string): Promise<DeviceConfig> {
    try {
      const response = await deviceApi.get(`/devices/${deviceId}/config`);
      return response.data?.data?.data || response.data?.data || {};
    } catch (error) {
      console.error(`获取设备 ${deviceId} 配置失败:`, error);
      throw error;
    }
  },

  async saveDeviceConfig(deviceId: string, config: DeviceConfig): Promise<void> {
    try {
      await deviceApi.post(`/devices/${deviceId}/config`, config);
    } catch (error) {
      console.error(`保存设备 ${deviceId} 配置失败:`, error);
      throw error;
    }
  },

  async getStatistics(): Promise<DeviceStatistics> {
    try {
      const response = await deviceApi.get('/devices/statistics');
      return response.data?.data?.data || response.data?.data || {};
    } catch (error) {
      console.error('获取设备统计信息失败:', error);
      throw error;
    }
  },

  async cleanupDevices(days: number = 30): Promise<{ cleaned_count: number }> {
    try {
      const response = await deviceApi.post('/devices/cleanup', { days });
      return response.data?.data?.data || response.data?.data || { cleaned_count: 0 };
    } catch (error) {
      console.error('清理旧设备失败:', error);
      throw error;
    }
  },

  async deleteDevice(deviceId: string): Promise<void> {
    try {
      await deviceApi.delete(`/devices/${deviceId}`);
    } catch (error) {
      console.error(`删除设备 ${deviceId} 失败:`, error);
      throw error;
    }
  },

  async getDeviceStatus(deviceId: string): Promise<DeviceStatus> {
    try {
      const response = await deviceApi.get(`/devices/${deviceId}/status`);
      return response.data?.data?.data || response.data?.data;
    } catch (error) {
      console.error(`获取设备 ${deviceId} 状态失败:`, error);
      throw error;
    }
  },

  async createPairingRequest(deviceId: string): Promise<{ pairing_id: string }> {
    try {
      const response = await deviceApi.post(`/devices/pairing/request`, {
        device_id: deviceId
      });

      console.log('[Device API] 创建设备配对请求响应:', response);

      const responseData = response.data;

      if (responseData && responseData.success) {
        if (responseData.data && responseData.data.pairing_id) {
          return responseData.data;
        }
        if (responseData.pairing_id) {
          return { pairing_id: responseData.pairing_id };
        }
      }

      console.error('[Device API] 配对请求响应格式错误:', responseData);
      throw new Error('配对请求响应格式错误');

    } catch (error) {
      console.error(`创建设备 ${deviceId} 配对请求失败:`, error);
      throw error;
    }
  },

  async confirmPairing(
    pairingId: string,
    deviceType: string,
    customName?: string,
    autoConnect: boolean = true
  ): Promise<void> {
    try {
      await deviceApi.post(`/devices/pairing/confirm`, {
        pairing_id: pairingId,
        device_type: deviceType,
        custom_name: customName,
        auto_connect: autoConnect
      });
    } catch (error) {
      console.error(`确认配对 ${pairingId} 失败:`, error);
      throw error;
    }
  },

  async getPairingHistory(): Promise<any[]> {
    try {
      const response = await deviceApi.get('/devices/pairing/history');
      return response.data?.data?.data || response.data?.data || [];
    } catch (error) {
      console.error('获取配对历史失败:', error);
      throw error;
    }
  },

  async getPairedDevices(): Promise<any[]> {
    try {
      const response = await deviceApi.get('/devices/pairing/paired');
      return response.data?.data?.data || response.data?.data || [];
    } catch (error) {
      console.error('获取已配对设备失败:', error);
      throw error;
    }
  },

  async unpairDevice(deviceId: string): Promise<void> {
    try {
      await deviceApi.post(`/devices/${deviceId}/unpair`);
    } catch (error) {
      console.error(`取消设备 ${deviceId} 配对失败:`, error);
      throw error;
    }
  },

  async updatePairingInfo(deviceId: string, updates: any): Promise<void> {
    try {
      await deviceApi.post(`/devices/pairing/update`, {
        device_id: deviceId,
        ...updates
      });
    } catch (error) {
      console.error(`更新设备 ${deviceId} 配对信息失败:`, error);
      throw error;
    }
  },

  async getPairingStatus(pairingId: string): Promise<any> {
    try {
      const response = await deviceApi.get(`/devices/pairing/status/${pairingId}`);
      return response.data?.data;
    } catch (error) {
      console.error(`获取配对请求 ${pairingId} 状态失败:`, error);
      throw error;
    }
  },

  async deletePairingRecord(deviceId: string): Promise<void> {
    try {
      await deviceApi.delete(`/devices/pairing/record/${deviceId}`);
    } catch (error) {
      console.error(`删除设备 ${deviceId} 配对记录失败:`, error);
      throw error;
    }
  },

  async getDeviceRealTimeData(deviceId: string): Promise<DeviceStatusDetail> {
    try {
      const response = await deviceApi.get(`/devices/${deviceId}/status/realtime`);
      return response.data?.data?.data || response.data?.data || {};
    } catch (error) {
      console.error(`获取设备 ${deviceId} 实时数据失败:`, error);
      throw error;
    }
  },

  async getDevicesRealTimeData(deviceIds: string[]): Promise<DeviceStatusDetail[]> {
    try {
      const limitedDeviceIds = deviceIds.slice(0, 10);

      const response = await retryRequest({
        method: 'post',
        url: '/devices/status/realtime/batch',
        data: {
          device_ids: limitedDeviceIds
        },
        timeout: 15000
      });

      console.log('[Device API] 批量获取设备实时数据响应:', response);

      const responseData = response.data;

      if (responseData && responseData.success) {
        return responseData.data || [];
      } else if (Array.isArray(responseData)) {
        return responseData;
      } else if (responseData && responseData.data && Array.isArray(responseData.data)) {
        return responseData.data;
      }

      console.warn('[Device API] 未知的响应格式:', responseData);
      return [];
    } catch (error) {
      console.error('获取批量设备实时数据失败:', error);
      return [];
    }
  },

  async getDevicePerformanceMetrics(deviceId: string, timeRange: string = '1h'): Promise<any> {
    try {
      const response = await deviceApi.get(`/devices/${deviceId}/metrics`, {
        params: { time_range: timeRange }
      });
      return response.data?.data?.data || response.data?.data || [];
    } catch (error) {
      console.error(`获取设备 ${deviceId} 性能指标失败:`, error);
      throw error;
    }
  },

  async getDeviceSensorData(deviceId: string, sensorType: string): Promise<any> {
    try {
      const response = await deviceApi.get(`/devices/${deviceId}/sensors/${sensorType}`);
      return response.data?.data?.data || response.data?.data || {};
    } catch (error) {
      console.error(`获取设备 ${deviceId} 传感器数据失败:`, error);
      throw error;
    }
  }
};

export interface DeviceConnectedEvent {
  device_id: string;
  name: string;
  type: string;
  connection_time: string;
}

export interface DeviceDisconnectedEvent {
  device_id: string;
  name: string;
  type: string;
  disconnect_time: string;
}

export interface DeviceErrorEvent {
  device_id: string;
  error: string;
  timestamp: string;
}

export interface DeviceStatusUpdatedEvent {
  device_id: string;
  status: DeviceStatus;
  timestamp: string;
}

export interface DeviceWebSocketHandlers {
  onDeviceConnected?: (data: DeviceConnectedEvent) => void;
  onDeviceDisconnected?: (data: DeviceDisconnectedEvent) => void;
  onDeviceError?: (data: DeviceErrorEvent) => void;
  onDeviceStatusUpdated?: (data: DeviceStatusUpdatedEvent) => void;
}

export class DeviceWebSocketService {
  private socket: Socket | null = null;
  private handlers: DeviceWebSocketHandlers = {};
  private reconnectInterval: number = 5000;
  private reconnectTimer: any = null;
  private isConnected: boolean = false;

  constructor(private wsUrl: string = 'http://localhost:5000') {}

  connect(): void {
    try {
      this.socket = io(this.wsUrl, {
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      });

      this.socket.on('connect', () => {
        console.log('[Device WebSocket] 连接已建立', this.socket?.id);
        this.isConnected = true;
        this.clearReconnectTimer();
      });

      this.socket.on('device_connected', (data: DeviceConnectedEvent) => {
        if (this.handlers.onDeviceConnected) {
          this.handlers.onDeviceConnected(data);
        }
      });

      this.socket.on('device_disconnected', (data: DeviceDisconnectedEvent) => {
        if (this.handlers.onDeviceDisconnected) {
          this.handlers.onDeviceDisconnected(data);
        }
      });

      this.socket.on('device_error', (data: DeviceErrorEvent) => {
        if (this.handlers.onDeviceError) {
          this.handlers.onDeviceError(data);
        }
      });

      this.socket.on('device_status_updated', (data: DeviceStatusUpdatedEvent) => {
        if (this.handlers.onDeviceStatusUpdated) {
          this.handlers.onDeviceStatusUpdated(data);
        }
      });

      this.socket.on('disconnect', () => {
        console.log('[Device WebSocket] 连接已关闭');
        this.isConnected = false;
        this.scheduleReconnect();
      });

      this.socket.on('connect_error', (error) => {
        console.error('[Device WebSocket] 连接错误:', error);
        this.isConnected = false;
      });

    } catch (error) {
      console.error('[Device WebSocket] 连接失败:', error);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.clearReconnectTimer();
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.isConnected = false;
  }

  private handleMessage(event: MessageEvent): void {
    console.warn('[Device WebSocket] 不应调用此方法，请使用事件监听器');
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = setTimeout(() => {
      console.log('[Device WebSocket] 尝试重新连接...');
      this.connect();
    }, this.reconnectInterval);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  registerHandlers(handlers: DeviceWebSocketHandlers): void {
    this.handlers = { ...this.handlers, ...handlers };
  }

  getConnectionStatus(): boolean {
    return this.isConnected;
  }

  sendMessage(type: string, payload: any): void {
    if (this.socket && this.isConnected) {
      this.socket.emit(type, payload);
    } else {
      console.warn('[Device WebSocket] WebSocket未连接，无法发送消息');
    }
  }
}

export const deviceWebSocketService = new DeviceWebSocketService();

export default deviceApiService;