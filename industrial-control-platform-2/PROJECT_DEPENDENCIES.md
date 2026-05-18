# 工业控制平台 - 完整依赖安装指南

## 🚀 项目概述
本项目是一个完整的工业控制系统，集成了传送带控制、机器人臂操作、物体追踪、OCR识别等功能。

## 📦 系统依赖

### 后端依赖 (Python)
- **Web框架**: Flask + Socket.IO
- **计算机视觉**: OpenCV + YOLOv8 + PyTorch
- **物体追踪**: DeepSORT
- **串口通信**: PySerial
- **GPU加速**: CUDA支持 (可选)

### 前端依赖 (Node.js)
- **框架**: Vue 3 + TypeScript
- **UI库**: Element Plus
- **3D图形**: Three.js
- **图表**: ECharts
- **通信**: Socket.IO + MQTT

## 🔧 安装步骤

### 1. 后端安装

#### 基础安装 (CPU版本)
```bash
cd backend
pip install -r requirements.txt
```

#### GPU加速安装 (推荐)
```bash
cd backend
# 安装GPU版本PyTorch
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 -f https://download.pytorch.org/whl/torch_stable.html
# 安装其他依赖
pip install -r requirements-gpu.txt
```

### 2. 前端安装
```bash
cd frontend
npm install
```

## 📋 详细依赖列表

### 后端依赖 (requirements.txt)
```
# Web框架
flask==2.3.3
flask-cors==4.0.0
flask-socketio==5.3.6
python-socketio==5.8.0

# 计算机视觉
opencv-python==4.8.1.78
ultralytics==8.0.200
numpy==1.24.3
pillow==10.0.1

# 追踪算法
deep-sort-realtime==1.3.0
filterpy==1.4.5
scipy==1.11.3

# 串口通信
pyserial==3.5

# 其他依赖
python-dotenv==1.0.0

```

### 前端依赖 (package.json)
```json
{
  "dependencies": {
    "@element-plus/icons-vue": "^2.3.1",
    "@types/three": "^0.178.0",
    "axios": "^1.10.0",
    "echarts": "^5.6.0",
    "element-plus": "^2.10.4",
    "mqttjs": "^0.0.0",
    "pinia": "^3.0.3",
    "sass": "^1.89.2",
    "socket.io-client": "^4.8.1",
    "three": "^0.178.0",
    "three.js": "^0.77.1",
    "vue": "^3.5.17",
    "vue-echarts": "^7.0.3",
    "vue-router": "^4.5.1"
  }
}
```

## 🎯 功能模块依赖

### 传送带控制
- **依赖**: `pyserial`, `flask`
- **硬件**: 串口通信支持

### 机器人臂控制
- **依赖**: `pyserial`, `flask`, `numpy`
- **硬件**: 串口通信支持

### 物体追踪系统
- **依赖**: `opencv-python`, `ultralytics`, `deep-sort-realtime`, `torch`
- **硬件**: 摄像头 + GPU(推荐)

### OCR识别系统
- **依赖**: `pillow`, `requests`
- **服务**: 需要OCR服务运行

### 3D可视化
- **依赖**: `three`, `@types/three`
- **浏览器**: WebGL支持

## 🔍 GPU支持检查

### 检查NVIDIA驱动
```bash
nvidia-smi
```

### 检查CUDA版本
```bash
nvcc --version
```

### 检查PyTorch GPU支持
```python
import torch
print(f"CUDA可用: {torch.cuda.is_available()}")
print(f"GPU设备: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else '无'}")
```

## 🚀 启动项目

### 启动后端
```bash
cd backend
python app.py
```

### 启动前端
```bash
cd frontend
npm run dev
```

## 📊 性能优化建议

### CPU版本
- 降低视频分辨率
- 减少检测频率
- 使用更小的YOLO模型

### GPU版本
- 启用混合精度推理
- 优化batch size
- 使用GPU内存清理

## 🔧 故障排除

### 常见问题

1. **摄像头无法打开**
   - 检查摄像头权限
   - 尝试不同的摄像头索引
   - 检查驱动程序

2. **GPU未启用**
   - 检查NVIDIA驱动
   - 安装CUDA版本PyTorch
   - 参考 `backend/GPU_INSTALLATION_GUIDE.md`

3. **串口通信失败**
   - 检查串口号和波特率
   - 确认硬件连接
   - 检查权限设置

4. **前端构建失败**
   - 清除node_modules重新安装
   - 检查Node.js版本
   - 更新npm到最新版本

## 📁 项目结构
```
industrial-control-platform/
├── backend/                 # Flask后端
│   ├── app.py              # 主应用
│   ├── api/                # API路由
│   ├── services/           # 业务逻辑
│   ├── model/              # AI模型
│   └── requirements.txt    # Python依赖
├── frontend/               # Vue前端
│   ├── src/                # 源代码
│   ├── package.json        # Node.js依赖
│   └── vite.config.ts      # 构建配置
└── docs/                   # 文档
    ├── PROJECT_DEPENDENCIES.md
    └── GPU_INSTALLATION_GUIDE.md
```

## 📞 技术支持
如遇到安装问题，请检查：
1. 系统环境是否符合要求
2. 依赖版本是否匹配
3. 硬件设备是否正常
4. 查看相关日志文件