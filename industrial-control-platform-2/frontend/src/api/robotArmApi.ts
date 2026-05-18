// src/api/robotArmApi.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

export const setJointAngle = async (joint: number, angle: number) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/robot_arm`, {
      command: 'set_joint_angle',
      params: { joint, angle }
    });
    return response.data;
  } catch (error) {
    console.error('控制机械臂失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '控制指令发送失败'
    };
  }
};

export const runSequence = async (actions: any[]) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/robot_arm`, {
      command: 'run_sequence',
      params: { actions }
    });
    return response.data;
  } catch (error) {
    console.error('执行动作序列失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '执行序列失败'
    };
  }
};

export const emergencyStop = async () => {
  try {
    const response = await axios.post(`${API_BASE_URL}/robot_arm/stop`);
    return response.data;
  } catch (error) {
    console.error('紧急停止失败:', error);
    return {
      success: false,
      message: error.response?.data?.message || '紧急停止失败'
    };
  }
};