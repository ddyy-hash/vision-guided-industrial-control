import logging
import threading
import time
from typing import Dict, Optional, Any
from .device_scanner import DeviceType, get_device_scanner
from api.robot_arm import RobotArm
from api.belt import BeltController

logger = logging.getLogger(__name__)

class DeviceConnectionManager:

    def __init__(self):
        self.scanner = get_device_scanner()
        self.connected_devices: Dict[str, Any] = {}
        self.lock = threading.RLock()
        self.initialized = False

        self.device_controllers = {
            DeviceType.ROBOT_ARM: RobotArm,
            DeviceType.CONVEYOR_BELT: BeltController
        }

        self.default_ports = {
            DeviceType.ROBOT_ARM: "COM4",
            DeviceType.CONVEYOR_BELT: "COM5"
        }

        logger.info("设备连接管理器初始化完成")

    def initialize_connections(self):
        with self.lock:
            if self.initialized:
                return

            logger.info("开始初始化设备连接...")

            paired_devices = self.scanner.get_paired_devices()
            auto_connect_devices = [d for d in paired_devices if d.auto_connect]

            if auto_connect_devices:
                logger.info(f"找到 {len(auto_connect_devices)} 个启用自动连接的配对设备")
                for device_info in auto_connect_devices:
                    self._connect_device(device_info)
            else:
                logger.info("没有找到启用自动连接的配对设备，尝试连接默认设备")
                self._connect_default_devices()

            self.initialized = True
            logger.info(f"设备连接初始化完成，已连接 {len(self.connected_devices)} 个设备")

    def _connect_default_devices(self):
        logger.info("尝试连接默认设备...")

        try:
            arm_port = self.default_ports[DeviceType.ROBOT_ARM]
            arm_controller = RobotArm(serial_port=arm_port)
            if arm_controller.connected:
                self.connected_devices[DeviceType.ROBOT_ARM] = arm_controller
                logger.info(f"机械臂默认连接成功: {arm_port}")
            else:
                logger.warning(f"机械臂默认连接失败: {arm_port}")
        except Exception as e:
            logger.error(f"机械臂默认连接异常: {e}")

        try:
            belt_port = self.default_ports[DeviceType.CONVEYOR_BELT]
            belt_controller = BeltController(port=belt_port, hardware_enabled=True)
            if belt_controller.connected:
                self.connected_devices[DeviceType.CONVEYOR_BELT] = belt_controller
                logger.info(f"传送带硬件连接成功: {belt_port}")
            else:
                belt_controller = BeltController(hardware_enabled=False)
                self.connected_devices[DeviceType.CONVEYOR_BELT] = belt_controller
                logger.info("传送带使用软件模式")
        except Exception as e:
            logger.error(f"传送带硬件连接异常: {e}")
            belt_controller = BeltController(hardware_enabled=False)
            self.connected_devices[DeviceType.CONVEYOR_BELT] = belt_controller
            logger.info("传送带使用软件模式（异常回退）")

    def _connect_device(self, device_info):
        try:
            device_type = device_info.device_type
            port = device_info.connection_info

            if device_type not in self.device_controllers:
                logger.warning(f"不支持的设备类型: {device_type}")
                return

            controller_class = self.device_controllers[device_type]

            if device_type in self.connected_devices:
                existing_controller = self.connected_devices[device_type]
                if hasattr(existing_controller, 'connected') and existing_controller.connected:
                    logger.info(f"设备已连接，跳过重复连接: {device_info.name}")
                    return

            if device_type == DeviceType.CONVEYOR_BELT:
                try:
                    if port and isinstance(port, str) and port.startswith('COM'):
                        controller = BeltController(port=port, hardware_enabled=True)
                        if controller.connected:
                            self.connected_devices[device_type] = controller
                            logger.info(f"传送带硬件连接成功: {device_info.name} -> {port}")
                            return
                        else:
                            logger.warning(f"传送带硬件连接失败: {device_info.name} -> {port}")
                    else:
                        logger.warning(f"无效的传送带端口: {port}")
                except Exception as e:
                    logger.error(f"传送带硬件连接异常: {device_info.name} -> {port}, 错误: {e}")

                controller = BeltController(hardware_enabled=False)
                self.connected_devices[device_type] = controller
                logger.info(f"传送带使用软件模式: {device_info.name}")
                return

            if device_type == DeviceType.ROBOT_ARM:
                try:
                    if not port or not isinstance(port, str) or not port.startswith('COM'):
                        logger.warning(f"无效的串口格式: {port}，使用默认端口")
                        port = self.default_ports[DeviceType.ROBOT_ARM]

                    controller = RobotArm(serial_port=port)
                    if controller.connected:
                        self.connected_devices[device_type] = controller
                        logger.info(f"机械臂连接成功: {device_info.name} -> {port}")
                    else:
                        logger.warning(f"机械臂连接失败: {device_info.name} -> {port}")
                        self._record_connection_failure(device_info.device_id)
                except Exception as e:
                    logger.error(f"机械臂连接异常: {device_info.name} -> {port}, 错误: {e}")
                    self._record_connection_failure(device_info.device_id)

        except Exception as e:
            logger.error(f"设备连接失败 {device_info.name}: {e}")
            self._record_connection_failure(device_info.device_id)

    def get_device_controller(self, device_type: DeviceType):
        with self.lock:
            return self.connected_devices.get(device_type)

    def get_robot_arm(self) -> Optional[RobotArm]:
        return self.get_device_controller(DeviceType.ROBOT_ARM)

    def get_belt_controller(self) -> Optional[BeltController]:
        return self.get_device_controller(DeviceType.CONVEYOR_BELT)

    def reconnect_device(self, device_type: DeviceType, port: str = None) -> bool:
        with self.lock:
            try:
                if hasattr(self, '_connection_failures'):
                    device_id = f"{device_type.value}_{port}" if port else device_type.value
                    failure_count = self._connection_failures.get(device_id, 0)
                    if failure_count >= 3:
                        logger.warning(f"设备连接失败次数过多，跳过重试: {device_type.value}")
                        return False

                if device_type in self.connected_devices:
                    old_controller = self.connected_devices[device_type]
                    if hasattr(old_controller, 'close'):
                        try:
                            old_controller.close()
                        except Exception as e:
                            logger.warning(f"关闭设备连接时出错: {e}")
                    del self.connected_devices[device_type]

                if device_type == DeviceType.ROBOT_ARM:
                    if not port:
                        paired_devices = self.scanner.get_paired_devices()
                        for device in paired_devices:
                            if device.device_type == device_type and device.auto_connect:
                                port = device.connection_info
                                break

                    if port:
                        if not isinstance(port, str) or not port.startswith('COM'):
                            logger.warning(f"无效的串口格式: {port}")
                            return False

                        controller = RobotArm(serial_port=port)
                        if controller.connected:
                            self.connected_devices[device_type] = controller
                            logger.info(f"机械臂重新连接成功: {port}")
                            self._clear_connection_failure(f"{device_type.value}_{port}")
                            return True
                        else:
                            logger.warning(f"机械臂重新连接失败: {port}")
                            self._record_connection_failure(f"{device_type.value}_{port}")
                            return False
                    else:
                        logger.warning("未找到有效的端口进行机械臂重连")
                        return False

                elif device_type == DeviceType.CONVEYOR_BELT:
                    if not port:
                        paired_devices = self.scanner.get_paired_devices()
                        for device in paired_devices:
                            if device.device_type == device_type and device.auto_connect:
                                port = device.connection_info
                                break

                    if port:
                        if not isinstance(port, str) or not port.startswith('COM'):
                            logger.warning(f"无效的串口格式: {port}")
                            return False

                        try:
                            controller = BeltController(port=port, hardware_enabled=True)
                            if controller.connected:
                                self.connected_devices[device_type] = controller
                                logger.info(f"传送带重新连接成功: {port}")
                                return True
                            else:
                                logger.warning(f"传送带重新连接失败: {port}")
                        except Exception as e:
                            logger.error(f"传送带重新连接异常: {port}, 错误: {e}")

                    controller = BeltController(hardware_enabled=False)
                    self.connected_devices[device_type] = controller
                    logger.info("传送带重新连接成功（软件模式）")
                    return True

            except Exception as e:
                logger.error(f"重新连接设备失败 {device_type}: {e}")
                device_id = f"{device_type.value}_{port}" if port else device_type.value
                self._record_connection_failure(device_id)
                return False

            return False

    def get_connection_status(self) -> Dict[str, Any]:
        with self.lock:
            status = {
                "initialized": self.initialized,
                "connected_devices": {},
                "total_connected": len(self.connected_devices)
            }

            for device_type, controller in self.connected_devices.items():
                if device_type == DeviceType.ROBOT_ARM:
                    status["connected_devices"]["robot_arm"] = {
                        "connected": controller.connected,
                        "port": controller.serial_port if hasattr(controller, 'serial_port') else "N/A"
                    }
                elif device_type == DeviceType.CONVEYOR_BELT:
                    status["connected_devices"]["conveyor_belt"] = {
                        "connected": controller.connected,
                        "hardware_enabled": controller.hardware_enabled,
                        "port": "COM7" if controller.hardware_enabled else "软件模式"
                    }

            return status

    def close_all_connections(self):
        with self.lock:
            for device_type, controller in self.connected_devices.items():
                try:
                    if hasattr(controller, 'close'):
                        controller.close()
                        logger.info(f"已关闭 {device_type.value} 连接")
                except Exception as e:
                    logger.error(f"关闭 {device_type.value} 连接时出错: {e}")

            self.connected_devices.clear()
            self.initialized = False
            logger.info("所有设备连接已关闭")


    def _record_connection_failure(self, device_id: str):
        if not hasattr(self, '_connection_failures'):
            self._connection_failures = {}

        current_count = self._connection_failures.get(device_id, 0)
        self._connection_failures[device_id] = current_count + 1
        logger.warning(f"记录设备连接失败: {device_id}, 失败次数: {current_count + 1}")

    def _clear_connection_failure(self, device_id: str):
        if hasattr(self, '_connection_failures') and device_id in self._connection_failures:
            del self._connection_failures[device_id]
            logger.info(f"清除设备连接失败记录: {device_id}")

    def get_connection_failure_count(self, device_id: str) -> int:
        if hasattr(self, '_connection_failures'):
            return self._connection_failures.get(device_id, 0)
        return 0

    def reset_connection_failures(self):
        if hasattr(self, '_connection_failures'):
            self._connection_failures.clear()
            logger.info("已重置所有设备连接失败记录")


_device_connection_manager = None

def get_device_connection_manager() -> DeviceConnectionManager:
    global _device_connection_manager
    if _device_connection_manager is None:
        _device_connection_manager = DeviceConnectionManager()
    return _device_connection_manager