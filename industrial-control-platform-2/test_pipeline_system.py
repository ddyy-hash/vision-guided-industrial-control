#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"
API_PREFIX = "/api"

def test_api_endpoint(endpoint, method="GET", data=None):
    url = f"{BASE_URL}{API_PREFIX}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ {method} {endpoint} - 成功")
            return result
        else:
            print(f"❌ {method} {endpoint} - 失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ {method} {endpoint} - 异常: {e}")
        return None

def test_pipeline_status():
    print("\n=== 测试流水线状态 ===")
    result = test_api_endpoint("/pipeline/status")
    if result and result.get('success'):
        status = result.get('data', {})
        pipeline_state = status.get('pipeline_state', {})
        print(f"流水线状态: {pipeline_state.get('status', 'unknown')}")
        print(f"当前步骤: {pipeline_state.get('current_step', 'unknown')}")
        print(f"处理计数: {pipeline_state.get('processed_count', 0)}")
        return True
    return False

def test_start_pipeline():
    print("\n=== 测试启动流水线 ===")
    result = test_api_endpoint("/pipeline/control", "POST", {"action": "start"})
    if result:
        print(f"启动结果: {result.get('message', 'unknown')}")
        return result.get('success', False)
    return False

def test_stop_pipeline():
    print("\n=== 测试停止流水线 ===")
    result = test_api_endpoint("/pipeline/control", "POST", {"action": "stop"})
    if result:
        print(f"停止结果: {result.get('message', 'unknown')}")
        return result.get('success', False)
    return False

def test_tracking_service():
    print("\n=== 测试追踪服务 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/tracking/status")
        if response.status_code == 200:
            status = response.json()
            print(f"追踪服务状态: {status.get('success', False)}")
            if status.get('success'):
                data = status.get('data', {})
                print(f"追踪运行状态: {data.get('is_running', False)}")
                print(f"活跃追踪数: {data.get('active_tracks', 0)}")
                print(f"FPS: {data.get('fps', 0):.1f}")
                return True
        else:
            print(f"追踪服务测试失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"追踪服务测试异常: {e}")
        return False

def test_conveyor_service():
    print("\n=== 测试传送带服务 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/conveyor/status")
        if response.status_code == 200:
            status = response.json()
            print(f"传送带服务状态: {status.get('success', False)}")
            if status.get('success'):
                data = status.get('data', {})
                print(f"传送带运行状态: {data.get('isRunning', False)}")
                print(f"当前速度: {data.get('currentSpeed', 0):.3f} m/s")
                print(f"方向: {data.get('direction', 'unknown')}")
                return True
        else:
            print(f"传送带服务测试失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"传送带服务测试异常: {e}")
        return False

def test_system_integration():
    print("\n=== 测试系统集成 ===")

    print("1. 检查初始状态...")
    if not test_pipeline_status():
        print("初始状态检查失败")
        return False

    print("2. 启动流水线...")
    if not test_start_pipeline():
        print("流水线启动失败")
        return False

    print("等待系统启动...")
    time.sleep(3)

    print("3. 检查运行状态...")
    if not test_pipeline_status():
        print("运行状态检查失败")
        return False

    print("4. 检查各个子服务...")
    tracking_ok = test_tracking_service()
    conveyor_ok = test_conveyor_service()

    if tracking_ok and conveyor_ok:
        print("✅ 所有子服务正常运行")
    else:
        print("⚠️  部分子服务异常")

    print("5. 运行测试...")
    print("系统运行中，模拟工作流程...")

    for i in range(10):
        time.sleep(1)
        if i % 3 == 0:
            result = test_api_endpoint("/pipeline/status")
            if result and result.get('success'):
                status = result.get('data', {})
                pipeline_state = status.get('pipeline_state', {})
                print(f"状态更新: {pipeline_state.get('current_step', 'unknown')}")

    print("6. 停止系统...")
    if test_stop_pipeline():
        print("✅ 系统停止成功")
    else:
        print("❌ 系统停止失败")

    return True

def test_error_handling():
    print("\n=== 测试错误处理 ===")

    print("1. 测试重复启动...")
    test_start_pipeline()
    time.sleep(1)
    result = test_start_pipeline()
    if result and not result.get('success') and '已在运行' in result.get('message', ''):
        print("✅ 重复启动处理正确")
    else:
        print("⚠️  重复启动处理异常")

    print("2. 测试无效操作...")
    result = test_api_endpoint("/pipeline/control", "POST", {"action": "invalid"})
    if result and not result.get('success'):
        print("✅ 无效操作处理正确")
    else:
        print("⚠️  无效操作处理异常")

    return True

def main():
    print("=" * 60)
    print("智能流水线系统测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        test_system_integration()

        test_error_handling()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)

        print("\n最终状态检查:")
        test_pipeline_status()

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        return False

    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)