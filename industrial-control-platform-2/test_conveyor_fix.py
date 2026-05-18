#!/usr/bin/env python3

import logging
import sys
import os
import time
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_BASE_URL = 'http://localhost:5000/api'

def test_conveyor_status():
    try:
        logger.info("测试传送带状态获取...")
        response = requests.get(f"{API_BASE_URL}/conveyor/status")
        data = response.json()

        if response.status_code == 200 and data.get('success'):
            status = data.get('data', {})
            logger.info(f"传送带状态: 运行={status.get('isRunning')}, 速度={status.get('currentSpeed')} m/s, 方向={status.get('direction')}")
            return True
        else:
            logger.error(f"获取传送带状态失败: {data.get('message')}")
            return False

    except Exception as e:
        logger.error(f"测试传送带状态时出错: {e}")
        return False

def test_conveyor_start():
    try:
        logger.info("测试传送带启动...")

        payload = {
            "speed": 0.1,
            "direction": "forward",
            "action": "start"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=payload)
        data = response.json()

        if response.status_code == 200 and data.get('success'):
            logger.info(f"传送带启动成功: {data.get('message')}")

            time.sleep(2)
            status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
            status_data = status_response.json()

            if status_data.get('success'):
                status = status_data.get('data', {})
                logger.info(f"启动后状态: 运行={status.get('isRunning')}, 速度={status.get('currentSpeed')} m/s")
                return status.get('isRunning', False)
            else:
                logger.error("启动后无法获取状态")
                return False
        else:
            logger.error(f"传送带启动失败: {data.get('message')}")
            return False

    except Exception as e:
        logger.error(f"测试传送带启动时出错: {e}")
        return False

def test_conveyor_speed_change():
    try:
        logger.info("测试传送带速度调整...")

        start_payload = {
            "speed": 0.1,
            "direction": "forward",
            "action": "start"
        }

        start_response = requests.post(f"{API_BASE_URL}/conveyor/control", json=start_payload)
        if not start_response.json().get('success'):
            logger.error("无法启动传送带进行速度测试")
            return False

        time.sleep(1)

        speed_payload = {
            "speed": 0.3,
            "direction": "forward",
            "action": "set_speed"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=speed_payload)
        data = response.json()

        if response.status_code == 200 and data.get('success'):
            logger.info(f"速度调整成功: {data.get('message')}")

            time.sleep(2)
            status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
            status_data = status_response.json()

            if status_data.get('success'):
                status = status_data.get('data', {})
                current_speed = status.get('currentSpeed', 0)
                logger.info(f"速度调整后状态: 速度={current_speed} m/s")

                return abs(current_speed - 0.3) < 0.01
            else:
                logger.error("速度调整后无法获取状态")
                return False
        else:
            logger.error(f"速度调整失败: {data.get('message')}")
            return False

    except Exception as e:
        logger.error(f"测试传送带速度调整时出错: {e}")
        return False

def test_conveyor_stop():
    try:
        logger.info("测试传送带停止...")

        start_payload = {
            "speed": 0.1,
            "direction": "forward",
            "action": "start"
        }

        start_response = requests.post(f"{API_BASE_URL}/conveyor/control", json=start_payload)
        time.sleep(1)

        stop_payload = {
            "speed": 0,
            "direction": "forward",
            "action": "stop"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=stop_payload)
        data = response.json()

        if response.status_code == 200 and data.get('success'):
            logger.info(f"传送带停止成功: {data.get('message')}")

            time.sleep(2)
            status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
            status_data = status_response.json()

            if status_data.get('success'):
                status = status_data.get('data', {})
                is_running = status.get('isRunning', True)
                current_speed = status.get('currentSpeed', 0)
                logger.info(f"停止后状态: 运行={is_running}, 速度={current_speed} m/s")
                return not is_running and current_speed == 0
            else:
                logger.error("停止后无法获取状态")
                return False
        else:
            logger.error(f"传送带停止失败: {data.get('message')}")
            return False

    except Exception as e:
        logger.error(f"测试传送带停止时出错: {e}")
        return False

def test_emergency_stop():
    try:
        logger.info("测试紧急停止...")

        start_payload = {
            "speed": 0.2,
            "direction": "forward",
            "action": "start"
        }

        start_response = requests.post(f"{API_BASE_URL}/conveyor/control", json=start_payload)
        time.sleep(1)

        emergency_payload = {
            "speed": 0,
            "direction": "forward",
            "action": "emergency_stop"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=emergency_payload)
        data = response.json()

        if response.status_code == 200 and data.get('success'):
            logger.info(f"紧急停止成功: {data.get('message')}")

            time.sleep(2)
            status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
            status_data = status_response.json()

            if status_data.get('success'):
                status = status_data.get('data', {})
                is_running = status.get('isRunning', True)
                current_speed = status.get('currentSpeed', 0)
                status_text = status.get('status', '')
                logger.info(f"紧急停止后状态: 运行={is_running}, 速度={current_speed} m/s, 状态={status_text}")
                return not is_running and current_speed == 0 and status_text == 'emergency_stop'
            else:
                logger.error("紧急停止后无法获取状态")
                return False
        else:
            logger.error(f"紧急停止失败: {data.get('message')}")
            return False

    except Exception as e:
        logger.error(f"测试紧急停止时出错: {e}")
        return False

