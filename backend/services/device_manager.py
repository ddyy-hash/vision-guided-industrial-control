import threading
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from .device_scanner import DeviceInfo, DeviceStatus, DeviceType, get_device_scanner
from .device_storage import get_device_storage
from api.belt import BeltController
from api.robot_arm import RobotArm

logger = logging.getLogger(__name__)

class ConnectionEvent(Enum):
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    DEVICE_ERROR = "device_error"
    STATUS_UPDATED = "status_updated"

class DeviceConnection:
    def __init__(self, device_info: DeviceInfo):
        self.device_info = device_info
        self.controller = None
        self.connected = False
        self.last_activity = time.time()
        self.connection_time = None
        self.error_count = 0

    def connect(self) -> bool:
        try:
            if self.device_info.device_type == DeviceType.ROBOT_ARM:
                self.controller = RobotArm(serial_port=self.device_info.connection_info)
                self.connected = self.controller.connected
            elif self.device_info.device_type == DeviceType.CONVEYOR_BELT:
                port = self.device_info.connection_info
                if port == 'COM5':
                    logger.info(f"检测到COM5端口，使用优化的连接参数")
                    try:
                        self.controller = BeltController(
                            port=port,
                            hardware_enabled=True
                        )
                        self.connected = self.controller.hardware_enabled and self.controller.connected
                        if not self.connected:
                            logger.warning(f"COM5硬件连接失败，回退到软件模式")
                            self.controller = BeltController(hardware_enabled=False)
                            self.connected = True
                    except Exception as e:
                        logger.error(f"COM5连接异常: {e}，使用软件模式")
                        self.controller = BeltController(hardware_enabled=False)
                        self.connected = True
                else:
                    self.controller = BeltController(
                        port=self.device_info.connection_info,
                        hardware_enabled=True
                    )
                    self.connected = self.controller.hardware_enabled and self.controller.connected
            else:
                self.connected = True

            if self.connected:
                self.connection_time = time.time()
                self.device_info.status = DeviceStatus.CONNECTED
                logger.info(f"设备连接成功: {self.device_info.name}")
                return True
            else:
                self.device_info.status = DeviceStatus.ERROR
                logger.error(f"设备连接失败: {self.device_info.name}")
                return False

        except Exception as e:
            self.device_info.status = DeviceStatus.ERROR
            self.error_count += 1
            logger.error(f"设备连接异常: {self.device_info.name} - {e}")
            return False

    def disconnect(self):
        try:
            if self.controller and hasattr(self.controller, 'close'):
                self.controller.close()
            self.connected = False
            self.device_info.status = DeviceStatus.DISCONNECTED
            self.connection_time = None
            logger.info(f"设备已断开: {self.device_info.name}")
        except Exception as e:
            logger.error(f"设备断开异常: {self.device_info.name} - {e}")

    def get_status(self) -> Dict[str, Any]:
        status = {
            "device_id": self.device_info.device_id,
            "name": self.device_info.name,
            "device_type": self.device_info.device_type.value,
            "connected": self.connected,
            "status": self.device_info.status.value,
            "connection_time": self.connection_time,
            "last_activity": self.last_activity,
            "error_count": self.error_count
        }

        if self.controller:
            if hasattr(self.controller, 'get_status'):
                status.update(self.controller.get_status())
            elif hasattr(self.controller, 'hardware_enabled'):
                status["hardware_enabled"] = self.controller.hardware_enabled
                status["simulation_mode"] = not self.controller.hardware_enabled

        return status

