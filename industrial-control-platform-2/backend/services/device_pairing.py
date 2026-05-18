import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional
from enum import Enum
from .device_scanner import DeviceType, DeviceStatus, DeviceInfo, get_device_scanner
from .device_connection_manager import get_device_connection_manager

logger = logging.getLogger(__name__)

class PairingStatus(Enum):
    UNPAIRED = "unpaired"
    PENDING = "pending"
    PAIRED = "paired"
    FAILED = "failed"

class PairingMode(Enum):
    DISCOVERY = "discovery"
    PAIRING = "pairing"
    CONNECTING = "connecting"

class PairingRecord:
    def __init__(self, device_id: str, device_type: DeviceType, custom_name: str = None,
                 auto_connect: bool = True, connection_info: str = ""):
        self.device_id = device_id
        self.device_type = device_type
        self.custom_name = custom_name
        self.auto_connect = auto_connect
        self.connection_info = connection_info
        self.paired_at = time.time()
        self.last_connected = None
        self.connection_count = 0
        self.success_rate = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "custom_name": self.custom_name,
            "auto_connect": self.auto_connect,
            "connection_info": self.connection_info,
            "paired_at": self.paired_at,
            "last_connected": self.last_connected,
            "connection_count": self.connection_count,
            "success_rate": self.success_rate
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PairingRecord':
        record = cls(
            device_id=data["device_id"],
            device_type=DeviceType(data["device_type"]),
            custom_name=data.get("custom_name"),
            auto_connect=data.get("auto_connect", True),
            connection_info=data.get("connection_info", "")
        )
        record.paired_at = data.get("paired_at", time.time())
        record.last_connected = data.get("last_connected")
        record.connection_count = data.get("connection_count", 0)
        record.success_rate = data.get("success_rate", 1.0)
        return record

