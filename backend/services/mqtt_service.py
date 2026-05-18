import paho.mqtt.client as mqtt
import json
import logging
import threading
import time
from typing import Dict, Callable, Any, Optional
import base64
import cv2
import numpy as np
import uuid
import random
import socket

logger = logging.getLogger(__name__)

class MQTTService:

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.client = None
        self.is_connected = False
        self.callbacks = {}
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.last_reconnect_time = 0
        self.min_reconnect_interval = 5

        self.broker_host = self.config.get('mqtt_broker_host', 'localhost')
        self.broker_port = self.config.get('mqtt_broker_port', 1883)
        base_client_id = self.config.get('mqtt_client_id', 'conveyor_tracking_system')
        self.client_id = f"{base_client_id}_{uuid.uuid4().hex[:8]}"
        self.username = self.config.get('mqtt_username')
        self.password = self.config.get('mqtt_password')

        self.topics = {
            'video_stream': 'conveyor/tracking/video',
            'object_data': 'conveyor/tracking/objects',
            'tracking_stats': 'conveyor/tracking/stats',
            'system_status': 'conveyor/system/status',
            'control_commands': 'conveyor/control/commands',
            'error_alerts': 'conveyor/alerts/errors'
        }

        self.video_quality = self.config.get('video_quality', 20)
        self.target_fps = self.config.get('target_fps', 30)
        self.enable_binary_video = self.config.get('enable_binary_video', True)

    def _cleanup_old_connection(self):
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                logger.debug("旧连接资源已清理")
            except Exception as e:
                logger.debug(f"清理旧连接时发生错误: {e}")
            finally:
                self.client = None

    def connect(self) -> bool:
        try:
            self._cleanup_old_connection()

            self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)

            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish

            self.client.will_set(self.topics['system_status'],
                               json.dumps({'status': 'offline', 'timestamp': time.time()}),
                               qos=1, retain=True)

            logger.info(f"正在连接到MQTT代理: {self.broker_host}:{self.broker_port} (Client ID: {self.client_id})")

            try:
                self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            except socket.error as e:
                if hasattr(e, 'errno') and e.errno == 10055:
                    logger.error("系统端口耗尽，等待端口回收后再重连")
                    self._handle_port_exhaustion()
                    return False
                else:
                    raise e

            self.client.loop_start()

            for i in range(10):
                if self.is_connected:
                    break
                time.sleep(0.1)

            if self.is_connected:
                logger.info("MQTT连接成功")
                self._subscribe_to_topics()
                self._publish_system_status('online')
                return True
            else:
                logger.error("MQTT连接超时")
                return False

        except Exception as e:
            logger.error(f"MQTT连接失败: {e}")
            return False

    def disconnect(self):
        if self.client:
            self._publish_system_status('offline')
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            logger.info("MQTT连接已断开")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("MQTT代理连接成功")
        else:
            self.is_connected = False
            error_messages = {
                1: "协议版本错误",
                2: "客户端标识符无效",
                3: "服务器不可用",
                4: "用户名或密码错误",
                5: "未授权"
            }
            error_msg = error_messages.get(rc, f"未知错误代码: {rc}")
            logger.error(f"MQTT连接失败: {error_msg}")

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        if rc != 0:
            logger.warning(f"MQTT意外断开，将尝试重连 (代码: {rc})")
            threading.Timer(1.0, self._safe_reconnect).start()
        else:
            logger.info("MQTT正常断开")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload

            if topic in self.callbacks:
                for callback in self.callbacks[topic]:
                    try:
                        if payload:
                            data = json.loads(payload.decode('utf-8'))
                        else:
                            data = {}
                        callback(data)
                    except json.JSONDecodeError:
                        callback(payload)
                    except Exception as e:
                        logger.error(f"消息回调处理错误: {e}")

        except Exception as e:
            logger.error(f"处理MQTT消息错误: {e}")

    def _on_publish(self, client, userdata, mid):
        logger.debug(f"消息发布成功 (消息ID: {mid})")

    def _safe_reconnect(self):
        current_time = time.time()
        time_since_last_reconnect = current_time - self.last_reconnect_time

        if time_since_last_reconnect < self.min_reconnect_interval:
            wait_time = self.min_reconnect_interval - time_since_last_reconnect
            logger.info(f"重连过快，等待 {wait_time:.1f} 秒")
            time.sleep(wait_time)

        self._handle_reconnection()

    def _handle_reconnection(self):
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            wait_time = min(2 ** self.reconnect_attempts, 30)

            self.last_reconnect_time = time.time()

            logger.info(f"等待 {wait_time} 秒后尝试第 {self.reconnect_attempts} 次重连")

            self._cleanup_old_connection()

            time.sleep(wait_time)
            self.connect()
        else:
            logger.error("达到最大重连次数，停止重连")
            self.reconnect_attempts = 0
            self.last_reconnect_time = time.time()

    def _subscribe_to_topics(self):
        if not self.client:
            logger.error("MQTT客户端未初始化，无法订阅主题")
            return

        for topic in self.topics.values():
            try:
                self.client.subscribe(topic, qos=1)
                logger.debug(f"已订阅主题: {topic}")
            except Exception as e:
                logger.error(f"订阅主题 {topic} 失败: {e}")

    def _publish_system_status(self, status: str):
        message = {
            'status': status,
            'client_id': self.client_id,
            'timestamp': time.time(),
            'topics': list(self.topics.values())
        }
        self.publish(self.topics['system_status'], message, qos=1, retain=True)

    def publish(self, topic: str, payload: Any, qos: int = 0, retain: bool = False) -> bool:
        if not self.is_connected or not self.client:
            logger.warning(f"MQTT未连接，无法发布消息到: {topic}")
            return False

        try:
            if isinstance(payload, (dict, list)):
                payload = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            elif isinstance(payload, str):
                payload = payload.encode('utf-8')

            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                logger.error(f"发布消息失败 (错误代码: {result.rc})")
                return False

        except Exception as e:
            logger.error(f"发布消息错误: {e}")
            return False

    def publish_video_frame(self, frame: np.ndarray, frame_id: int = 0) -> bool:
        if not self.is_connected:
            return False

        try:
            height, width = frame.shape[:2]
            target_width = 320
            target_height = 240

            if width != target_width or height != target_height:
                frame_resized = cv2.resize(frame, (target_width, target_height),
                                         interpolation=cv2.INTER_LINEAR)
            else:
                frame_resized = frame

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.video_quality]
            success, buffer = cv2.imencode('.jpg', frame_resized, encode_param)

            if not success:
                logger.error("视频帧编码失败")
                return False

            frame_info = {
                'frame_id': frame_id,
                'timestamp': time.time(),
                'width': target_width,
                'height': target_height,
                'format': 'jpeg'
            }

            header = json.dumps(frame_info).encode('utf-8')
            separator = b'\x00\x00\x00\x00'
            message = header + separator + buffer.tobytes()

            return self.publish(self.topics['video_stream'], message, qos=0)

        except Exception as e:
            logger.error(f"发布视频帧错误: {e}")
            return False

    def publish_object_data(self, objects: list, frame_id: int = 0) -> bool:
        message = {
            'frame_id': frame_id,
            'timestamp': time.time(),
            'objects': objects,
            'object_count': len(objects)
        }
        return self.publish(self.topics['object_data'], message, qos=1)

    def publish_tracking_stats(self, stats: Dict) -> bool:
        message = {
            **stats,
            'timestamp': time.time(),
            'protocol': 'mqtt'
        }
        return self.publish(self.topics['tracking_stats'], message, qos=1)

    def publish_error_alert(self, error_type: str, message: str, severity: str = 'warning') -> bool:
        alert = {
            'type': error_type,
            'message': message,
            'severity': severity,
            'timestamp': time.time(),
            'client_id': self.client_id
        }
        return self.publish(self.topics['error_alerts'], alert, qos=2, retain=True)

    def subscribe(self, topic: str, callback: Callable) -> bool:
        if not self.is_connected or not self.client:
            return False

        try:
            if topic not in self.callbacks:
                self.callbacks[topic] = []
            self.callbacks[topic].append(callback)

            self.client.subscribe(topic, qos=1)
            logger.debug(f"已添加回调并订阅主题: {topic}")
            return True

        except Exception as e:
            logger.error(f"订阅主题错误: {e}")
            return False

    def _handle_port_exhaustion(self):
        logger.warning("检测到端口耗尽，执行特殊处理...")
        wait_time = 60
        logger.info(f"等待 {wait_time} 秒让系统回收端口...")
        time.sleep(wait_time)

        self.reconnect_attempts = 0
        self.last_reconnect_time = time.time()

    def unsubscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        try:
            if callback and topic in self.callbacks:
                if callback in self.callbacks[topic]:
                    self.callbacks[topic].remove(callback)

            if not callback or not self.callbacks[topic]:
                if self.client:
                    self.client.unsubscribe(topic)
                if topic in self.callbacks:
                    del self.callbacks[topic]
                logger.debug(f"已取消订阅主题: {topic}")

            return True

        except Exception as e:
            logger.error(f"取消订阅错误: {e}")
            return False

_mqtt_service = None

def get_mqtt_service(config: Optional[Dict] = None) -> MQTTService:
    global _mqtt_service
    if _mqtt_service is None:
        _mqtt_service = MQTTService(config)
    return _mqtt_service

def initialize_mqtt_service(config: Optional[Dict] = None) -> MQTTService:
    global _mqtt_service
    _mqtt_service = MQTTService(config)
    return _mqtt_service