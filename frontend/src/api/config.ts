/**
 */

export const API_CONFIG = {
  BASE_URL: 'http://localhost:5000',

  ENDPOINTS: {
    PIPELINE: {
      STATUS: '/api/pipeline/status',
      CONTROL: '/api/pipeline/control',
      CONFIG: '/api/pipeline/config',
      STATS: '/api/pipeline/stats',
      HISTORY: '/api/pipeline/history',
      RESET: '/api/pipeline/reset',
      HEALTH: '/api/pipeline/health'
    },

    DEVICES: {
      LIST: '/api/devices',
      CONNECTED: '/api/devices/connected',
      STATISTICS: '/api/devices/statistics',
      REALTIME_DATA: '/api/devices/status/realtime/batch'
    },

    CONVEYOR: {
      STATUS: '/api/conveyor/status',
      CONTROL: '/api/conveyor/control',
      RESET: '/api/conveyor/reset'
    },

    ROBOT_ARM: {
      CONTROL: '/api/robot_arm',
      STOP: '/api/robot_arm/stop'
    },

    TRACKING: {
      START: '/api/tracking/start',
      STOP: '/api/tracking/stop',
      STATUS: '/api/tracking/status',
      CONFIG: '/api/tracking/config'
    },

    ENERGY: {
      CONTROL: '/api/realtime_energy/control',
      STATUS: '/api/realtime_energy/status'
    },

    OCR: {
      DETECT: '/api/energy_ocr/detect',
      STATUS: '/api/energy_ocr/status'
    }
  },

  TIMEOUT: {
    DEFAULT: 10000,
    UPLOAD: 30000,
    LONG: 60000
  },

  RETRY: {
    MAX_ATTEMPTS: 3,
    DELAY: 1000
  }
};

export function buildUrl(endpoint: string): string {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(buildUrl('/api/status'), {
      method: 'GET',
      timeout: API_CONFIG.TIMEOUT.DEFAULT
    });
    return response.ok;
  } catch (error) {
    console.error('API健康检查失败:', error);
    return false;
  }
}

export function getApiConnectionStatus(): {
  baseUrl: string;
  available: boolean;
  lastCheck: Date;
} {
  return {
    baseUrl: API_CONFIG.BASE_URL,
    available: false,
    lastCheck: new Date()
  };
}