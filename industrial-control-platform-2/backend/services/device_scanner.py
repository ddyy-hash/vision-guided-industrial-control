import serial.tools.list_ports
import threading
import time
import logging
import serial
import json
from typing import List, Dict, Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    ROBOT_ARM = "robot_arm"
    CONVEYOR_BELT = "conveyor_belt"
    VISION_SYSTEM = "vision_system"
    TEMPERATURE_SENSOR = "temperature_sensor"
    PLC = "plc"
    UNKNOWN = "unknown"

class DeviceStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class DeviceInfo:
    def __init__(self, device_id: str, name: str, device_type: DeviceType,
                 connection_info: str, status: DeviceStatus = DeviceStatus.DISCONNECTED, **kwargs):
        self.device_id = device_id
        self.name = name
        self.device_type = device_type
        self.connection_info = connection_info
        self.status = status
        self.last_seen = time.time()
        self.discovered_time = time.time()
        self.metadata = {}
        self.pairing_status = "unpaired"  # unpaired, pairing, paired
        self.auto_connect = False

    def to_dict(self) -> Dict[str, Any]:
        import time
        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type.value,
            "model": "未知型号",
            "manufacturer": "未知厂商",
            "serial_number": f"SN_{self.device_id}",
            "firmware_version": "1.0.0",
            "connection_type": "serial",
            "connection_info": self.connection_info,
            "connection_params": {
                "port": self.connection_info,
                "baud_rate": 9600,
                "data_bits": 8,
                "stop_bits": 1,
                "parity": "none"
            },
            "last_seen": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_seen)),
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.discovered_time)),
            "updated_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_seen)),
            "is_online": self.status == DeviceStatus.CONNECTED,
            "status": self.status.value,
            "pairing_status": self.pairing_status,
            "description": f"{self.device_type.value}设备",
            "tags": [self.device_type.value, "serial"],
            "capabilities": ["connect", "disconnect", "reset"],
            "health_score": 85,
            "port": self.connection_info,
            "auto_connect": self.auto_connect,
            "last_connection_time": None,
            "connection_count": 0
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        device = cls(
            device_id=data["device_id"],
            name=data["name"],
            device_type=DeviceType(data["device_type"]),
            connection_info=data["connection_info"],
            status=DeviceStatus(data["status"])
        )
        device.last_seen = data["last_seen"]
        device.discovered_time = data["discovered_time"]
        device.metadata = data.get("metadata", {})
        device.pairing_status = data.get("pairing_status", "unpaired")
        device.auto_connect = data.get("auto_connect", False)
        return device

