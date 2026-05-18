#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000/api/pipeline"

def test_pipeline_control():

    print("开始测试流水线控制功能...")

    print("\n1. 获取流水线状态...")
    try:
        response = requests.get(f"{BASE_URL}/status")
        if response.status_code == 200:
            result = response.json()
            print(f"状态获取成功: {result}")
        else:
            print(f"状态获取失败: {response.status_code}")
    except Exception as e:
        print(f"状态获取异常: {e}")

    print("\n2. 启动流水线...")
    try:
        response = requests.post(f"{BASE_URL}/control", json={"action": "start"})
        if response.status_code == 200:
            result = response.json()
            print(f"启动结果: {result}")
        else:
            print(f"启动失败: {response.status_code}")
    except Exception as e:
        print(f"启动异常: {e}")

    print("\n3. 获取流水线统计信息...")
    try:
        response = requests.get(f"{BASE_URL}/stats")
        if response.status_code == 200:
            result = response.json()
            print(f"统计信息: {result}")
        else:
            print(f"统计信息获取失败: {response.status_code}")
    except Exception as e:
        print(f"统计信息获取异常: {e}")

    print("\n4. 暂停流水线...")
    try:
        response = requests.post(f"{BASE_URL}/control", json={"action": "pause"})
        if response.status_code == 200:
            result = response.json()
            print(f"暂停结果: {result}")
        else:
            print(f"暂停失败: {response.status_code}")
    except Exception as e:
        print(f"暂停异常: {e}")

    print("\n5. 恢复流水线...")
    try:
        response = requests.post(f"{BASE_URL}/control", json={"action": "resume"})
        if response.status_code == 200:
            result = response.json()
            print(f"恢复结果: {result}")
        else:
            print(f"恢复失败: {response.status_code}")
    except Exception as e:
        print(f"恢复异常: {e}")

    print("\n6. 停止流水线...")
    try:
        response = requests.post(f"{BASE_URL}/control", json={"action": "stop"})
        if response.status_code == 200:
            result = response.json()
            print(f"停止结果: {result}")
        else:
            print(f"停止失败: {response.status_code}")
    except Exception as e:
        print(f"停止异常: {e}")

    print("\n7. 获取处理历史...")
    try:
        response = requests.get(f"{BASE_URL}/history?limit=5")
        if response.status_code == 200:
            result = response.json()
            print(f"处理历史: {result}")
        else:
            print(f"处理历史获取失败: {response.status_code}")
    except Exception as e:
        print(f"处理历史获取异常: {e}")

    print("\n流水线控制功能测试完成！")

if __name__ == "__main__":
    test_pipeline_control()