class DevicePairingManager:
    def __init__(self):
        self.pairing_records: Dict[str, PairingRecord] = {}
        self.pending_pairings: Dict[str, Dict[str, Any]] = {}
        self.scanner = get_device_scanner()
        self.connection_manager = get_device_connection_manager()
        self.lock = threading.RLock()

        self._load_pairing_records()

        self.scanner.add_device_handler(self._on_device_discovered)

        self.auto_connect_enabled = True
        self.auto_connect_thread = None
        self.running = False

    def _load_pairing_records(self):
        try:
            import os
            pairing_file = "pairing_records.json"
            if os.path.exists(pairing_file):
                with open(pairing_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for device_id, record_data in data.items():
                        self.pairing_records[device_id] = PairingRecord.from_dict(record_data)
                logger.info(f"已加载 {len(self.pairing_records)} 条设备配对记录")
            else:
                logger.info("配对记录文件不存在，将创建新的配对记录文件")
        except Exception as e:
            logger.error(f"加载配对记录失败: {e}")
            self.pairing_records = {}

    def _save_pairing_records(self):
        try:
            pairing_file = "pairing_records.json"
            data = {device_id: record.to_dict() for device_id, record in self.pairing_records.items()}
            with open(pairing_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(self.pairing_records)} 条设备配对记录")
        except Exception as e:
            logger.error(f"保存配对记录失败: {e}")

    def _on_device_discovered(self, device_info: DeviceInfo):
        with self.lock:
            device_id = device_info.device_id

            if device_id in self.pairing_records:
                pairing_record = self.pairing_records[device_id]

                device_info.device_type = pairing_record.device_type
                device_info.pairing_status = "paired"
                device_info.auto_connect = pairing_record.auto_connect

                if pairing_record.custom_name:
                    device_info.name = pairing_record.custom_name

                if (self.auto_connect_enabled and
                    pairing_record.auto_connect and
                    device_info.status == DeviceStatus.DISCONNECTED):

                    connection_failures = self.connection_manager.get_connection_failure_count(device_id)
                    if connection_failures >= 3:
                        logger.warning(f"设备连接失败次数过多，跳过自动连接: {device_info.name} (失败次数: {connection_failures})")
                        return

                    logger.info(f"尝试自动连接设备: {device_info.name}")
                    self._auto_connect_device(device_info, pairing_record)

    def create_pairing_request(self, device_id: str) -> Optional[str]:
        with self.lock:
            if device_id not in self.scanner.devices:
                logger.error(f"设备不存在: {device_id}")
                return None

            device = self.scanner.devices[device_id]

            pairing_id = f"pairing_{int(time.time())}_{device_id}"

            self.pending_pairings[pairing_id] = {
                "device_id": device_id,
                "device_info": device.to_dict(),
                "status": PairingStatus.PENDING,
                "created_at": time.time(),
                "expires_at": time.time() + 300
            }

            logger.info(f"创建设备配对请求: {pairing_id} for {device_id}")
            return pairing_id

    def confirm_pairing(self, pairing_id: str, device_type: DeviceType,
                       custom_name: str = None, auto_connect: bool = True) -> bool:
        with self.lock:
            if pairing_id not in self.pending_pairings:
                logger.error(f"配对请求不存在或已过期: {pairing_id}")
                return False

            pairing_request = self.pending_pairings[pairing_id]

            current_time = time.time()
            if current_time > pairing_request["expires_at"]:
                del self.pending_pairings[pairing_id]
                logger.error(f"配对请求已过期: {pairing_id}, 创建时间: {pairing_request['created_at']}, 过期时间: {pairing_request['expires_at']}, 当前时间: {current_time}")
                return False

            device_id = pairing_request["device_id"]

            if device_id not in self.scanner.devices:
                logger.error(f"设备已不存在: {device_id}")
                pairing_request["status"] = PairingStatus.FAILED
                return False

            success = self.scanner.pair_device(device_id, device_type, custom_name, auto_connect)

            if success:
                device = self.scanner.devices[device_id]
                self.pairing_records[device_id] = PairingRecord(
                    device_id=device_id,
                    device_type=device_type,
                    custom_name=custom_name,
                    auto_connect=auto_connect,
                    connection_info=device.connection_info
                )

                self._save_pairing_records()

                pairing_request["status"] = PairingStatus.PAIRED
                pairing_request["confirmed_at"] = time.time()

                if auto_connect:
                    logger.info(f"配对成功后延迟尝试连接设备: {device_id}")
                    threading.Timer(2.0, lambda: self._auto_connect_device(device, self.pairing_records[device_id])).start()

                logger.info(f"设备配对成功: {device_id} -> {device_type.value}")
            else:
                pairing_request["status"] = PairingStatus.FAILED
                logger.error(f"设备配对失败: {device_id}, 设备类型: {device_type.value}")

            return success

    def cancel_pairing(self, pairing_id: str) -> bool:
        with self.lock:
            if pairing_id in self.pending_pairings:
                del self.pending_pairings[pairing_id]
                logger.info(f"取消设备配对: {pairing_id}")
                return True
            return False

    def unpair_device(self, device_id: str) -> bool:
        with self.lock:
            if device_id in self.pairing_records:
                del self.pairing_records[device_id]
                self._save_pairing_records()

            success = self.scanner.unpair_device(device_id)

            if success:
                logger.info(f"设备取消配对: {device_id}")
            else:
                logger.error(f"取消设备配对失败: {device_id}")

            return success

    def get_pairing_status(self, pairing_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            if pairing_id in self.pending_pairings:
                return self.pending_pairings[pairing_id]
            return None

    def get_pairing_history(self) -> List[Dict[str, Any]]:
        with self.lock:
            history = []
            for record in self.pairing_records.values():
                history.append(record.to_dict())
            return sorted(history, key=lambda x: x["paired_at"], reverse=True)

    def get_paired_devices(self) -> List[Dict[str, Any]]:
        with self.lock:
            paired_devices = []
            for device_id, record in self.pairing_records.items():
                device = self.scanner.get_device(device_id)
                if device:
                    device_dict = device.to_dict()
                    device_dict.update({
                        "pairing_record": record.to_dict(),
                        "auto_connect": record.auto_connect
                    })
                    paired_devices.append(device_dict)
            return paired_devices

    def update_pairing_record(self, device_id: str, **kwargs) -> bool:
        with self.lock:
            if device_id not in self.pairing_records:
                logger.error(f"配对记录不存在: {device_id}")
                return False

            record = self.pairing_records[device_id]

            old_auto_connect = record.auto_connect

            if "custom_name" in kwargs:
                record.custom_name = kwargs["custom_name"]
            if "auto_connect" in kwargs:
                record.auto_connect = kwargs["auto_connect"]

            device = self.scanner.get_device(device_id)
            if device:
                if "custom_name" in kwargs:
                    device.name = kwargs["custom_name"]
                if "auto_connect" in kwargs:
                    device.auto_connect = kwargs["auto_connect"]

            self._save_pairing_records()

            if "auto_connect" in kwargs and kwargs["auto_connect"] != old_auto_connect:
                if kwargs["auto_connect"]:
                    logger.info(f"启用自动连接，尝试连接设备: {device_id}")
                    self._auto_connect_device(device, record)
                else:
                    logger.info(f"禁用自动连接，断开设备: {device_id}")

            logger.info(f"更新配对记录: {device_id}")
            return True

    def record_connection_attempt(self, device_id: str, success: bool):
        with self.lock:
            if device_id in self.pairing_records:
                record = self.pairing_records[device_id]
                record.connection_count += 1

                if success:
                    record.last_connected = time.time()
                    if record.connection_count > 0:
                        record.success_rate = (
                            (record.success_rate * (record.connection_count - 1) + 1)
                            / record.connection_count
                        )
                else:
                    if record.connection_count > 0:
                        record.success_rate = (
                            (record.success_rate * (record.connection_count - 1))
                            / record.connection_count
                        )

                self._save_pairing_records()

    def start_auto_connect(self):
        with self.lock:
            if self.running:
                return

            self.auto_connect_enabled = True
            self.running = True
            self.auto_connect_thread = threading.Thread(target=self._auto_connect_loop, daemon=True)
            self.auto_connect_thread.start()
            logger.info("自动连接服务已启动")

    def stop_auto_connect(self):
        with self.lock:
            self.auto_connect_enabled = False
            self.running = False
            if self.auto_connect_thread:
                self.auto_connect_thread.join(timeout=5)
            logger.info("自动连接服务已停止")

    def _auto_connect_loop(self):
        while self.running:
            try:
                with self.lock:
                    if not self.auto_connect_enabled:
                        break

                    auto_connect_devices = [
                        record for record in self.pairing_records.values()
                        if record.auto_connect
                    ]

                    for record in auto_connect_devices:
                        device = self.scanner.get_device(record.device_id)
                        if (device and
                            device.status == DeviceStatus.DISCONNECTED and
                            device.pairing_status == "paired"):

                            connection_failures = self.connection_manager.get_connection_failure_count(record.device_id)
                            if connection_failures >= 3:
                                logger.debug(f"设备连接失败次数过多，跳过自动连接: {device.name} (失败次数: {connection_failures})")
                                continue

                            logger.info(f"自动连接循环: 尝试连接设备: {device.name}")
                            self._auto_connect_device(device, record)

                time.sleep(60)

            except Exception as e:
                logger.error(f"自动连接循环错误: {e}")
                time.sleep(60)

    def _auto_connect_device(self, device_info: DeviceInfo, pairing_record: PairingRecord):
        try:
            if device_info.status == DeviceStatus.CONNECTED:
                logger.debug(f"设备已连接，跳过自动连接: {device_info.name}")
                return

            if device_info.device_type == DeviceType.ROBOT_ARM:
                success = self.connection_manager.reconnect_device(
                    device_info.device_type,
                    device_info.connection_info
                )
                if success:
                    logger.info(f"自动连接成功: {device_info.name}")
                    self.record_connection_attempt(device_info.device_id, True)
                    self.connection_manager._clear_connection_failure(device_info.device_id)
                else:
                    logger.warning(f"自动连接失败: {device_info.name}")
                    self.record_connection_attempt(device_info.device_id, False)

            elif device_info.device_type == DeviceType.CONVEYOR_BELT:
                belt_controller = self.connection_manager.get_belt_controller()
                if belt_controller and belt_controller.connected:
                    logger.info(f"传送带已连接（软件模式）: {device_info.name}")
                    self.record_connection_attempt(device_info.device_id, True)
                    self.connection_manager._clear_connection_failure(device_info.device_id)
                else:
                    try:
                        from api.belt import BeltController
                        new_belt_controller = BeltController(hardware_enabled=False)
                        self.connection_manager.connected_devices[DeviceType.CONVEYOR_BELT] = new_belt_controller
                        logger.info(f"传送带重新连接（软件模式）: {device_info.name}")
                        self.record_connection_attempt(device_info.device_id, True)
                        self.connection_manager._clear_connection_failure(device_info.device_id)
                    except Exception as e:
                        logger.warning(f"传送带重新连接失败: {device_info.name}, 错误: {e}")
                        self.record_connection_attempt(device_info.device_id, False)

        except Exception as e:
            logger.error(f"自动连接设备异常 {device_info.name}: {e}")
            self.record_connection_attempt(device_info.device_id, False)

    def get_statistics(self) -> Dict[str, Any]:
        with self.lock:
            total_paired = len(self.pairing_records)
            auto_connect_count = sum(1 for r in self.pairing_records.values() if r.auto_connect)

            if total_paired > 0:
                avg_success_rate = sum(r.success_rate for r in self.pairing_records.values()) / total_paired
            else:
                avg_success_rate = 0

            type_stats = {}
            for record in self.pairing_records.values():
                device_type = record.device_type.value
                type_stats[device_type] = type_stats.get(device_type, 0) + 1

            return {
                "total_paired_devices": total_paired,
                "auto_connect_devices": auto_connect_count,
                "average_success_rate": round(avg_success_rate, 2),
                "device_type_stats": type_stats,
                "auto_connect_enabled": self.auto_connect_enabled
            }

_device_pairing_manager = None

def get_device_pairing_manager() -> DevicePairingManager:
    global _device_pairing_manager
    if _device_pairing_manager is None:
        _device_pairing_manager = DevicePairingManager()
    return _device_pairing_manager