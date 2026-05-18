#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import sys

API_BASE_URL = "http://localhost:5000/api"

def test_custom_arm_sequence():
    print("=== 测试自定义机械臂序列功能 ===")

    custom_sequence = [
        {
            "name": "测试初始位置",
            "duration": 1000,
            "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -75},
                {"jointId": 4, "angle": 60},
                {"jointId": 5, "angle": 45},
                {"jointId": 6, "angle": 90}
            ]
        },
        {
            "name": "测试抓取位置",
            "duration": 1000,
            "actions": [
                {"jointId": 1, "angle": 130},
                {"jointId": 3, "angle": -20},
                {"jointId": 4, "angle": 80},
                {"jointId": 5, "angle": 140},
                {"jointId": 6, "angle": 90}
            ]
        },
        {
            "name": "测试抓取动作",
            "duration": 500,
            "actions": [
                {"jointId": 1, "angle": 0}
            ]
        }
    ]

    try:
        print("1. 设置自定义机械臂序列...")
        response = requests.post(
            f"{API_BASE_URL}/pipeline/arm_sequence",
            json={"sequence": custom_sequence}
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✓ 自定义序列设置成功: {result.get('message')}")
            else:
                print(f"✗ 自定义序列设置失败: {result.get('message')}")
                return False
        else:
            print(f"✗ API请求失败: {response.status_code}")
            return False

        print("2. 验证自定义序列...")
        response = requests.get(f"{API_BASE_URL}/pipeline/arm_sequence")

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                saved_sequence = result.get("data", {}).get("sequence", [])
                sequence_count = result.get("data", {}).get("count", 0)
                print(f"✓ 获取序列成功，共 {sequence_count} 个步骤")

                if len(saved_sequence) == len(custom_sequence):
                    print("✓ 序列长度验证通过")
                else:
                    print(f"✗ 序列长度不匹配: 期望 {len(custom_sequence)}, 实际 {len(saved_sequence)}")
                    return False
            else:
                print(f"✗ 获取序列失败: {result.get('message')}")
                return False
        else:
            print(f"✗ 获取序列API请求失败: {response.status_code}")
            return False

        print("3. 检查流水线状态...")
        response = requests.get(f"{API_BASE_URL}/pipeline/status")

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                config = result.get("data", {}).get("config", {})
                custom_arm_sequence = config.get("custom_arm_sequence", [])
                print(f"✓ 流水线状态获取成功，自定义序列包含 {len(custom_arm_sequence)} 个步骤")

                if len(custom_arm_sequence) == len(custom_sequence):
                    print("✓ 流水线配置中的序列验证通过")
                else:
                    print(f"✗ 流水线配置中的序列长度不匹配")
                    return False
            else:
                print(f"✗ 获取流水线状态失败: {result.get('message')}")
                return False
        else:
            print(f"✗ 获取状态API请求失败: {response.status_code}")
            return False

        print("4. 测试序列格式验证...")

        invalid_sequences = [
            {"invalid": "sequence"},
            {"name": "测试", "duration": 1000, "actions": "不是数组"},
            {"name": "测试", "duration": 1000, "actions": [{"angle": 90}]}
        ]

        for i, invalid_seq in enumerate(invalid_sequences):
            response = requests.post(
                f"{API_BASE_URL}/pipeline/arm_sequence",
                json={"sequence": [invalid_seq]}
            )

            if response.status_code == 400:
                result = response.json()
                if not result.get("success"):
                    print(f"✓ 无效序列 {i+1} 正确被拒绝: {result.get('message')}")
                else:
                    print(f"✗ 无效序列 {i+1} 应该被拒绝")
                    return False
            else:
                print(f"✗ 无效序列 {i+1} 验证失败，状态码: {response.status_code}")
                return False

        print("✓ 所有测试通过！")
        return True

    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到后端服务，请确保后端服务正在运行")
        return False
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {str(e)}")
        return False

def test_pipeline_with_custom_sequence():
    print("\n=== 测试流水线使用自定义序列 ===")

    try:
        print("1. 启动流水线...")
        response = requests.post(f"{API_BASE_URL}/pipeline/control", json={"action": "start"})

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✓ 流水线启动成功")
            else:
                print(f"✗ 流水线启动失败: {result.get('message')}")
                return False
        else:
            print(f"✗ 启动流水线API请求失败: {response.status_code}")
            return False

        print("2. 确认流水线状态...")
        time.sleep(1)

        response = requests.get(f"{API_BASE_URL}/pipeline/status")
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                pipeline_state = result.get("data", {}).get("pipeline_state", {})
                status = pipeline_state.get("status")
                if status == "running":
                    print("✓ 流水线状态为运行中")
                else:
                    print(f"✗ 流水线状态异常: {status}")
                    return False
            else:
                print(f"✗ 获取状态失败: {result.get('message')}")
                return False
        else:
            print(f"✗ 获取状态API请求失败: {response.status_code}")
            return False

        print("3. 停止流水线...")
        response = requests.post(f"{API_BASE_URL}/pipeline/control", json={"action": "stop"})

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✓ 流水线停止成功")
            else:
                print(f"✗ 流水线停止失败: {result.get('message')}")
                return False
        else:
            print(f"✗ 停止流水线API请求失败: {response.status_code}")
            return False

        print("✓ 流水线测试通过！")
        return True

    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到后端服务")
        return False
    except Exception as e:
        print(f"✗ 测试过程中发生错误: {str(e)}")
        return False

def main():
    print("开始测试自定义机械臂序列功能...")
    print(f"API地址: {API_BASE_URL}")
    print("-" * 50)

    success1 = test_custom_arm_sequence()

    success2 = test_pipeline_with_custom_sequence()

    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 所有测试通过！自定义机械臂序列功能正常工作。")
        return 0
    else:
        print("❌ 部分测试失败，请检查错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())