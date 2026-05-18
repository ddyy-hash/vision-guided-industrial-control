#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import websocket
import json
import time
import threading
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketTestClient:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.connected = False
        self.message_count = 0

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.message_count += 1
            logger.info(f"收到消息 #{self.message_count}: {data.get('type', 'unknown')}")

            if data.get('type') == 'pipeline_status':
                logger.info(f"流水线状态: {data.get('status', 'unknown')}")
            elif data.get('type') == 'tracking_status':
                logger.info(f"追踪状态: {data.get('status', 'unknown')}")
            elif data.get('type') == 'video_frame':
                logger.info(f"收到视频帧，大小: {len(str(data.get('frame', '')))} 字符")
            elif data.get('type') == 'object_detected':
                logger.info(f"检测到物体: {data.get('object', {}).get('class_name', 'unknown')}")
            elif data.get('type') == 'connection_status':
                logger.info(f"连接状态: {data.get('status', 'unknown')}")
            else:
                logger.info(f"其他消息类型: {data}")

        except json.JSONDecodeError:
            logger.info(f"收到非JSON消息: {message}")
        except Exception as e:
            logger.error(f"处理消息错误: {e}")

    def on_error(self, ws, error):
        logger.error(f"WebSocket错误: {error}")
        self.connected = False

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket连接关闭 - 状态码: {close_status_code}, 消息: {close_msg}")
        self.connected = False

    def on_open(self, ws):
        logger.info("WebSocket连接已建立")
        self.connected = True

        def run_test_sequence():
            time.sleep(1)

            logger.info("测试1: 获取流水线状态")
            ws.send(json.dumps({
                'type': 'get_pipeline_status'
            }))

            time.sleep(2)

            logger.info("测试2: 启动追踪")
            ws.send(json.dumps({
                'type': 'start_tracking',
                'camera_source': 0
            }))

            time.sleep(3)

            logger.info("测试3: 获取追踪物体")
            ws.send(json.dumps({
                'type': 'get_tracking_objects'
            }))

            time.sleep(3)

            logger.info("测试4: 启动流水线")
            ws.send(json.dumps({
                'type': 'start_pipeline'
            }))

            time.sleep(5)

            logger.info("测试5: 停止追踪")
            ws.send(json.dumps({
                'type': 'stop_tracking'
            }))

            time.sleep(2)

            logger.info("测试6: 停止流水线")
            ws.send(json.dumps({
                'type': 'stop_pipeline'
            }))

            time.sleep(2)

            logger.info("测试序列完成，等待更多消息...")

        test_thread = threading.Thread(target=run_test_sequence)
        test_thread.daemon = True
        test_thread.start()

    def connect(self):
        try:
            websocket.enableTrace(True)

            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )

            logger.info(f"正在连接到: {self.url}")
            self.ws.run_forever()

        except Exception as e:
            logger.error(f"连接WebSocket失败: {e}")
            self.connected = False

def test_websocket_connection():
    print("=" * 60)
    print("WebSocket连接测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    test_urls = [
        "ws://localhost:5000/socket.io/?EIO=4&transport=websocket",
        "ws://localhost:5000/socket.io/?EIO=3&transport=websocket",
        "ws://localhost:5000/socket.io/?transport=websocket"
    ]

    for url in test_urls:
        print(f"\n测试URL: {url}")
        client = WebSocketTestClient(url)

        try:
            test_thread = threading.Thread(target=client.connect)
            test_thread.daemon = True
            test_thread.start()

            time.sleep(30)

            if client.connected:
                logger.info("✅ WebSocket连接测试成功")
                logger.info(f"收到消息数量: {client.message_count}")
            else:
                logger.warning("❌ WebSocket连接失败或已断开")

        except KeyboardInterrupt:
            logger.info("测试被用户中断")
            break
        except Exception as e:
            logger.error(f"测试过程中出现错误: {e}")

        finally:
            if client.ws:
                client.ws.close()
            time.sleep(2)

    print("\n" + "=" * 60)
    print("WebSocket连接测试完成")
    print("=" * 60)

def test_http_endpoints():
    print("\n=== 测试HTTP端点 ===")

    import requests

    endpoints = [
        "http://localhost:5000/api/pipeline/status",
        "http://localhost:5000/api/tracking/status",
        "http://localhost:5000/api/conveyor/status"
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {endpoint} - 正常")
                print(f"   响应: {data.get('success', False)}")
            else:
                print(f"❌ {endpoint} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - 错误: {e}")

if __name__ == "__main__":
    print("开始WebSocket连接测试...")

    test_http_endpoints()

    test_websocket_connection()

    print("\n测试完成！")