def test_direction_control():
    try:
        logger.info("测试方向控制功能...")

        start_payload = {
            "speed": 0.1,
            "direction": "forward",
            "action": "start"
        }

        start_response = requests.post(f"{API_BASE_URL}/conveyor/control", json=start_payload)
        if not start_response.json().get('success'):
            logger.error("无法启动传送带进行方向测试")
            return False

        time.sleep(1)

        status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
        status_data = status_response.json()

        if not status_data.get('success'):
            logger.error("无法获取传送带状态")
            return False

        initial_status = status_data.get('data', {})
        initial_direction = initial_status.get('direction', 'forward')
        logger.info(f"初始方向: {initial_direction}")

        reverse_payload = {
            "speed": 0.1,
            "direction": "backward",
            "action": "set_speed"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=reverse_payload)
        data = response.json()

        if response.status_code == 200 and data.get('success'):
            logger.info(f"方向切换成功: {data.get('message')}")

            time.sleep(2)
            status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
            status_data = status_response.json()

            if status_data.get('success'):
                status = status_data.get('data', {})
                current_direction = status.get('direction', 'forward')
                current_speed = status.get('currentSpeed', 0)
                is_running = status.get('isRunning', False)

                logger.info(f"方向切换后状态: 方向={current_direction}, 速度={current_speed} m/s, 运行={is_running}")

                return (current_direction == 'backward' and
                       abs(current_speed - 0.1) < 0.01 and
                       is_running == True)
            else:
                logger.error("方向切换后无法获取状态")
                return False
        else:
            logger.error(f"方向切换失败: {data.get('message')}")
            return False

    except Exception as e:
        logger.error(f"测试方向控制时出错: {e}")
        return False

def test_direction_persistence_on_stop():
    try:
        logger.info("测试停止时方向保持功能...")

        start_payload = {
            "speed": 0.1,
            "direction": "backward",
            "action": "start"
        }

        start_response = requests.post(f"{API_BASE_URL}/conveyor/control", json=start_payload)
        if not start_response.json().get('success'):
            logger.error("无法启动传送带进行方向保持测试")
            return False

        time.sleep(1)

        stop_payload = {
            "speed": 0,
            "direction": "backward",
            "action": "stop"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=stop_payload)
        data = response.json()

        if response.status_code == 200 and data.get('success'):
            logger.info(f"停止成功: {data.get('message')}")

            time.sleep(2)
            status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
            status_data = status_response.json()

            if status_data.get('success'):
                status = status_data.get('data', {})
                current_direction = status.get('direction', 'forward')
                current_speed = status.get('currentSpeed', 0)
                is_running = status.get('isRunning', True)

                logger.info(f"停止后状态: 方向={current_direction}, 速度={current_speed} m/s, 运行={is_running}")

                return (current_direction == 'backward' and
                       current_speed == 0 and
                       is_running == False)
            else:
                logger.error("停止后无法获取状态")
                return False
        else:
            logger.error(f"停止失败: {data.get('message')}")
            return False

    except Exception as e:
        logger.error(f"测试停止时方向保持功能出错: {e}")
        return False

def main():
    logger.info("=== 开始传送带控制修复测试 ===")

    status_success = test_conveyor_status()

    start_success = test_conveyor_start()

    speed_success = test_conveyor_speed_change()

    stop_success = test_conveyor_stop()

    emergency_success = test_emergency_stop()

    direction_success = test_direction_control()

    direction_persistence_success = test_direction_persistence_on_stop()

    logger.info("=== 测试结果汇总 ===")
    logger.info(f"状态获取测试: {'成功' if status_success else '失败'}")
    logger.info(f"启动测试: {'成功' if start_success else '失败'}")
    logger.info(f"速度调整测试: {'成功' if speed_success else '失败'}")
    logger.info(f"停止测试: {'成功' if stop_success else '失败'}")
    logger.info(f"紧急停止测试: {'成功' if emergency_success else '失败'}")
    logger.info(f"方向控制测试: {'成功' if direction_success else '失败'}")
    logger.info(f"方向保持测试: {'成功' if direction_persistence_success else '失败'}")

    all_tests = [status_success, start_success, speed_success, stop_success,
                 emergency_success, direction_success, direction_persistence_success]

    if all(all_tests):
        logger.info("🎉 所有传送带控制测试通过！修复成功。")
        logger.info("✓ 传送带可以正常启动")
        logger.info("✓ 传送带速度可以调整")
        logger.info("✓ 传送带可以正常停止")
        logger.info("✓ 紧急停止功能正常")
        return 0
    else:
        logger.error("❌ 部分传送带控制测试失败，需要进一步调试。")
        return 1

if __name__ == "__main__":
    sys.exit(main())