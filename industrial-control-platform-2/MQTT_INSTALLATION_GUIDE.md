# MQTT代理安装和配置指南

## 问题描述
测试显示MQTT代理未运行，导致连接被拒绝错误：
```
[WinError 10061] 由于目标计算机积极拒绝，无法连接。
```

## 解决方案

### 方法1：安装Mosquitto MQTT代理（推荐）

#### Windows系统
1. **下载安装包**
   - 访问：https://mosquitto.org/download/
   - 下载Windows版本的Mosquitto

2. **安装步骤**
   - 运行下载的安装程序
   - 安装到默认路径（如：`C:\Program Files\mosquitto`）
   - 确保安装过程中选择"安装为Windows服务"

3. **启动服务**
   ```cmd
   # 以管理员身份运行命令提示符
   net start mosquitto
   ```

4. **验证安装**
   ```cmd
   # 检查服务状态
   sc query mosquitto

   # 测试连接
   mosquitto_sub -h localhost -t test
   ```

#### Linux系统 (Ubuntu/Debian)
```bash
# 安装Mosquitto
sudo apt update
sudo apt install mosquitto mosquitto-clients

# 启动服务
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

# 验证安装
sudo systemctl status mosquitto
```

#### macOS系统
```bash
# 使用Homebrew安装
brew install mosquitto

# 启动服务
brew services start mosquitto
```

### 方法2：使用Docker运行MQTT代理

#### 安装Docker
1. 下载Docker Desktop：https://www.docker.com/products/docker-desktop
2. 安装并启动Docker

#### 运行MQTT容器
```bash
# 拉取Eclipse Mosquitto镜像
docker pull eclipse-mosquitto

# 运行MQTT代理
docker run -d -p 1883:1883 -p 9001:9001 --name mosquitto eclipse-mosquitto

# 验证运行
docker ps
```

### 方法3：使用Python内置MQTT代理（开发测试用）

创建一个简单的MQTT代理用于测试：

```python
# backend/start_mqtt_broker.py
import asyncio
import websockets
import json

async def mqtt_broker(websocket, path):
    print("MQTT代理已启动")
    try:
        async for message in websocket:
            print(f"收到消息: {message}")
            # 这里可以添加消息处理逻辑
    except websockets.exceptions.ConnectionClosed:
        print("客户端断开连接")

start_server = websockets.serve(mqtt_broker, "localhost", 1883)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
```

## 验证MQTT代理运行

### 测试连接
```bash
# 发布测试消息
mosquitto_pub -h localhost -t "test/topic" -m "Hello MQTT"

# 订阅测试消息
mosquitto_sub -h localhost -t "test/topic"
```

### 使用Python测试
```python
import paho.mqtt.client as mqtt

def test_connection():
    client = mqtt.Client()
    try:
        client.connect("localhost", 1883, 60)
        print("✓ MQTT代理连接成功")
        return True
    except Exception as e:
        print(f"✗ MQTT代理连接失败: {e}")
        return False

test_connection()
```

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 检查1883端口
   netstat -an | findstr 1883

   # 如果被占用，可以修改Mosquitto配置使用其他端口
   ```

2. **防火墙阻止**
   - 确保防火墙允许1883端口通信
   - Windows: 在Windows Defender防火墙中添加例外

3. **服务启动失败**
   ```bash
   # 查看服务日志
   journalctl -u mosquitto.service  # Linux
   # 或检查Windows事件查看器
   ```

### 配置修改

如果需要修改默认配置，编辑Mosquitto配置文件：

**Windows**: `C:\Program Files\mosquitto\mosquitto.conf`
**Linux**: `/etc/mosquitto/mosquitto.conf`

添加以下配置允许匿名连接（仅用于开发）：
```
listener 1883
allow_anonymous true
```

## 下一步

1. 安装并启动MQTT代理
2. 运行测试脚本验证连接：
   ```bash
   python backend/test_mqtt_broker.py
   python backend/test_mqtt_integration.py
   ```
3. 启动后端服务测试完整功能
4. 启动前端应用测试MQTT通信

## 注意事项

- 生产环境请配置认证和加密
- 开发环境可以使用匿名连接简化测试
- 确保防火墙配置允许MQTT通信