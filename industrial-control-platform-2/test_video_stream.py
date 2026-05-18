#!/usr/bin/env python3

import time
import requests
import json
from datetime import datetime

def test_video_stream():
    print("=== 视频流功能测试 ===")

    print("1. 启动追踪服务...")
    try:
        response = requests.post('http://localhost:5000/api/tracking/control',
                               json={'action': 'start', 'camera_source': 0})
        result = response.json()
        print(f"   启动结果: {result.get('success', False)}")
        print(f"   消息: {result.get('message', '无消息')}")
    except Exception as e:
        print(f"   启动失败: {e}")
        return

    print("   等待追踪服务启动...")
    time.sleep(3)

    print("2. 检查追踪状态...")
    try:
        response = requests.get('http://localhost:5000/api/tracking/status')
        result = response.json()
        if result.get('success'):
            stats = result.get('data', {})
            print(f"   追踪状态: {'运行中' if stats.get('is_running') else '已停止'}")
            print(f"   FPS: {stats.get('fps', 0):.1f}")
            print(f"   活跃追踪: {stats.get('active_tracks', 0)}")
            print(f"   帧计数: {stats.get('frame_count', 0)}")
        else:
            print(f"   获取状态失败: {result.get('message')}")
    except Exception as e:
        print(f"   检查状态失败: {e}")

    print("3. 获取当前视频帧...")
    try:
        response = requests.get('http://localhost:5000/api/tracking/frame',
                               params={'type': 'detections'})
        result = response.json()
        if result.get('success'):
            frame_data = result.get('data', {})
            frame = frame_data.get('frame')
            if frame:
                print(f"   成功获取视频帧")
                print(f"   帧数据长度: {len(frame)} 字符")
                print(f"   帧类型: {frame_data.get('type', 'unknown')}")
                print(f"   时间戳: {frame_data.get('timestamp', 'unknown')}")

                if frame.startswith('data:image/jpeg;base64,'):
                    print("   ✓ 帧数据格式正确")
                else:
                    print("   ⚠ 帧数据格式可能有问题")
            else:
                print("   ⚠ 无视频帧数据")
        else:
            print(f"   获取视频帧失败: {result.get('message')}")
    except Exception as e:
        print(f"   获取视频帧失败: {e}")

    print("4. 检查当前追踪物体...")
    try:
        response = requests.get('http://localhost:5000/api/tracking/objects')
        result = response.json()
        if result.get('success'):
            objects = result.get('data', {}).get('objects', [])
            print(f"   追踪物体数量: {len(objects)}")
            for i, obj in enumerate(objects[:3]):
                print(f"   物体 {i+1}: ID={obj.get('track_id')}, 类别={obj.get('class_name')}, "
                      f"位置=({obj.get('conveyor_x'):.3f}, {obj.get('conveyor_y'):.3f})")
        else:
            print(f"   获取物体失败: {result.get('message')}")
    except Exception as e:
        print(f"   获取物体失败: {e}")

    print("5. 测试MJPEG视频流...")
    try:
        response = requests.get('http://localhost:5000/api/tracking/video_feed_with_detections',
                               stream=True, timeout=10)
        if response.status_code == 200:
            print("   ✓ MJPEG视频流连接成功")
            print(f"   内容类型: {response.headers.get('content-type', 'unknown')}")

            frame_count = 0
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    frame_count += 1
                    if frame_count >= 3:
                        break

            print(f"   成功读取 {frame_count} 个数据块")
        else:
            print(f"   ✗ MJPEG视频流连接失败: {response.status_code}")
    except Exception as e:
        print(f"   MJPEG视频流测试失败: {e}")

    print("\n=== 测试完成 ===")

def test_websocket_video():
    print("\n=== WebSocket视频流测试 ===")

    try:
        import socketio

        sio = socketio.Client()

        @sio.on('connect')
        def on_connect():
            print("✓ WebSocket已连接")
            sio.emit('start_tracking', {'camera_source': 0})

        @sio.on('video_frame')
        def on_video_frame(data):
            frame = data.get('frame')
            if frame:
                print(f"收到视频帧 - 长度: {len(frame)} 字符, 帧ID: {data.get('frame_id')}")
            else:
                print("收到空视频帧")

        @sio.on('frame_processed')
        def on_frame_processed(data):
            frame_data = data.get('frame_data', {})
            print(f"帧处理完成 - 帧ID: {frame_data.get('frame_id')}, 检测: {frame_data.get('detections')}")

        @sio.on('tracking_status')
        def on_tracking_status(data):
            print(f"追踪状态: {data.get('status')}, 消息: {data.get('message')}")

        sio.connect('http://localhost:5000')

        time.sleep(10)

        sio.disconnect()

    except Exception as e:
        print(f"WebSocket测试失败: {e}")

if __name__ == "__main__":
    test_video_stream()

    test_websocket_video()

    print("\n所有测试完成！")