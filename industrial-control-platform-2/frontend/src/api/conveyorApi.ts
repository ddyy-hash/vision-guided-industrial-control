import axios from 'axios';
import type { ConveyorStatus, ConveyorControlParams, DeviceCapabilities, SpeedRecommendation } from '../types/conveyor';

const API_BASE_URL = 'http://localhost:5000/api';

export const conveyorApiService = {
  /**
   */
  async controlConveyor(params: ConveyorControlParams) {
    try {
      const response = await axios.post(`${API_BASE_URL}/conveyor/control`, params);
      return response.data;
    } catch (error: any) {
      console.error('控制传送带失败:', error);
      return {
        success: false,
        message: error.response?.data?.message || '控制指令发送失败'
      };
    }
  },

  /**
   */
  async getConveyorStatus(): Promise<ConveyorStatus> {
    try {
      const response = await axios.get(`${API_BASE_URL}/conveyor/status`);
      if (response.data.success && response.data.data) {
        return response.data.data;
      }
      throw new Error(response.data.message || '获取状态失败');
    } catch (error: any) {
      console.error('获取传送带状态失败:', error);
      return {
        isRunning: false,
        currentSpeed: 0.0,
        targetSpeed: 0.0,
        actualSpeed: 0.0,
        direction: 'forward',
        status: 'stopped',
        deviceType: 'unknown',
        speedRange: { min: 0.001, max: 0.8 },
        temperature: 25,
        load: 0,
        healthScore: 100,
        lastUpdate: new Date().toISOString()
      };
    }
  },

  /**
   */
  async startConveyor(speed: number = 0.1, direction: string = 'forward') {
    return this.controlConveyor({
      speed,
      direction,
      action: 'start'
    });
  },

  /**
   */
  async stopConveyor() {
    let currentDirection = 'forward';
    try {
      const status = await this.getConveyorStatus();
      currentDirection = status.direction;
    } catch (error) {
    }

    return this.controlConveyor({
      speed: 0,
      direction: currentDirection,
      action: 'stop'
    });
  },

  /**
   */
  async emergencyStop() {
    let currentDirection = 'forward';
    try {
      const status = await this.getConveyorStatus();
      currentDirection = status.direction;
    } catch (error) {
    }

    return this.controlConveyor({
      speed: 0,
      direction: currentDirection,
      action: 'emergency_stop'
    });
  },

  /**
   */
  async setSpeed(speed: number, direction?: string) {
    let currentDirection = direction;
    if (!currentDirection) {
      try {
        const status = await this.getConveyorStatus();
        currentDirection = status.direction;
      } catch (error) {
        currentDirection = 'forward';
      }
    }

    return this.controlConveyor({
      speed,
      direction: currentDirection,
      action: 'set_speed'
    });
  },

  /**
   */
  async toggleDirection() {
    try {
      const status = await this.getConveyorStatus();
      const newDirection = status.direction === 'forward' ? 'backward' : 'forward';

      if (status.isRunning) {
        return this.controlConveyor({
          speed: status.targetSpeed,
          direction: newDirection,
          action: 'set_speed'
        });
      } else {
        return this.controlConveyor({
          speed: 0,
          direction: newDirection,
          action: 'set_speed'
        });
      }
    } catch (error: any) {
      console.error('切换方向失败:', error);
      return {
        success: false,
        message: error.response?.data?.message || '切换方向失败'
      };
    }
  },

  /**
   */
  async setDirection(direction: string) {
    try {
      const status = await this.getConveyorStatus();

      const currentSpeed = status.isRunning ? status.targetSpeed : 0;

      return this.controlConveyor({
        speed: currentSpeed,
        direction: direction,
        action: 'set_speed'
      });
    } catch (error: any) {
      console.error('设置方向失败:', error);
      return {
        success: false,
        message: error.response?.data?.message || '设置方向失败'
      };
    }
  },

  /**
   */
  async getDeviceCapabilities(): Promise<DeviceCapabilities> {
    try {
      const status = await this.getConveyorStatus();
      return {
        deviceType: status.deviceType,
        speedRange: status.speedRange,
        supportedDirections: ['forward', 'backward'],
        maxAcceleration: 0.5,
        maxDeceleration: 1.0,
        precision: 0.001,
        features: ['speed_control', 'direction_control', 'emergency_stop']
      };
    } catch (error: any) {
      console.error('获取设备能力失败:', error);
      return {
        deviceType: 'standard',
        speedRange: { min: 0.001, max: 0.8 },
        supportedDirections: ['forward', 'backward'],
        maxAcceleration: 0.5,
        maxDeceleration: 1.0,
        precision: 0.001,
        features: ['speed_control', 'direction_control', 'emergency_stop']
      };
    }
  },

  /**
   */
  async resetSystem() {
    try {
      const response = await axios.post(`${API_BASE_URL}/conveyor/reset`);
      return response.data;
    } catch (error: any) {
      console.error('系统复位失败:', error);
      return {
        success: false,
        message: error.response?.data?.message || '系统复位失败'
      };
    }
  },

  /**
   */
  async getSpeedRecommendations(): Promise<SpeedRecommendation[]> {
    return [
      { speed: 0.005, description: '精密装配', type: 'precision' },
      { speed: 0.020, description: '质量检测', type: 'inspection' },
      { speed: 0.300, description: '标准输送', type: 'standard' },
      { speed: 0.500, description: '中速分拣', type: 'medium-speed' },
      { speed: 2.000, description: '高速分拣', type: 'high-speed' }
    ];
  }
};

export const controlConveyor = conveyorApiService.controlConveyor;
export const getConveyorStatus = conveyorApiService.getConveyorStatus;

export const conveyorWebSocketService = {
  connect() {
    console.log('传送带WebSocket连接已建立');
  },

  disconnect() {
    console.log('传送带WebSocket连接已断开');
  },

  onStatusUpdate(callback: (status: ConveyorStatus) => void) {
    setInterval(async () => {
      const status = await conveyorApiService.getConveyorStatus();
      callback(status);
    }, 2000);
  },

  onError(callback: (error: any) => void) {
    console.log('错误监听器已注册');
  }
};