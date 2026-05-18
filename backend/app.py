import os
from fix_omp_conflict import apply_omp_fixes
apply_omp_fixes()

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import threading
import time
import logging
import math
from datetime import datetime
from utils.json_encoder import CustomJSONEncoder

from api.belt import BeltController
from api.robot_arm import RobotArm
from api.tracking import tracking_bp, initialize_tracking_routes
from api.energy_ocr import energy_ocr_bp
from api.realtime_energy import realtime_energy_bp, initialize_realtime_energy_routes
from api.device_management import device_management_bp, initialize_device_management_routes
from api.pipeline_control import pipeline_bp, initialize_pipeline_routes
from services.device_connection_manager import get_device_connection_manager
from services.device_scanner import DeviceType

OCR_SERVICE_AVAILABLE = True

app = Flask(__name__)
app.json_encoder = CustomJSONEncoder

device_manager = get_device_connection_manager()

CORS(app, resources={
    r"/api/*": {
        "origins": "http://localhost:3000",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

socketio = SocketIO(app,
                   cors_allowed_origins="http://localhost:3000",
                   async_mode='threading')


def initialize_device_connections():
    try:
        device_manager.initialize_connections()
        connection_status = device_manager.get_connection_status()
        logger.info(f"设备连接状态: {connection_status}")

        arm_controller = device_manager.get_robot_arm()
        if arm_controller and arm_controller.connected:
            logger.info("机械臂已连接，正在初始化到安全位置...")
            arm_controller.home_position()
            logger.info("机械臂已初始化到安全位置")
        else:
            logger.warning("机械臂未连接，跳过初始化")

    except Exception as e:
        logger.error(f"设备连接初始化失败: {e}")

def delayed_device_init():
    time.sleep(3)
    initialize_device_connections()

device_init_thread = threading.Thread(target=delayed_device_init)
device_init_thread.daemon = True
device_init_thread.start()

initialize_tracking_routes(socketio)
initialize_realtime_energy_routes(socketio)
initialize_device_management_routes(socketio)

app.register_blueprint(tracking_bp)
app.register_blueprint(energy_ocr_bp)
app.register_blueprint(realtime_energy_bp)
app.register_blueprint(device_management_bp)

initialize_pipeline_routes(app, socketio, None, None, None, None)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

arm_lock = threading.Lock()

hardware_status = {
    "robot_arm": {
        "position": {"x": 0, "y": 0, "z": 0},
        "joints": [0, 0, 0, 0],
        "temperature": 35.2,
        "status": "idle"
    },
    "conveyor_belt": {
        "speed": 0,
        "direction": "forward",
        "load": 0,
        "status": "running"
    },
    "vision_system": {
        "detection_rate": 92.5,
        "last_result": "pass",
        "status": "active"
    }
}

@socketio.on('connect')
def handle_connect():
    try:
        logger.info('客户端已连接')
        socketio.emit('arm_status', hardware_status["robot_arm"])
        socketio.emit('connection_status', {'status': 'connected'})
        logger.info('已发送初始状态给客户端')
    except Exception as e:
        logger.error(f"处理客户端连接错误: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    try:
        logger.info('客户端已断开连接')
    except Exception as e:
        logger.error(f"处理客户端断开连接错误: {e}")

@socketio.on('get_arm_position')
def handle_get_position():
    try:
        logger.debug('收到获取机械臂位置请求')
        socketio.emit('arm_position', hardware_status["robot_arm"]["position"])
    except Exception as e:
        logger.error(f"处理获取机械臂位置错误: {e}")
        socketio.emit('arm_error', {'message': f'获取位置失败: {str(e)}'})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(hardware_status)

@app.route('/api/robot_arm', methods=['POST'])
def control_robot_arm():
    data = request.json
    try:
        command = data['command']
        params = data.get('params', {})

        logger.info(f"执行机械臂命令: {command}, 参数: {params}")

        arm_controller = device_manager.get_robot_arm()
        if not arm_controller or not arm_controller.connected:
            return jsonify({"success": False, "message": "机械臂未连接"}), 400

        with arm_lock:
            hardware_status["robot_arm"]["status"] = "busy"
            socketio.emit('arm_status', hardware_status["robot_arm"])

            if command == "move_to_position":
                required = ['x', 'y', 'z']
                if not all(k in params for k in required):
                    return jsonify({"success": False, "message": "缺少位置参数"}), 400

                if params['z'] < 0:
                    return jsonify({"success": False, "message": "高度不能低于0"}), 400

                distance = math.sqrt(params['x']**2 + params['y']**2)
                if distance > 20:
                    return jsonify({"success": False, "message": "超出工作范围"}), 400

                success = arm_controller.move_to_position(
                    params['x'], params['y'], params['z'],
                    pitch=params.get('pitch', 0),
                    movetime=params.get('movetime', 1000)
                )
                if not success:
                    hardware_status["robot_arm"]["status"] = "error"
                    return jsonify({"success": False, "message": "无法到达该位置"}), 400

                hardware_status["robot_arm"]["position"] = {
                    "x": params['x'],
                    "y": params['y'],
                    "z": params['z']
                }

            elif command == "set_joint_angle":
                if 'joint' not in params or 'angle' not in params:
                    return jsonify({"success": False, "message": "缺少关节参数"}), 400

                joint_id = params['joint']
                if joint_id not in [1, 3, 4, 5, 6]:
                    return jsonify({"success": False, "message": "无效关节ID"}), 40

                angle = params['angle']
                valid_ranges = {
                    1: (0, 180),
                    3: (-90, 90),
                    4: (-90, 90),
                    5: (0, 180),
                    6: (0, 180)
                }

                min_angle, max_angle = valid_ranges.get(joint_id, (0, 180))

                if not min_angle <= angle <= max_angle:
                    return jsonify({
                        "success": False,
                        "message": f"关节{joint_id}角度超出范围({min_angle}-{max_angle})"
                    }), 400

                success = arm_controller.set_joint_angle(
                    joint_id, angle,
                    movetime=params.get('movetime', 500)
                )
                if not success:
                    hardware_status["robot_arm"]["status"] = "error"
                    return jsonify({"success": False, "message": "关节控制失败"}), 400

                hardware_status["robot_arm"]["joints"][joint_id-3] = angle

            elif command == "run_sequence":
                if 'actions' not in params:
                    return jsonify({"success": False, "message": "缺少动作序列"}), 400

                for action in params['actions']:
                    if action.get('type') == 'multi_joint':
                        movetime = action.get('movetime', 500)
                        servos = []

                        for servo_action in action.get('servos', []):
                            joint_id = servo_action.get('jointId')
                            angle = servo_action.get('angle')

                            if joint_id not in [1, 3, 4, 5, 6]:
                                logger.error(f"无效关节ID: {joint_id}")
                                continue

                            valid_ranges = {
                                1: (0, 180),
                                3: (-90, 90),
                                4: (-90, 90),
                                5: (0, 180),
                                6: (0, 180)
                            }

                            min_angle, max_angle = valid_ranges.get(joint_id, (0, 180))
                            if not min_angle <= angle <= max_angle:
                                logger.error(f"关节{joint_id}角度超出范围({min_angle}-{max_angle})")
                                continue

                            pulse = arm_controller.angle_to_pulse(joint_id, angle)
                            servos.append((joint_id, pulse))

                        if servos:
                            arm_controller.move_servos(movetime, servos)

                            for joint_id, pulse in servos:
                                angle = arm_controller.pulse_to_angle(joint_id, pulse)
                                if joint_id in [3, 4, 5, 6]:
                                    index = joint_id - 3
                                    hardware_status["robot_arm"]["joints"][index] = angle
                                elif joint_id == 1:
                                    hardware_status["robot_arm"]["gripper"] = angle

                            socketio.emit('sequence_progress', {
                                'progress': 0,
                                'description': f"执行: {action.get('name', '多舵机动作')}"
                            })
                            time.sleep(movetime / 1000.0)

                hardware_status["robot_arm"]["position"] = arm_controller.current_position

            else:
                return jsonify({"success": False, "message": "未知命令类型"}), 400

            hardware_status["robot_arm"]["status"] = "idle"
            socketio.emit('arm_status', hardware_status["robot_arm"])
            socketio.emit('arm_position', hardware_status["robot_arm"]["position"])
            return jsonify({"success": True, "message": "命令执行成功"})

    except Exception as e:
        logger.error(f"控制错误: {str(e)}")
        hardware_status["robot_arm"]["status"] = "error"
        socketio.emit('arm_status', hardware_status["robot_arm"])
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/robot_arm/status', methods=['GET'])
def get_robot_arm_status():
    try:
        arm_controller = device_manager.get_robot_arm()
        if not arm_controller:
            return jsonify({
                "connected": False,
                "position": [0, 0, 0, 0, 0],
                "temperature": 32.5,
                "busy": False
            })

        status = arm_controller.get_status()
        return jsonify({
            "connected": status["connected"],
            "position": [
                status.get("current_position", [0, 0, 0])[0],
                status.get("current_position", [0, 0, 0])[1],
                status.get("current_position", [0, 0, 0])[2],
                status.get("current_pitch", 0),
                130 if status.get("is_gripper_open", False) else 0
            ],
            "temperature": hardware_status["robot_arm"]["temperature"],
            "busy": hardware_status["robot_arm"]["status"] == "busy"
        })
    except Exception as e:
        logger.error(f"获取机械臂状态错误: {str(e)}")
        return jsonify({
            "connected": False,
            "position": [0, 0, 0, 0, 0],
            "temperature": 32.5,
            "busy": False
        })

@app.route('/api/robot_arm/execute_sequence', methods=['POST'])
def execute_robot_arm_sequence():
    try:
        data = request.json
        actions = data.get('actions', [])
        protocol = data.get('protocol', 'http')

        if not actions:
            return jsonify({"success": False, "message": "缺少动作序列"}), 400

        arm_controller = device_manager.get_robot_arm()
        if not arm_controller or not arm_controller.connected:
            return jsonify({"success": False, "message": "机械臂未连接"}), 400

        logger.info(f"执行机械臂动作序列，共 {len(actions)} 个动作，协议: {protocol}")

        with arm_lock:
            hardware_status["robot_arm"]["status"] = "busy"
            socketio.emit('arm_status', hardware_status["robot_arm"])

            try:
                sequence = []
                for i, action in enumerate(actions):
                    action_type = action.get('type', 'joint')

                    if action_type == 'joint':
                        joint_id = action.get('joint')
                        angle = action.get('angle')
                        speed = action.get('speed', 50)
                        movetime = int((100 - speed) * 20)

                        if joint_id is None or angle is None:
                            logger.warning(f"动作 {i+1} 参数不完整，跳过")
                            continue

                        if joint_id not in [1, 3, 4, 5, 6]:
                            logger.warning(f"无效关节ID: {joint_id}，跳过")
                            continue

                        valid_ranges = {
                            1: (0, 180),
                            3: (-90, 90),
                            4: (-90, 90),
                            5: (0, 180),
                            6: (0, 180)
                        }

                        min_angle, max_angle = valid_ranges.get(joint_id, (0, 180))
                        if not min_angle <= angle <= max_angle:
                            logger.warning(f"关节{joint_id}角度 {angle} 超出范围({min_angle}-{max_angle})，修正为边界值")
                            angle = max(min_angle, min(max_angle, angle))

                        sequence.append({
                            'type': 'joint',
                            'joint_id': joint_id,
                            'angle': angle,
                            'movetime': movetime,
                            'name': f'关节{joint_id} -> {angle}°'
                        })

                    elif action_type == 'gripper':
                        action_param = action.get('action')
                        movetime = action.get('movetime', 500)

                        if action_param == 'open':
                            sequence.append({
                                'type': 'gripper',
                                'params': {'action': 'open'},
                                'movetime': movetime,
                                'name': '打开夹爪'
                            })
                        elif action_param == 'close':
                            sequence.append({
                                'type': 'gripper',
                                'params': {'action': 'close'},
                                'movetime': movetime,
                                'name': '关闭夹爪'
                            })
                        else:
                            logger.warning(f"未知夹爪动作: {action_param}")

                    elif action_type == 'move':
                        x = action.get('x')
                        y = action.get('y')
                        z = action.get('z')
                        pitch = action.get('pitch', 0)
                        movetime = action.get('movetime', 1000)

                        if x is not None and y is not None and z is not None:
                            sequence.append({
                                'type': 'move',
                                'params': {'x': x, 'y': y, 'z': z, 'pitch': pitch},
                                'movetime': movetime,
                                'name': f'移动到 ({x}, {y}, {z})'
                            })
                        else:
                            logger.warning(f"坐标移动参数不完整")
                    else:
                        logger.warning(f"未知动作类型: {action_type}")

                if not sequence:
                    return jsonify({"success": False, "message": "没有有效的动作"}), 400

                def progress_callback(progress, description):
                    socketio.emit('sequence_progress', {
                        'progress': progress,
                        'description': description
                    })
                    logger.info(f"序列进度: {progress}% - {description}")

                success = arm_controller.run_sequence(sequence, progress_callback)

                if success:
                    hardware_status["robot_arm"]["status"] = "idle"
                    hardware_status["robot_arm"]["position"] = {
                        "x": arm_controller.current_position[0],
                        "y": arm_controller.current_position[1],
                        "z": arm_controller.current_position[2]
                    }

                    socketio.emit('arm_status', hardware_status["robot_arm"])
                    socketio.emit('arm_position', hardware_status["robot_arm"]["position"])

                    return jsonify({
                        "success": True,
                        "message": "机械臂动作序列执行成功"
                    })
                else:
                    hardware_status["robot_arm"]["status"] = "error"
                    socketio.emit('arm_status', hardware_status["robot_arm"])
                    return jsonify({
                        "success": False,
                        "message": "机械臂动作序列执行失败"
                    }), 500

            except Exception as e:
                logger.error(f"执行机械臂序列时出错: {str(e)}")
                hardware_status["robot_arm"]["status"] = "error"
                socketio.emit('arm_status', hardware_status["robot_arm"])
                return jsonify({
                    "success": False,
                    "message": f"执行序列出错: {str(e)}"
                }), 500
            finally:
                hardware_status["robot_arm"]["status"] = "idle"
                socketio.emit('arm_status', hardware_status["robot_arm"])

    except Exception as e:
        logger.error(f"机械臂序列控制错误: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/robot_arm/stop', methods=['POST'])
def emergency_stop():
    try:
        arm_controller = device_manager.get_robot_arm()
        if not arm_controller or not arm_controller.connected:
            return jsonify({"success": False, "message": "机械臂未连接"}), 400

        with arm_lock:
            logger.warning("执行紧急停止")
            arm_controller.home_position()
            hardware_status["robot_arm"]["status"] = "emergency_stop"
            hardware_status["robot_arm"]["position"] = {"x": 0, "y": 0, "z": 10}
            socketio.emit('arm_status', hardware_status["robot_arm"])
            socketio.emit('arm_position', hardware_status["robot_arm"]["position"])
            return jsonify({"success": True, "message": "紧急停止执行"})
    except Exception as e:
        logger.error(f"紧急停止错误: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/belt', methods=['POST'])
def control_conveyor():
    data = request.json
    speed_mps = data.get('speed')  # m/s (0-0.8)
    direction = data.get('direction', 'forward')

    if speed_mps is None or not 0 <= speed_mps <= 0.8:
        return jsonify({"success": False, "message": "速度需为0-0.8 m/s的数值"}), 400
    if direction not in ["forward", "backward"]:
        return jsonify({"success": False, "message": "方向需为forward或backward"}), 400

    belt_controller = device_manager.get_belt_controller()
    if not belt_controller:
        return jsonify({"success": False, "message": "传送带控制器未初始化"}), 400

    try:
        result = belt_controller.set_speed_mps(speed_mps, direction)
        if result.get("success", False):
            speed_percent = int((speed_mps / 0.8) * 100)
            hardware_status["conveyor_belt"]["speed"] = speed_percent
            hardware_status["conveyor_belt"]["direction"] = direction
            return jsonify({"success": True, "message": "指令执行成功"})
        else:
            return jsonify({"success": False, "message": result.get("response", "硬件控制失败")}), 500
    except Exception as e:
        logger.error(f"传送带控制异常: {str(e)}")
        return jsonify({"success": False, "message": f"控制异常: {str(e)}"}), 500

@app.route('/api/conveyor/control', methods=['POST'])
def control_conveyor_mps():
    data = request.json
    try:
        speed_mps = data.get('speed', 0.0)  # m/s
        direction = data.get('direction', 'forward')
        action = data.get('action')  # start, stop, emergency_stop, set_speed

        logger.info(f"传送带控制请求: speed={speed_mps} m/s, direction={direction}, action={action}")

        belt_controller = device_manager.get_belt_controller()
        if not belt_controller:
            return jsonify({
                "success": False,
                "message": "传送带控制器未初始化",
                "status": "error"
            }), 400

        max_speed_mps = 0.8
        if speed_mps < 0 or speed_mps > max_speed_mps:
            return jsonify({
                "success": False,
                "message": f"速度必须在 0 - {max_speed_mps} m/s 范围内",
                "status": "error"
            }), 400

        if action == "start":
            result = belt_controller.set_speed_mps(speed_mps, direction)
            if result.get("success", False):
                speed_percent = int((speed_mps / max_speed_mps) * 100)
                hardware_status["conveyor_belt"]["speed"] = speed_percent
                hardware_status["conveyor_belt"]["direction"] = direction
                hardware_status["conveyor_belt"]["status"] = "running"
                logger.info(f"传送带启动成功: {speed_mps:.3f} m/s, 方向: {direction}")
                return jsonify({
                    "success": True,
                    "message": f"传送带已启动，速度: {speed_mps:.3f} m/s",
                    "status": "running"
                })
            else:
                logger.error(f"传送带启动失败: {result.get('response', '未知错误')}")
                return jsonify({
                    "success": False,
                    "message": result.get("response", "启动失败"),
                    "status": "error"
                }), 500

        elif action == "stop":
            current_direction = direction
            if current_direction not in ["forward", "backward"]:
                current_direction = hardware_status["conveyor_belt"]["direction"]

            result = belt_controller.set_speed_mps(0, current_direction)
            hardware_status["conveyor_belt"]["speed"] = 0
            hardware_status["conveyor_belt"]["direction"] = current_direction
            hardware_status["conveyor_belt"]["status"] = "stopped"
            logger.info(f"传送带已停止，方向保持: {current_direction}")
            return jsonify({
                "success": True,
                "message": "传送带已停止",
                "status": "stopped"
            })

        elif action == "emergency_stop":
            current_direction = direction
            if current_direction not in ["forward", "backward"]:
                current_direction = hardware_status["conveyor_belt"]["direction"]

            result = belt_controller.set_speed_mps(0, current_direction)
            hardware_status["conveyor_belt"]["speed"] = 0
            hardware_status["conveyor_belt"]["direction"] = current_direction
            hardware_status["conveyor_belt"]["status"] = "emergency_stop"
            logger.warning(f"传送带已紧急停止，方向保持: {current_direction}")
            return jsonify({
                "success": True,
                "message": "传送带已紧急停止",
                "status": "emergency_stop"
            })

        elif action == "set_speed":
            result = belt_controller.set_speed_mps(speed_mps, direction)
            if result.get("success", False):
                speed_percent = int((speed_mps / max_speed_mps) * 100)
                hardware_status["conveyor_belt"]["speed"] = speed_percent
                hardware_status["conveyor_belt"]["direction"] = direction
                hardware_status["conveyor_belt"]["status"] = "running" if speed_mps > 0 else "stopped"
                logger.info(f"传送带速度设置成功: {speed_mps:.3f} m/s, 方向: {direction}")
                return jsonify({
                    "success": True,
                    "message": f"传送带速度已设置为 {speed_mps:.3f} m/s",
                    "status": hardware_status["conveyor_belt"]["status"]
                })
            else:
                logger.error(f"传送带速度设置失败: {result.get('response', '未知错误')}")
                return jsonify({
                    "success": False,
                    "message": result.get("response", "速度设置失败"),
                    "status": "error"
                }), 500

        else:
            logger.error(f"未知动作类型: {action}")
            return jsonify({
                "success": False,
                "message": f"未知动作类型: {action}",
                "status": "error"
            }), 400

    except Exception as e:
        logger.error(f"传送带控制错误: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"控制错误: {str(e)}",
            "status": "error"
        }), 500

@app.route('/api/conveyor/status', methods=['GET'])
def get_conveyor_status():
    try:
        belt_controller = device_manager.get_belt_controller()
        if not belt_controller:
            return jsonify({
                "success": False,
                "message": "传送带控制器未初始化",
                "data": None
            }), 400

        hardware_status_info = belt_controller.get_status()

        speed_mps = hardware_status["conveyor_belt"]["speed"] * 0.8 / 100

        status_data = {
            "isRunning": hardware_status["conveyor_belt"]["speed"] > 0,
            "currentSpeed": speed_mps,
            "targetSpeed": speed_mps,
            "actualSpeed": speed_mps,
            "direction": hardware_status["conveyor_belt"]["direction"],
            "status": hardware_status["conveyor_belt"]["status"],
            "deviceType": "standard",
            "speedRange": {
                "min": 0.001,
                "max": 0.8
            },
            "temperature": 25 + (hardware_status["conveyor_belt"]["load"] * 0.1),
            "load": hardware_status["conveyor_belt"]["load"],
            "healthScore": max(100 - (hardware_status["conveyor_belt"]["load"] * 0.5), 70),
            "hardwareInfo": hardware_status_info,
            "lastUpdate": datetime.now().isoformat(),
            "timestamp": datetime.now().isoformat()
        }

        return jsonify({
            "success": True,
            "data": status_data
        })

    except Exception as e:
        logger.error(f"获取传送带状态错误: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
            "data": None
        }), 500

@app.route('/api/conveyor/reset', methods=['POST'])
def reset_conveyor():
    try:
        belt_controller = device_manager.get_belt_controller()
        if not belt_controller:
            return jsonify({"success": False, "message": "传送带控制器未初始化"}), 400

        result = belt_controller.set_speed_percent(0, "forward")
        hardware_status["conveyor_belt"]["speed"] = 0
        hardware_status["conveyor_belt"]["direction"] = "forward"
        hardware_status["conveyor_belt"]["status"] = "stopped"

        return jsonify({
            "success": True,
            "message": "传送带系统已复位"
        })

    except Exception as e:
        logger.error(f"传送带复位错误: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"复位错误: {str(e)}"
        }), 500

@app.route('/api/belt/status', methods=['GET'])
def get_belt_status_compat():
    try:
        from services.tracking_service import get_tracking_service
        tracking_service = get_tracking_service()
        stats = tracking_service.get_tracking_stats()

        belt_status = {
            'belt_running': stats.get('is_running', False),
            'objects_on_belt': stats.get('active_tracks', 0),
            'average_speed': 0.0,
            'total_processed': stats.get('frame_count', 0),
            'current_fps': stats.get('fps', 0),
            'detection_mode': stats.get('detection_mode', {}).get('current_mode', 'unknown'),
            'gpu_available': stats.get('gpu_info', {}).get('gpu_available', False),
            'timestamp': datetime.now().isoformat()
        }

        if tracking_service.tracked_objects:
            import numpy as np
            avg_velocity = np.mean([abs(obj['velocity']) for obj in tracking_service.tracked_objects.values()])
            belt_status['average_speed'] = round(avg_velocity, 3)

        return jsonify({
            'success': True,
            'data': belt_status
        })

    except Exception as e:
        logger.error(f"获取传送带状态兼容路由错误: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def update_sensor_data():
    while True:
        try:
            time.sleep(2)
            hardware_status["robot_arm"]["temperature"] = round(35 + (5 * (time.time() % 10) / 10), 1)

            hardware_status["conveyor_belt"]["load"] = round(10 + (8 * (time.time() % 10) / 10), 1)

            if time.time() % 7 < 0.5:
                hardware_status["vision_system"]["last_result"] = "fail"
            else:
                hardware_status["vision_system"]["last_result"] = "pass"

            try:
                socketio.emit('status_update', hardware_status)
                logger.debug("传感器数据已推送")
            except Exception as emit_error:
                logger.warning(f"WebSocket数据推送失败: {emit_error}")

        except Exception as e:
            logger.error(f"传感器数据更新错误: {e}")
            time.sleep(1)

@app.route('/api/devices', methods=['GET'])
def get_devices():
    try:
        connection_status = device_manager.get_connection_status()

        devices = []

        if "conveyor_belt" in connection_status["connected_devices"]:
            belt_status = connection_status["connected_devices"]["conveyor_belt"]
            devices.append({
                "device_id": "conveyor_belt_1",
                "name": "传送带系统",
                "device_type": "conveyor_belt",
                "model": "标准传送带",
                "manufacturer": "工业控制平台",
                "serial_number": "CONV001",
                "firmware_version": "1.0.0",
                "connection_type": "serial",
                "connection_info": belt_status["port"],
                "status": "connected" if belt_status["connected"] else "disconnected",
                "is_online": belt_status["connected"],
                "pairing_status": "paired",
                "health_score": 95,
                "port": belt_status["port"],
                "auto_connect": True,
                "last_connection_time": datetime.now().isoformat(),
                "connection_count": 1,
                "description": "工业传送带控制系统",
                "tags": ["conveyor", "belt", "industrial"],
                "capabilities": ["speed_control", "direction_control", "emergency_stop"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            })

        if "robot_arm" in connection_status["connected_devices"]:
            arm_status = connection_status["connected_devices"]["robot_arm"]
            devices.append({
                "device_id": "robot_arm_1",
                "name": "机械臂系统",
                "device_type": "robot_arm",
                "model": "标准机械臂",
                "manufacturer": "工业控制平台",
                "serial_number": "ROB001",
                "firmware_version": "1.0.0",
                "connection_type": "serial",
                "connection_info": arm_status["port"],
                "status": "connected" if arm_status["connected"] else "disconnected",
                "is_online": arm_status["connected"],
                "pairing_status": "paired",
                "health_score": 90,
                "port": arm_status["port"],
                "auto_connect": True,
                "last_connection_time": datetime.now().isoformat(),
                "connection_count": 1,
                "description": "工业机械臂控制系统",
                "tags": ["robot", "arm", "industrial"],
                "capabilities": ["position_control", "joint_control", "sequence_control"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            })

        return jsonify({
            "success": True,
            "data": devices
        })

    except Exception as e:
        logger.error(f"获取设备列表失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取设备列表失败: {str(e)}",
            "data": []
        }), 500

@app.route('/api/devices/status/realtime/batch', methods=['POST'])
def get_devices_real_time_data_batch():
    try:
        data = request.json
        device_ids = data.get('device_ids', [])

        real_time_data = []

        for device_id in device_ids:
            if device_id == "conveyor_belt_1":
                real_time_data.append({
                    "device_id": device_id,
                    "temperature": 35.2,
                    "cpu_usage": 25.5,
                    "signal_strength": "强",
                    "last_connection_time": datetime.now().isoformat(),
                    "health_score": 95
                })
            elif device_id == "robot_arm_1":
                real_time_data.append({
                    "device_id": device_id,
                    "temperature": 42.1,
                    "cpu_usage": 18.7,
                    "signal_strength": "强",
                    "last_connection_time": datetime.now().isoformat(),
                    "health_score": 90
                })

        return jsonify({
            "success": True,
            "data": real_time_data
        })

    except Exception as e:
        logger.error(f"获取设备实时数据失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取设备实时数据失败: {str(e)}",
            "data": []
        }), 500

if __name__ == '__main__':
    logger.info("工业控制平台后端服务启动，OCR服务将在需要时通过HTTP调用")

    sensor_thread = threading.Thread(target=update_sensor_data)
    sensor_thread.daemon = True
    sensor_thread.start()

    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
