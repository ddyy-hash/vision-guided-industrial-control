#!/usr/bin/env python3

import time
import requests
import json
from datetime import datetime

def test_robot_arm_control():
    print("=== 机械臂控制测试 ===")

    print("1. 测试直接关节角度控制...")
    try:
        response = requests.post('http://localhost:5000/api/arm/control',
                               json={
                                   'command': 'set_joint_angle',
                                   'joint_id': 1,
                                   'angle': 90,
                                   'movetime': 500
                               })
        result = response.json()
        print(f"   关节1角度设置结果: {result.get('success', False)}")
        print(f"   消息: {result.get('message', '无消息')}")
    except Exception as e:
        print(f"   关节角度控制测试失败: {e}")

    print("2. 测试动作序列执行...")
    try:
        sequence = [
            {
                "type": "joint",
                "joint_id": 1,
                "angle": 130,
                "movetime": 500
            },
            {
                "type": "joint",
                "joint_id": 3,
                "angle": -70,
                "movetime": 500
            },
            {
                "type": "joint",
                "joint_id": 4,
                "angle": 90,
                "movetime": 500
            }
        ]

        response = requests.post('http://localhost:5000/api/arm/sequence',
                               json={'sequence': sequence})
        result = response.json()
        print(f"   动作序列执行结果: {result.get('success', False)}")
        print(f"   消息: {result.get('message', '无消息')}")

    except Exception as e:
        print(f"   动作序列测试失败: {e}")

    print("3. 测试机械臂状态获取...")
    try:
        response = requests.get('http://localhost:5000/api/arm/status')
        result = response.json()
        if result.get('success'):
            status = result.get('data', {})
            print(f"   机械臂连接状态: {'已连接' if status.get('connected') else '未连接'}")
            print(f"   当前位置: {status.get('current_position', '未知')}")
            print(f"   夹爪状态: {'打开' if status.get('is_gripper_open') else '闭合'}")
        else:
            print(f"   获取状态失败: {result.get('message')}")
    except Exception as e:
        print(f"   状态获取测试失败: {e}")

    print("4. 测试夹爪控制...")
    try:
        response = requests.post('http://localhost:5000/api/arm/control',
                               json={'command': 'open_gripper'})
        result = response.json()
        print(f"   打开夹爪结果: {result.get('success', False)}")

        time.sleep(1)

        response = requests.post('http://localhost:5000/api/arm/control',
                               json={'command': 'close_gripper'})
        result = response.json()
        print(f"   关闭夹爪结果: {result.get('success', False)}")

    except Exception as e:
        print(f"   夹爪控制测试失败: {e}")

    print("5. 测试预设的取放序列...")
    try:
        response = requests.post('http://localhost:5000/api/pipeline/start')
        result = response.json()
        print(f"   流水线启动结果: {result.get('success', False)}")
        print(f"   消息: {result.get('message', '无消息')}")

        if result.get('success'):
            print("   等待机械臂序列执行...")
            time.sleep(30)

            response = requests.post('http://localhost:5000/api/pipeline/stop')
            result = response.json()
            print(f"   流水线停止结果: {result.get('success', False)}")

    except Exception as e:
        print(f"   预设序列测试失败: {e}")

    print("\n=== 机械臂控制测试完成 ===")

def test_individual_joint_control():
    print("\n=== 单个关节控制测试 ===")

    joints = [1, 3, 4, 5, 6]
    test_angles = [0, 45, 90, 135, 180]

    for joint_id in joints:
        print(f"测试关节 {joint_id}:")
        for angle in test_angles:
            try:
                response = requests.post('http://localhost:5000/api/arm/control',
                                       json={
                                           'command': 'set_joint_angle',
                                           'joint_id': joint_id,
                                           'angle': angle,
                                           'movetime': 300
                                       })
                result = response.json()
                print(f"   角度 {angle}°: {'成功' if result.get('success') else '失败'}")
                time.sleep(0.5)
            except Exception as e:
                print(f"   角度 {angle}°: 错误 - {e}")

    print("单个关节控制测试完成")

def test_sequence_with_different_formats():
    print("\n=== 不同格式动作序列测试 ===")

    print("测试格式1：直接参数格式")
    sequence1 = [
        {"type": "joint", "joint_id": 1, "angle": 90, "movetime": 500},
        {"type": "joint", "joint_id": 3, "angle": -45, "movetime": 500},
        {"type": "joint", "joint_id": 4, "angle": 60, "movetime": 500}
    ]

    try:
        response = requests.post('http://localhost:5000/api/arm/sequence',
                               json={'sequence': sequence1})
        result = response.json()
        print(f"   结果: {'成功' if result.get('success') else '失败'}")
        print(f"   消息: {result.get('message', '无消息')}")
    except Exception as e:
        print(f"   错误: {e}")

    print("测试格式2：params格式")
    sequence2 = [
        {"type": "joint", "params": {"joint": 1, "angle": 130, "movetime": 500}},
        {"type": "joint", "params": {"joint": 3, "angle": -70, "movetime": 500}}
    ]

    try:
        response = requests.post('http://localhost:5000/api/arm/sequence',
                               json={'sequence': sequence2})
        result = response.json()
        print(f"   结果: {'成功' if result.get('success') else '失败'}")
        print(f"   消息: {result.get('message', '无消息')}")
    except Exception as e:
        print(f"   错误: {e}")

    print("不同格式测试完成")

if __name__ == "__main__":
    test_robot_arm_control()
    test_individual_joint_control()
    test_sequence_with_different_formats()

    print("\n所有机械臂控制测试完成！")