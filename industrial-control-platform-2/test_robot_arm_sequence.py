#!/usr/bin/env python3
import requests
import json
import time
import sys

def test_robot_arm_status():
    print("=== 测试机械臂状态获取 ===")
    try:
        response = requests.get('http://localhost:5000/api/robot_arm/status')
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"机械臂状态: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"获取状态失败: {response.text}")
            return False
    except Exception as e:
        print(f"获取机械臂状态异常: {e}")
        return False

def test_execute_sequence():
    print("\n=== 测试执行机械臂动作序列 ===")

    sequence = [
        {"type": "joint", "joint": 6, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -75, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 60, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 45, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 90, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -70, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 90, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 80, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 90, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -45, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 85, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 110, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 90, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -20, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 80, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 140, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 90, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 0, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -20, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 80, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 140, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 90, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 0, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -10, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 75, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 120, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 70, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 0, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -10, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 70, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 100, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 45, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 0, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -10, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 65, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 120, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 20, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 0, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -20, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 60, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 140, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 0, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -20, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 60, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 140, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 0, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -32, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 70, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 120, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 30, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -45, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 70, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 100, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 45, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -57, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 80, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 90, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 60, "speed": 50},

        {"type": "joint", "joint": 6, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 5, "angle": -70, "speed": 50},
        {"type": "joint", "joint": 4, "angle": 90, "speed": 50},
        {"type": "joint", "joint": 3, "angle": 80, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 90, "speed": 50}
    ]

    print(f"发送动作序列，共 {len(sequence)} 个动作...")

    try:
        response = requests.post(
            'http://localhost:5000/api/robot_arm/execute_sequence',
            json={
                'actions': sequence,
                'protocol': 'http'
            },
            headers={'Content-Type': 'application/json'}
        )

        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if result.get('success'):
            print("✅ 机械臂序列执行成功！")
            return True
        else:
            print(f"❌ 机械臂序列执行失败: {result.get('message')}")
            return False

    except Exception as e:
        print(f"执行机械臂序列异常: {e}")
        return False

def test_simple_sequence():
    print("\n=== 测试简单机械臂动作序列 ===")

    simple_sequence = [
        {"type": "joint", "joint": 6, "angle": 90, "speed": 50},
        {"type": "joint", "joint": 5, "angle": 0, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 130, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 0, "speed": 50},
        {"type": "joint", "joint": 1, "angle": 130, "speed": 50}
    ]

    try:
        response = requests.post(
            'http://localhost:5000/api/robot_arm/execute_sequence',
            json={
                'actions': simple_sequence,
                'protocol': 'http'
            },
            headers={'Content-Type': 'application/json'}
        )

        result = response.json()
        print(f"简单序列执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result.get('success', False)

    except Exception as e:
        print(f"简单序列测试异常: {e}")
        return False

def main():
    print("🤖 机械臂控制功能测试")
    print("=" * 50)

    status_ok = test_robot_arm_status()

    if not status_ok:
        print("⚠️  机械臂状态获取失败，继续测试其他功能...")

    simple_ok = test_simple_sequence()

    if simple_ok:
        print("\n等待2秒后继续测试完整序列...")
        time.sleep(2)
        full_ok = test_execute_sequence()
    else:
        print("⚠️  简单序列测试失败，跳过完整序列测试")
        full_ok = False

    print("\n" + "=" * 50)
    print("📊 测试结果总结:")
    print(f"机械臂状态: {'✅ 正常' if status_ok else '❌ 异常'}")
    print(f"简单序列: {'✅ 成功' if simple_ok else '❌ 失败'}")
    print(f"完整序列: {'✅ 成功' if full_ok else '❌ 失败'}")

    if status_ok and simple_ok and full_ok:
        print("\n🎉 所有测试通过！机械臂控制功能正常。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查后端服务和硬件连接。")
        return 1

if __name__ == "__main__":
    sys.exit(main())