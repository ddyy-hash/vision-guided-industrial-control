#!/usr/bin/env python3

import logging
import sys
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__))

from services.device_connection_manager import get_device_connection_manager
from api.belt import BeltController

def diagnose_conveyor_hardware():
    logger.info("=== 开始传送带硬件连接诊断 ===")

    device_manager = get_device_connection_manager()

    logger.info("初始化设备连接...")
    device_manager.initialize_connections()

    connection_status = device_manager.get_connection_status()
    logger.info(f"当前设备连接状态: {connection_status}")

    belt_controller = device_manager.get_belt_controller()
    if not belt_controller:
        logger.error("❌ 传送带控制器未初始化")
        return False

    logger.info(f"传送带控制器类型: {type(belt_controller).__name__}")
    logger.info(f"硬件启用: {getattr(belt_controller, 'hardware_enabled', 'N/A')}")
    logger.info(f"已连接: {getattr(belt_controller, 'connected', 'N/A')}")
    logger.info(f"端口: {getattr(belt_controller, 'ser', 'N/A')}")

    try:
        hardware_status = belt_controller.get_status()
        logger.info(f"硬件状态: {hardware_status}")
    except Exception as e:
        logger.error(f"获取硬件状态失败: {e}")
        hardware_status = {}

    if not hardware_status.get('hardware_enabled', False):
        logger.warning("⚠️ 传送带运行在软件模拟模式，不会控制实际硬件")

        logger.info("尝试强制硬件连接...")
        return force_hardware_connection()
    else:
        logger.info("✅ 传送带运行在硬件模式")

        return test_hardware_communication(belt_controller)

def force_hardware_connection():
    logger.info("=== 强制硬件连接 ===")

    try:
        logger.info("尝试连接COM5端口...")
        belt_controller = BeltController(port='COM5', hardware_enabled=True)

        if belt_controller.connected:
            logger.info("✅ 硬件连接成功！")
            logger.info(f"连接状态: {belt_controller.connected}")
            logger.info(f"端口: {belt_controller.ser.port if belt_controller.ser else 'N/A'}")

            logger.info("测试发送指令...")
            result = belt_controller.set_speed_mps(0.1, "forward")
            logger.info(f"指令发送结果: {result}")

            time.sleep(2)

            belt_controller.set_speed_mps(0, "forward")
            logger.info("✅ 硬件控制测试完成")

            return True
        else:
            logger.error("❌ 硬件连接失败")
            return False

    except Exception as e:
        logger.error(f"❌ 硬件连接异常: {e}")
        return False

def test_hardware_communication(belt_controller):
    logger.info("=== 测试硬件通信 ===")

    try:
        logger.info("测试低速运行 (0.05 m/s)...")
        result = belt_controller.set_speed_mps(0.05, "forward")
        logger.info(f"低速运行结果: {result}")

        time.sleep(3)

        logger.info("测试中速运行 (0.2 m/s)...")
        result = belt_controller.set_speed_mps(0.2, "forward")
        logger.info(f"中速运行结果: {result}")

        time.sleep(3)

        logger.info("停止传送带...")
        result = belt_controller.set_speed_mps(0, "forward")
        logger.info(f"停止结果: {result}")

        logger.info("✅ 硬件通信测试完成")
        return True

    except Exception as e:
        logger.error(f"❌ 硬件通信测试失败: {e}")
        return False

def check_serial_ports():
    logger.info("=== 检查可用串口 ===")

    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()

        if not ports:
            logger.warning("⚠️ 没有找到任何串口设备")
            return False

        logger.info(f"找到 {len(ports)} 个串口设备:")
        for port in ports:
            logger.info(f"  - {port.device}: {port.description} (VID:{port.vid:04X}, PID:{port.pid:04X})")

        com5_available = any(port.device == 'COM5' for port in ports)
        if com5_available:
            logger.info("✅ COM5端口可用")
        else:
            logger.warning("⚠️ COM5端口不可用")

        return True

    except ImportError:
        logger.error("❌ 无法导入serial模块")
        return False
    except Exception as e:
        logger.error(f"❌ 检查串口时出错: {e}")
        return False

def main():
    logger.info("传送带硬件连接诊断工具启动")

    check_serial_ports()

    hardware_ok = diagnose_conveyor_hardware()

    if hardware_ok:
        logger.info("🎉 传送带硬件连接诊断完成 - 硬件控制正常")
        return 0
    else:
        logger.error("❌ 传送带硬件连接诊断完成 - 发现问题")
        logger.info("\n可能的问题和解决方案:")
        logger.info("1. 检查传送带电源是否打开")
        logger.info("2. 检查USB连接线是否插好")
        logger.info("3. 检查设备管理器中的COM端口")
        logger.info("4. 尝试重新插拔USB线")
        logger.info("5. 检查Arduino固件是否正确烧录")
        return 1

if __name__ == "__main__":
    sys.exit(main())