# 工业控制平台运行指南

## 环境要求

### 系统要求
- Windows 10/11 或 Linux/macOS
- Python 3.8+
- Node.js 16+
- MQTT代理 (Mosquitto)

### 已安装的服务
- ✅ MQTT代理 (Mosquitto) - 已运行在 localhost:1883

## 启动步骤

### 第一步：启动后端服务

#### 方式1：使用Python直接运行
```bash
# 进入后端目录
cd backend

# 安装Python依赖
pip install -r requirements.txt

# 启动Flask应用
python app.py
```

#### 方式2：使用开发模式（推荐）
```bash
cd backend

# 设置开发环境变量
set FLASK_ENV=development  # Windows
# 或 export FLASK_ENV=development  # Linux/macOS

# 启动开发服务器
python app.py
```

### 第二步：启动前端服务

#### 方式1：使用npm运行
```bash
# 在项目根目录（确保package.json存在）
npm install
npm run dev
```

#### 方式2：使用Vite直接运行
```bash
# 如果npm不可用，使用npx
npx vite
```

### 第三步：访问应用

后端服务启动后，控制台会显示：
```
后端服务已启动在 http://localhost:5000
追踪API可用: http://localhost:5000/api/tracking/status
WebSocket服务已启动
MQTT服务已启用
```

前端服务启动后，控制台会显示：
```
  VITE v7.0.3  ready in 1234 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

在浏览器中访问：**http://localhost:5173**

## 验证服务状态

### 验证后端服务
```bash
# 测试API连接
curl http://localhost:5000/api/tracking/status

# 或使用浏览器访问
# http://localhost:5000/api/tracking/status
```

### 验证MQTT连接
```bash
# 使用测试脚本验证
python backend/test_mqtt_broker.py
python backend/test_mqtt_integration.py
```

### 验证前端服务
- 打开浏览器访问 http://localhost:5173
- 检查控制台无错误
- 测试追踪功能是否正常

## 故障排除

### 常见问题

#### 1. 端口被占用
```bash
# 检查端口占用
netstat -ano | findstr :5000  # Windows
lsof -i :5000                 # Linux/macOS

# 如果端口被占用，可以修改端口
# 后端: 修改 app.py 中的端口号
# 前端: 修改 vite.config.ts 中的端口配置
```

#### 2. Python依赖问题
```bash
# 重新安装依赖
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# 或使用虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

#### 3. Node.js依赖问题
```bash
# 清除缓存并重新安装
npm cache clean --force
rm -rf node_modules
rm package-lock.json
npm install
```

#### 4. MQTT连接问题
```bash
# 检查MQTT代理状态
net start mosquitto  # Windows
systemctl status mosquitto  # Linux

# 测试MQTT连接
python backend/test_mqtt_broker.py
```

### 服务启动顺序

推荐启动顺序：
1. **MQTT代理** (已运行)
2. **后端服务** (Flask应用)
3. **前端服务** (Vue应用)

## 开发模式

### 后端开发模式
启用开发模式会自动重载代码更改：
```bash
set FLASK_ENV=development
python app.py
```

### 前端开发模式
Vite默认启用热重载，代码更改会自动刷新浏览器。

## 生产部署

### 后端生产部署
```bash
# 使用生产WSGI服务器
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 前端生产构建
```bash
npm run build
```

构建后的文件在 `dist` 目录，可以部署到任何静态文件服务器。

## 服务管理

### 同时启动多个服务（Windows）
创建批处理文件 `start_all.bat`：
```batch
@echo off
echo 启动MQTT代理...
net start mosquitto

echo 启动后端服务...
cd backend
start python app.py

echo 启动前端服务...
cd ..
start npm run dev

echo 所有服务已启动！
pause
```

### 同时启动多个服务（Linux/macOS）
创建脚本文件 `start_all.sh`：
```bash
#!/bin/bash
echo "启动MQTT代理..."
sudo systemctl start mosquitto

echo "启动后端服务..."
cd backend
python app.py &

echo "启动前端服务..."
cd ..
npm run dev &

echo "所有服务已启动！"
```

## 监控服务状态

### 后端健康检查
```
http://localhost:5000/health
http://localhost:5000/api/tracking/status
```

### 前端开发服务器
```
http://localhost:5173
```

### MQTT代理状态
```
# 检查服务状态
net start mosquitto  # Windows
systemctl status mosquitto  # Linux

# 测试连接
mosquitto_sub -h localhost -t "test" -v
```

## 下一步

1. 按照上述步骤启动前后端服务
2. 访问 http://localhost:5173 测试应用
3. 如果遇到问题，参考故障排除部分
4. 查看使用说明文档了解功能使用方法

现在您可以开始使用工业控制平台了！🎉