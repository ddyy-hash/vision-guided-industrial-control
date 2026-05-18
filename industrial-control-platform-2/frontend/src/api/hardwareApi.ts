/*import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

export const fetchHardwareStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/status`);
    return response.data;
  } catch (error) {
    console.error('获取硬件状态失败:', error);
    return null;
  }
};

export const controlRobotArm = async (joint: number, angle: number) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/robot_arm/control`, {
      joint,
      angle
    });
    return response.data;
  } catch (error) {
    console.error('控制机械臂失败:', error);
    return { success: false, message: '控制指令发送失败' };
  }
};

export const controlConveyor = async (speed: number, direction: string) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/conveyor/control`, {
      speed,
      direction
    });
    return response.data;
  } catch (error) {
    console.error('控制传送带失败:', error);
    return { success: false, message: '控制指令发送失败' };
  }
};*/