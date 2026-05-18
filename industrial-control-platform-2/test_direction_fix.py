#!/usr/bin/env python3

import logging
import sys
import requests
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_BASE_URL = 'http://localhost:5000/api'

def test_direction_switching():
    try:
        logger.info("=== 开始方向切换测试 ===")

        logger.info("步骤1: 启动传送带（正向）...")
        start_payload = {
            "speed": 0.1,
            "direction": "forward",
            "action": "start"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=start_payload)
        data = response.json()

        if not (response.status_code == 200 and data.get('success')):
            logger.error(f"启动失败: {data.get('message')}")
            return False

        time.sleep(1)

        logger.info("步骤2: 检查初始状态...")
        status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
        status_data = status_response.json()

        if not status_data.get('success'):
            logger.error("无法获取状态")
            return False

        initial_status = status_data.get('data', {})
        initial_direction = initial_status.get('direction', 'unknown')
        initial_speed = initial_status.get('currentSpeed', 0)
        initial_running = initial_status.get('isRunning', False)

        logger.info(f"初始状态: 方向={initial_direction}, 速度={initial_speed} m/s, 运行={initial_running}")

        if initial_direction != 'forward' or not initial_running or abs(initial_speed - 0.1) > 0.01:
            logger.error("初始状态不符合预期")
            return False

        logger.info("步骤3: 切换到反向...")
        reverse_payload = {
            "speed": 0.1,
            "direction": "backward",
            "action": "set_speed"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=reverse_payload)
        data = response.json()

        if not (response.status_code == 200 and data.get('success')):
            logger.error(f"方向切换失败: {data.get('message')}")
            return False

        time.sleep(2)

        logger.info("步骤4: 验证方向切换结果...")
        status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
        status_data = status_response.json()

        if not status_data.get('success'):
            logger.error("无法获取切换后的状态")
            return False

        final_status = status_data.get('data', {})
        final_direction = final_status.get('direction', 'unknown')
        final_speed = final_status.get('currentSpeed', 0)
        final_running = final_status.get('isRunning', False)

        logger.info(f"切换后状态: 方向={final_direction}, 速度={final_speed} m/s, 运行={final_running}")

        direction_correct = final_direction == 'backward'
        speed_maintained = abs(final_speed - 0.1) < 0.01
        still_running = final_running == True

        if direction_correct and speed_maintained and still_running:
            logger.info("✅ 方向切换测试成功！")
            logger.info("✓ 方向已从正向切换到反向")
            logger.info("✓ 速度保持不变")
            logger.info("✓ 传送带仍在运行")
            return True
        else:
            logger.error("❌ 方向切换测试失败")
            if not direction_correct:
                logger.error("  - 方向未正确切换")
            if not speed_maintained:
                logger.error("  - 速度发生变化")
            if not still_running:
                logger.error("  - 传送带停止运行")
            return False

    except Exception as e:
        logger.error(f"方向切换测试出错: {e}")
        return False

def test_direction_persistence():
    try:
        logger.info("=== 开始方向保持测试 ===")

        logger.info("步骤1: 启动传送带（反向）...")
        start_payload = {
            "speed": 0.1,
            "direction": "backward",
            "action": "start"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=start_payload)
        if not response.json().get('success'):
            logger.error("启动失败")
            return False

        time.sleep(1)

        logger.info("步骤2: 停止传送带...")
        stop_payload = {
            "speed": 0,
            "direction": "backward",
            "action": "stop"
        }

        response = requests.post(f"{API_BASE_URL}/conveyor/control", json=stop_payload)
        data = response.json()

        if not (response.status_code == 200 and data.get('success')):
            logger.error(f"停止失败: {data.get('message')}")
            return False

        time.sleep(2)

        logger.info("步骤3: 验证方向保持...")
        status_response = requests.get(f"{API_BASE_URL}/conveyor/status")
        status_data = status_response.json()

        if not status_data.get('success'):
            logger.error("无法获取状态")
            return False

        final_status = status_data.get('data', {})
        final_direction = final_status.get('direction', 'unknown')
        final_speed = final_status.get('currentSpeed', 0)
        final_running = final_status.get('isRunning', True)

        logger.info(f"停止后状态: 方向={final_direction}, 速度={final_speed} m/s, 运行={final_running}")

        direction_maintained = final_direction == 'backward'
        properly_stopped = final_speed == 0 and not final_running

        if direction_maintained and properly_stopped:
            logger.info("✅ 方向保持测试成功！")
            logger.info("✓ 停止后方向保持为反向")
            logger.info("✓ 传送带已正确停止")
            return True
        else:
            logger.error("❌ 方向保持测试失败")
            if not direction_maintained:
                logger.error("  - 方向未保持")
            if not properly_stopped:
                logger.error("  - 停止状态不正确")
            return False

    except Exception as e:
        logger.error(f"方向保持测试出错: {e}")
        return False

def main():
    logger.info("🚀 开始传送带方向控制修复验证")

    switch_success = test_direction_switching()

    persistence_success = test_direction_persistence()

    logger.info("\n=== 测试结果汇总 ===")
    logger.info(f"方向切换测试: {'✅ 成功' if switch_success else '❌ 失败'}")
    logger.info(f"方向保持测试: {'✅ 成功' if persistence_success else '❌ 失败'}")

    if switch_success and persistence_success:
        logger.info("\n🎉 所有方向控制测试通过！修复成功。")
        logger.info("✓ 传送带可以正常切换方向")
        logger.info("✓ 停止时方向能够正确保持")
        return 0
    else:
        logger.error("\n❌ 部分方向控制测试失败，需要进一步调试。")
        return 1

if __name__ == "__main__":
    sys.exit(main())