class EnhancedDeviceScanner:
    def __init__(self, scan_interval: int = 5):
        self.scan_interval = scan_interval
        self.devices: Dict[str, DeviceInfo] = {}
        self.scanning = False
        self.scan_thread = None
        self.device_handlers: List[Callable[[DeviceInfo], None]] = []

        self.device_signatures = {
            DeviceType.ROBOT_ARM: [
                {"vid": "0x2341", "pid": "0x0042"},  # Arduino Uno
                {"vid": "0x2a03", "pid": "0x0042"},  # Arduino Uno Clone
                {"baud_rate": 115200, "data_bits": 8, "stop_bits": 1},
                {"description_contains": "robot", "confidence": 0.8},
                {"description_contains": "arm", "confidence": 0.7}
            ],
            DeviceType.CONVEYOR_BELT: [
                {"vid": "0x1a86", "pid": "0x7523"},  # CH340
                {"baud_rate": 9600, "data_bits": 8, "stop_bits": 1},
                {"description_contains": "conveyor", "confidence": 0.9},
                {"description_contains": "belt", "confidence": 0.7}
            ],
            DeviceType.TEMPERATURE_SENSOR: [
                {"vid": "0x0403", "pid": "0x6001"},  # FT232R
                {"baud_rate": 9600, "data_bits": 8, "stop_bits": 1},
                {"description_contains": "temp", "confidence": 0.8},
                {"description_contains": "sensor", "confidence": 0.6}
            ]
        }

        self.legacy_device_rules = {}

        self.network_devices = []

        self.pairing_records: Dict[str, Dict[str, Any]] = {}
        self._load_pairing_records()

    def add_device_handler(self, handler: Callable[[DeviceInfo], None]):
        self.device_handlers.append(handler)

    def start_scanning(self):
        if self.scanning:
            return

        self.scanning = True
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        logger.info("设备扫描服务已启动")

    def stop_scanning(self):
        self.scanning = False
        if self.scan_thread:
            self.scan_thread.join()
        logger.info("设备扫描服务已停止")

    def _scan_loop(self):
        while self.scanning:
            try:
                self._scan_serial_ports()
                self._scan_network_devices()
                time.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"设备扫描错误: {e}")
                time.sleep(self.scan_interval)

    def _scan_serial_ports(self):
        try:
            ports = serial.tools.list_ports.comports()
            current_devices = {}

            for port in ports:
                device_info = self._identify_serial_device(port)
                if device_info:
                    device_id = f"serial_{port.device}"

                    if device_id in self.pairing_records:
                        pairing_record = self.pairing_records[device_id]
                        device_info.device_type = DeviceType(pairing_record["device_type"])
                        device_info.pairing_status = "paired"
                        device_info.auto_connect = pairing_record.get("auto_connect", False)
                        device_info.name = pairing_record.get("custom_name", device_info.name)

                    if device_id in self.devices:
                        existing_device = self.devices[device_id]
                        existing_device.last_seen = time.time()
                        existing_device.device_type = device_info.device_type
                        existing_device.pairing_status = device_info.pairing_status
                        existing_device.auto_connect = device_info.auto_connect
                        current_devices[device_id] = existing_device
                    else:
                        device_info.device_id = device_id
                        self.devices[device_id] = device_info
                        current_devices[device_id] = device_info
                        self._notify_device_handlers(device_info)
                        logger.info(f"发现新设备: {device_info.name} ({port.device}) - 类型: {device_info.device_type.value}")

            disappeared_devices = set(self.devices.keys()) - set(current_devices.keys())
            for device_id in disappeared_devices:
                device = self.devices[device_id]
                logger.info(f"设备消失: {device.name} ({device.connection_info})")
                del self.devices[device_id]

            self.devices = current_devices

        except Exception as e:
            logger.error(f"串口扫描错误: {e}")

    def _identify_serial_device(self, port) -> Optional[DeviceInfo]:
        port_name = port.device

        device_id = f"serial_{port_name}"
        if device_id in self.pairing_records:
            pairing_record = self.pairing_records[device_id]
            device = DeviceInfo(
                device_id=device_id,
                name=pairing_record.get("custom_name", f"{pairing_record['device_type']}#{port_name}"),
                device_type=DeviceType(pairing_record["device_type"]),
                connection_info=port_name,
                status=DeviceStatus.DISCONNECTED
            )
            device.pairing_status = "paired"
            device.auto_connect = pairing_record.get("auto_connect", False)
            return device

        device_type = self._identify_by_device_signatures(port)

        if device_type == DeviceType.UNKNOWN:
            device_type = self._probe_device_communication(port)

        if device_type != DeviceType.UNKNOWN:
            device_name = f"{device_type.value}#{port_name}"
        else:
            device_name = f"端口_{port_name}"

        return DeviceInfo(
            device_id=device_id,
            name=device_name,
            device_type=device_type,
            connection_info=port_name,
            status=DeviceStatus.DISCONNECTED
        )

    def _identify_by_device_signatures(self, port) -> DeviceType:
        best_match = DeviceType.UNKNOWN
        highest_confidence = 0.0

        for device_type, signatures in self.device_signatures.items():
            for signature in signatures:
                confidence = self._calculate_signature_match_confidence(port, signature)
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_match = device_type

        return best_match if highest_confidence > 0.6 else DeviceType.UNKNOWN

    def _calculate_signature_match_confidence(self, port, signature) -> float:
        confidence = 0.0

        if hasattr(port, 'vid') and hasattr(port, 'pid'):
            if 'vid' in signature and 'pid' in signature:
                if (signature['vid'] == f"0x{port.vid:04x}" and
                    signature['pid'] == f"0x{port.pid:04x}"):
                    confidence += 0.8

        if 'baud_rate' in signature:
            confidence += 0.3

        if 'description_contains' in signature:
            desc_confidence = signature.get('confidence', 0.5)
            if hasattr(port, 'description') and port.description:
                if signature['description_contains'].lower() in port.description.lower():
                    confidence += desc_confidence

        return min(confidence, 1.0)

    def _probe_device_communication(self, port) -> DeviceType:
        port_name = port.device

        probe_configs = [
            {"baud_rate": 115200, "timeout": 1.0, "device_type": DeviceType.ROBOT_ARM},
            {"baud_rate": 9600, "timeout": 1.0, "device_type": DeviceType.CONVEYOR_BELT},
            {"baud_rate": 9600, "timeout": 1.0, "device_type": DeviceType.TEMPERATURE_SENSOR},
        ]

        for config in probe_configs:
            try:
                with serial.Serial(
                    port=port_name,
                    baudrate=config["baud_rate"],
                    timeout=config["timeout"]
                ) as ser:
                    probe_commands = {
                        DeviceType.ROBOT_ARM: b"STATUS\n",
                        DeviceType.CONVEYOR_BELT: b"GET_STATUS\n",
                        DeviceType.TEMPERATURE_SENSOR: b"READ_TEMP\n"
                    }

                    command = probe_commands.get(config["device_type"], b"PING\n")
                    ser.write(command)
                    response = ser.read(100)

                    if len(response) > 0:
                        logger.info(f"设备通信探测成功: {port_name} -> {config['device_type'].value}")
                        return config["device_type"]

            except (serial.SerialException, OSError) as e:
                continue
            except Exception as e:
                logger.debug(f"设备通信探测异常: {port_name} - {e}")
                continue

        return DeviceType.UNKNOWN

    def _load_pairing_records(self):
        try:
            import os
            pairing_file = "pairing_records.json"
            if os.path.exists(pairing_file):
                with open(pairing_file, 'r', encoding='utf-8') as f:
                    self.pairing_records = json.load(f)
                logger.info(f"已加载 {len(self.pairing_records)} 条配对记录")
            else:
                logger.info("配对记录文件不存在，将创建新的配对记录文件")
        except Exception as e:
            logger.error(f"加载配对记录失败: {e}")
            self.pairing_records = {}

    def _save_pairing_records(self):
        try:
            pairing_file = "pairing_records.json"
            with open(pairing_file, 'w', encoding='utf-8') as f:
                json.dump(self.pairing_records, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(self.pairing_records)} 条配对记录")
        except Exception as e:
            logger.error(f"保存配对记录失败: {e}")

    def pair_device(self, device_id: str, device_type: DeviceType, custom_name: str = None, auto_connect: bool = True) -> bool:
        try:
            if device_id not in self.devices:
                logger.error(f"设备不存在: {device_id}")
                return False

            device = self.devices[device_id]
            device.device_type = device_type
            device.pairing_status = "paired"
            device.auto_connect = auto_connect

            if custom_name:
                device.name = custom_name

            self.pairing_records[device_id] = {
                "device_type": device_type.value,
                "custom_name": custom_name or device.name,
                "auto_connect": auto_connect,
                "paired_at": time.time(),
                "connection_info": device.connection_info
            }

            self._save_pairing_records()
            logger.info(f"设备配对成功: {device_id} -> {device_type.value}")
            return True

        except Exception as e:
            logger.error(f"设备配对失败: {e}")
            return False

    def unpair_device(self, device_id: str) -> bool:
        try:
            if device_id in self.pairing_records:
                del self.pairing_records[device_id]
                self._save_pairing_records()

            if device_id in self.devices:
                device = self.devices[device_id]
                device.pairing_status = "unpaired"
                device.auto_connect = False
                device.device_type = DeviceType.UNKNOWN
                device.name = f"未知设备_{device.connection_info}"

            logger.info(f"设备取消配对: {device_id}")
            return True

        except Exception as e:
            logger.error(f"取消设备配对失败: {e}")
            return False

    def get_pairing_history(self) -> List[Dict[str, Any]]:
        history = []
        for device_id, record in self.pairing_records.items():
            history.append({
                "device_id": device_id,
                "device_type": record["device_type"],
                "custom_name": record.get("custom_name", ""),
                "auto_connect": record.get("auto_connect", False),
                "paired_at": record.get("paired_at", 0),
                "connection_info": record.get("connection_info", "")
            })
        return sorted(history, key=lambda x: x["paired_at"], reverse=True)

    def get_paired_devices(self) -> List[DeviceInfo]:
        paired_devices = []
        for device_id, device in self.devices.items():
            if device.pairing_status == "paired":
                paired_devices.append(device)
        return paired_devices

    def get_auto_connect_devices(self) -> List[DeviceInfo]:
        auto_connect_devices = []
        for device_id, device in self.devices.items():
            if device.auto_connect and device.pairing_status == "paired":
                auto_connect_devices.append(device)
        return auto_connect_devices

    def _scan_network_devices(self):
        pass

    def _notify_device_handlers(self, device_info: DeviceInfo):
        for handler in self.device_handlers:
            try:
                handler(device_info)
            except Exception as e:
                logger.error(f"设备处理函数错误: {e}")

    def get_available_devices(self) -> List[Dict[str, Any]]:
        return [device.to_dict() for device in self.devices.values()]

    def get_device(self, device_id: str) -> DeviceInfo:
        return self.devices.get(device_id)

    def update_device_status(self, device_id: str, status: DeviceStatus):
        if device_id in self.devices:
            self.devices[device_id].status = status
            self.devices[device_id].last_seen = time.time()

    def manual_scan(self):
        self._scan_serial_ports()
        self._scan_network_devices()

_enhanced_device_scanner = None

def get_device_scanner() -> EnhancedDeviceScanner:
    global _enhanced_device_scanner
    if _enhanced_device_scanner is None:
        _enhanced_device_scanner = EnhancedDeviceScanner()
    return _enhanced_device_scanner