// src/api/pipelineApi.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

export const setCustomArmSequence = async (sequence: any[]) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/pipeline/arm_sequence`, {
      sequence: sequence
    });
    return response.data;
  } catch (error) {
    console.error('设置自定义机械臂序列失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '设置序列失败'
    };
  }
};

export const getCustomArmSequence = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/pipeline/arm_sequence`);
    return response.data;
  } catch (error) {
    console.error('获取自定义机械臂序列失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '获取序列失败',
      data: { sequence: [], count: 0 }
    };
  }
};

export const startPipeline = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/pipeline/control`, {
      action: 'start'
    });
    return response.data;
  } catch (error) {
    console.error('启动流水线失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '启动失败'
    };
  }
};

export const stopPipeline = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/pipeline/control`, {
      action: 'stop'
    });
    return response.data;
  } catch (error) {
    console.error('停止流水线失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '停止失败'
    };
  }
};

export const pausePipeline = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/pipeline/control`, {
      action: 'pause'
    });
    return response.data;
  } catch (error) {
    console.error('暂停流水线失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '暂停失败'
    };
  }
};

export const resumePipeline = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/pipeline/control`, {
      action: 'resume'
    });
    return response.data;
  } catch (error) {
    console.error('恢复流水线失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '恢复失败'
    };
  }
};

export const getPipelineStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/pipeline/status`);
    return response.data;
  } catch (error) {
    console.error('获取流水线状态失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '获取状态失败'
    };
  }
};

export const getPipelineStats = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/pipeline/stats`);
    return response.data;
  } catch (error) {
    console.error('获取流水线统计信息失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '获取统计信息失败'
    };
  }
};

export const getProcessingHistory = async (limit: number = 10) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/pipeline/history`, {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    console.error('获取处理历史失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '获取历史失败',
      data: { history: [], count: 0 }
    };
  }
};

export const resetPipeline = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/pipeline/reset`);
    return response.data;
  } catch (error) {
    console.error('重置流水线失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '重置失败'
    };
  }
};

export const updatePipelineConfig = async (config: any) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/pipeline/config`, {
      config: config
    });
    return response.data;
  } catch (error) {
    console.error('更新流水线配置失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '更新配置失败'
    };
  }
};

export const pipelineWebSocketEvents = {
  onStatusUpdate: (callback: (data: any) => void) => {
    console.log('注册流水线状态更新监听器');
  },

  onError: (callback: (error: any) => void) => {
    console.log('注册流水线错误监听器');
  },

  removeAllListeners: () => {
    console.log('移除所有流水线监听器');
  }
};