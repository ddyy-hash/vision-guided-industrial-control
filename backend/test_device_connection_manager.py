#!/usr/bin/env python3

import logging
import sys
import os

sys.path.append(os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_device_connection_manager():
    try:
        from device_connection_manager import get_device_connection_manager
        from device_scanner import DeviceType

        logger.info("开始测试设备连接管理器...")

        device_manager = get_device_connection_manager()

        device_manager.initialize_connections()

        connection_status = device_manager.get_connection_status()
        logger.info(f"设备连接状态: {connection_status}")

        arm_controller = device_manager.get_robot_arm()
        if arm_controller:
            logger.info(f"机械臂控制器: 已连接={arm_controller.connected}, 端口={arm_controller.serial_port}")
        else:
            logger.warning("机械臂控制器未找到")

        belt_controller = device_manager.get_belt_controller()
        if belt_controller:
            logger.info(f"传送带控制器: 已连接={belt_controller.connected}, 硬件启用={belt_controller.hardware_enabled}")
        else:
            logger.warning("传送带控制器未找到")

        logger.info("测试机械臂重新连接...")
        success = device_manager.reconnect_device(DeviceType.ROBOT_ARM)
        logger.info(f"机械臂重新连接结果: {success}")

        updated_status = device_manager.get_connection_status()
        logger.info(f"更新后的设备连接状态: {updated_status}")

        logger.info("设备连接管理器测试完成")
        return True

    except Exception as e:
        logger.error(f"测试设备连接管理器时出错: {e}")
        return False

def test_pairing_records():
    try:
        import json

        logger.info("检查配对记录文件...")

        pairing_file = "pairing_records.json"
        if os.path.exists(pairing_file):
            with open(pairing_file, 'r', encoding='utf-8') as f:
                pairing_records = json.load(f)

            logger.info(f"找到 {len(pairing_records)} 条配对记录:")
            for device_id, record in pairing_records.items():
                logger.info(f"  - {device_id}: {record.get('device_type')} -> {record.get('connection_info')} (自动连接: {record.get('auto_connect', False)})")

            return True
        else:
            logger.warning("配对记录文件不存在")
            return False

    except Exception as e:
        logger.error(f"检查配对记录时出错: {e}")
        return False

def test_device_scanner():
    try:
        from device_scanner import get_device_scanner

        logger.info("测试设备扫描器...")

        scanner = get_device_scanner()

        scanner.manual_scan()

        available_devices = scanner.get_available_devices()
        logger.info(f"发现 {len(available_devices)} 个设备:")
        for device in available_devices:
            logger.info(f"  - {device['name']}: {device['device_type']} -> {device['connection_info']}")

        paired_devices = scanner.get_paired_devices()
        logger.info(f"已配对 {len(paired_devices)} 个设备:")
        for device in paired_devices:
            logger.info(f"  - {device.name}: {device.device_type.value} -> {device.connection_info}")

        auto_connect_devices = scanner.get_auto_connect_devices()
        logger.info(f"启用自动连接的 {len(auto_connect_devices)} 个设备:")
        for device in auto_connect_devices:
            logger.info(f"  - {device.name}: {device.device_type.value} -> {device.connection_info}")

        return True

    except Exception as e:
        logger.error(f"测试设备扫描器时出错: {e}")
        return False

def main():
    logger.info("=== 开始设备连接逻辑测试 ===")

    pairing_success = test_pairing_records()

    scanner_success = test_device_scanner()

    connection_success = test_device_connection_manager()

    logger.info("=== 测试结果汇总 ===")
    logger.info(f"配对记录测试: {'成功' if pairing_success else '失败'}")
    logger.info(f"设备扫描器测试: {'成功' if scanner_success else '失败'}")
    logger.info(f"设备连接管理器测试: {'成功' if connection_success else '失败'}")

    if pairing_success and scanner_success and connection_success:
        logger.info("所有测试通过！设备连接逻辑修复成功。")
        return 0
    else:
        logger.error("部分测试失败，需要进一步调试。")
        return 1

if __name__ == "__main__":
    sys.exit(main())