class DeviceConnectionManager:
    def __init__(self):
        self.connections: Dict[str, DeviceConnection] = {}
        self.event_handlers: Dict[ConnectionEvent, List[Callable]] = {
            event: [] for event in ConnectionEvent
        }
        self.lock = threading.RLock()
        self.auto_reconnect = True
        self.max_reconnect_attempts = 3
        self.reconnect_delay = 5

        self.scanner = get_device_scanner()
        self.storage = get_device_storage()

        self.scanner.add_device_handler(self._on_device_discovered)

    def add_event_handler(self, event: ConnectionEvent, handler: Callable):
        with self.lock:
            if event not in self.event_handlers:
                self.event_handlers[event] = []
            self.event_handlers[event].append(handler)

    def _notify_event_handlers(self, event: ConnectionEvent, data: Any):
        handlers = self.event_handlers.get(event, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"事件处理函数错误: {e}")

    def _on_device_discovered(self, device_info: DeviceInfo):
        with self.lock:
            self.storage.save_device(device_info)

            if (self.auto_reconnect and
                device_info.device_id in self.connections and
                not self.connections[device_info.device_id].connected):

                logger.info(f"尝试自动重连设备: {device_info.name}")
                self.connect_device(device_info.device_id)

    def connect_device(self, device_id: str) -> bool:
        with self.lock:
            if device_id in self.connections and self.connections[device_id].connected:
                logger.info(f"设备已连接: {device_id}")
                return True

            device_info = self.scanner.get_device(device_id)
            if not device_info:
                device_info = self.storage.get_device(device_id)
                if not device_info:
                    logger.error(f"设备不存在: {device_id}")
                    return False

            connection = DeviceConnection(device_info)

            device_info.status = DeviceStatus.CONNECTING
            self.scanner.update_device_status(device_id, DeviceStatus.CONNECTING)
            self.storage.save_device(device_info)

            success = connection.connect()

            if success:
                self.connections[device_id] = connection
                self.scanner.update_device_status(device_id, DeviceStatus.CONNECTED)
                self.storage.record_connection(device_id, DeviceStatus.CONNECTED)

                self._notify_event_handlers(
                    ConnectionEvent.DEVICE_CONNECTED,
                    connection.get_status()
                )
                logger.info(f"设备连接成功: {device_info.name}")
            else:
                self.scanner.update_device_status(device_id, DeviceStatus.ERROR)
                self.storage.record_connection(device_id, DeviceStatus.ERROR, "连接失败")

                self._notify_event_handlers(
                    ConnectionEvent.DEVICE_ERROR,
                    {"device_id": device_id, "error": "连接失败"}
                )
                logger.error(f"设备连接失败: {device_info.name}")

            return success

    def disconnect_device(self, device_id: str):
        with self.lock:
            if device_id in self.connections:
                connection = self.connections[device_id]
                connection.disconnect()

                self.scanner.update_device_status(device_id, DeviceStatus.DISCONNECTED)
                self.storage.record_connection(device_id, DeviceStatus.DISCONNECTED)

                self._notify_event_handlers(
                    ConnectionEvent.DEVICE_DISCONNECTED,
                    connection.get_status()
                )

                del self.connections[device_id]
                logger.info(f"设备已断开: {device_id}")

    def get_connected_devices(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [conn.get_status() for conn in self.connections.values()]

    def get_device_connection(self, device_id: str) -> Optional[DeviceConnection]:
        with self.lock:
            return self.connections.get(device_id)

    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            if device_id in self.connections:
                return self.connections[device_id].get_status()
            return None

    def update_device_status(self, device_id: str, status_data: Dict[str, Any]):
        with self.lock:
            if device_id in self.connections:
                connection = self.connections[device_id]
                connection.last_activity = time.time()

                self._notify_event_handlers(
                    ConnectionEvent.STATUS_UPDATED,
                    connection.get_status()
                )

    def get_available_devices(self) -> List[Dict[str, Any]]:
        available_devices = self.scanner.get_available_devices()

        historical_devices = self.storage.get_all_devices()
        historical_device_ids = {device.device_id for device in historical_devices}

        device_map = {}

        for device_dict in available_devices:
            device_map[device_dict["device_id"]] = device_dict

        for device in historical_devices:
            if device.device_id not in device_map:
                device_map[device.device_id] = device.to_dict()

        return list(device_map.values())

    def start_auto_scan(self):
        self.scanner.start_scanning()
        logger.info("设备自动扫描已启动")

    def stop_auto_scan(self):
        self.scanner.stop_scanning()
        logger.info("设备自动扫描已停止")

    def manual_scan(self):
        self.scanner.manual_scan()
        logger.info("手动设备扫描已完成")

    def cleanup_old_devices(self, days: int = 30):
        try:
            all_devices = self.storage.get_all_devices()
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)

            cleaned_count = 0
            for device in all_devices:
                if (device.last_seen < cutoff_time and
                    device.device_id not in self.connections):

                    self.storage.delete_device(device.device_id)
                    cleaned_count += 1

            logger.info(f"清理了 {cleaned_count} 个长时间未连接的设备")
            return cleaned_count

        except Exception as e:
            logger.error(f"清理旧设备失败: {e}")
            return 0

    def get_device_statistics(self) -> Dict[str, Any]:
        with self.lock:
            connected_count = len(self.connections)
            available_devices = self.scanner.get_available_devices()
            available_count = len(available_devices)
            historical_devices = self.storage.get_all_devices()
            historical_count = len(historical_devices)

            type_stats = {}
            for device in historical_devices:
                device_type = device.device_type.value
                type_stats[device_type] = type_stats.get(device_type, 0) + 1

            return {
                "connected_devices": connected_count,
                "available_devices": available_count,
                "historical_devices": historical_count,
                "device_types": type_stats,
                "auto_reconnect_enabled": self.auto_reconnect,
                "scan_interval": self.scanner.scan_interval
            }

_device_manager = None

def get_device_manager() -> DeviceConnectionManager:
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceConnectionManager()
    return _device_manager