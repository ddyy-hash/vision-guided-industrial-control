import time
import sys
import os

import numpy as np
from flask import Blueprint, jsonify, request, Response
from flask_socketio import emit
import logging
import json
from datetime import datetime
import cv2
import base64

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from services.tracking_service import get_tracking_service

logger = logging.getLogger(__name__)

tracking_bp = Blueprint('tracking', __name__, url_prefix='/api/tracking')

tracking_service = get_tracking_service()

def create_error_frame(error_message: str) -> bytes:
    try:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        cv2.putText(frame, "视频流错误", (50, 200),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        cv2.putText(frame, error_message, (50, 250),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, "正在尝试重新连接...", (50, 300),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])

        return buffer.tobytes()
    except Exception as e:
        logger.error(f"创建错误帧失败: {e}")
        return b''

def initialize_tracking_routes(socketio):

    @socketio.on('start_tracking')
    def handle_start_tracking(data):
        try:
            logger.info("收到WebSocket开始追踪请求")
            camera_source = data.get('camera_source', 0)

            if isinstance(camera_source, dict):
                logger.warning(f"摄像头源参数类型错误: {type(camera_source)}，使用默认值0")
                camera_source = 0
            elif not isinstance(camera_source, (int, float)):
                logger.warning(f"摄像头源参数类型异常: {type(camera_source)}，转换为整数")
                try:
                    camera_source = int(camera_source)
                except (ValueError, TypeError):
                    camera_source = 0

            camera_source = int(camera_source)

            success = tracking_service.start_tracking(camera_source)
            logger.info(f"追踪启动结果: {success}")

            if success:
                emit('tracking_status', {
                    'status': 'running',
                    'message': '追踪已启动',
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("追踪启动成功，WebSocket事件将开始发送")
            else:
                emit('tracking_status', {
                    'status': 'error',
                    'message': '追踪启动失败',
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"启动追踪错误: {e}", exc_info=True)
            try:
                emit('tracking_status', {
                    'status': 'error',
                    'message': f'启动追踪失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as emit_error:
                logger.error(f"WebSocket消息发送失败: {emit_error}")

    @socketio.on('stop_tracking')
    def handle_stop_tracking():
        try:
            logger.info("收到WebSocket停止追踪请求")
            tracking_service.stop_tracking()
            logger.info("追踪已停止")

            emit('tracking_status', {
                'status': 'stopped',
                'message': '追踪已停止',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"停止追踪错误: {e}", exc_info=True)
            try:
                emit('tracking_status', {
                    'status': 'error',
                    'message': f'停止追踪失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as emit_error:
                logger.error(f"WebSocket消息发送失败: {emit_error}")

    @socketio.on('get_tracking_objects')
    def handle_get_tracking_objects():
        try:
            logger.debug("收到WebSocket获取追踪物体请求")
            objects = tracking_service.get_current_objects()
            stats = tracking_service.get_tracking_stats()

            emit('tracking_objects', {
                'objects': objects,
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            })
            logger.debug(f"返回追踪物体数据: {len(objects)} 个物体")
        except Exception as e:
            logger.error(f"获取追踪物体错误: {e}", exc_info=True)
            try:
                emit('tracking_error', {
                    'message': f'获取追踪物体失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as emit_error:
                logger.error(f"WebSocket消息发送失败: {emit_error}")

    def on_object_detected(obj_data):
        try:
            logger.debug(f"物体检测回调: {obj_data.get('track_id', 'unknown')}")
            socketio.emit('object_detected', {
                'object': obj_data,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"物体检测回调错误: {e}")

    def on_object_lost(obj_data):
        try:
            logger.debug(f"物体丢失回调: {obj_data.get('track_id', 'unknown')}")
            socketio.emit('object_lost', {
                'object': obj_data,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"物体丢失回调错误: {e}")

    def on_frame_processed(frame_data):
        try:
            socketio.emit('frame_processed', {
                'frame_data': frame_data,
                'timestamp': datetime.now().isoformat()
            })

            frame_id = frame_data.get('frame_id', 0)

            current_time = time.time()

            frame_base64 = tracking_service.get_smooth_frame_base64()
            if frame_base64:
                if hasattr(on_frame_processed, 'last_frame_sent_time'):
                    time_since_last_frame = current_time - on_frame_processed.last_frame_sent_time
                    target_interval = 1.0 / 30

                    if time_since_last_frame >= target_interval:
                        try:
                            socketio.emit('video_frame', {
                                'frame': frame_base64,
                                'timestamp': datetime.now().isoformat(),
                                'frame_id': frame_id,
                                'detection_mode': frame_data.get('detection_mode', 'unknown'),
                                'frame_type': 'smooth',
                                'fps': tracking_service.fps
                            })
                            on_frame_processed.last_frame_sent_time = current_time
                        except Exception as emit_error:
                            logger.error(f"视频帧WebSocket发送失败: {emit_error}")
                    else:
                        logger.debug(f"跳过视频帧发送 - 时间间隔不足: {time_since_last_frame:.3f}s")
                else:
                    on_frame_processed.last_frame_sent_time = current_time
                    try:
                        socketio.emit('video_frame', {
                            'frame': frame_base64,
                            'timestamp': datetime.now().isoformat(),
                            'frame_id': frame_id,
                            'detection_mode': frame_data.get('detection_mode', 'unknown'),
                            'frame_type': 'smooth',
                            'fps': tracking_service.fps
                        })
                    except Exception as emit_error:
                        logger.error(f"视频帧WebSocket发送失败: {emit_error}")
            else:
                logger.warning(f"帧ID {frame_id} 无平滑视频帧数据")

        except Exception as e:
            logger.error(f"帧处理回调错误: {e}")

    tracking_service.add_callback('on_object_detected', on_object_detected)
    tracking_service.add_callback('on_object_lost', on_object_lost)
    tracking_service.add_callback('on_frame_processed', on_frame_processed)

    @tracking_bp.route('/status', methods=['GET'])
    def get_tracking_status():
        try:
            stats = tracking_service.get_tracking_stats()
            return jsonify({
                'success': True,
                'data': stats
            })
        except Exception as e:
            logger.error(f"获取追踪状态错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/objects', methods=['GET'])
    def get_current_objects():
        try:
            objects = tracking_service.get_current_objects()
            return jsonify({
                'success': True,
                'data': {
                    'objects': objects,
                    'count': len(objects)
                }
            })
        except Exception as e:
            logger.error(f"获取追踪物体错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/control', methods=['POST'])
    def control_tracking():
        try:
            data = request.json
            action = data.get('action')

            if action == 'start':
                camera_source = data.get('camera_source', 0)
                if isinstance(camera_source, dict):
                    logger.warning(f"HTTP路由摄像头源参数类型错误: {type(camera_source)}，使用默认值0")
                    camera_source = 0
                elif not isinstance(camera_source, (int, float)):
                    logger.warning(f"HTTP路由摄像头源参数类型异常: {type(camera_source)}，转换为整数")
                    try:
                        camera_source = int(camera_source)
                    except (ValueError, TypeError):
                        camera_source = 0

                camera_source = int(camera_source)

                success = tracking_service.start_tracking(camera_source)
                return jsonify({
                    'success': success,
                    'message': '追踪已启动' if success else '追踪启动失败'
                })

            elif action == 'stop':
                tracking_service.stop_tracking()
                return jsonify({
                    'success': True,
                    'message': '追踪已停止'
                })

            elif action == 'configure':
                config = data.get('config', {})
                return jsonify({
                    'success': True,
                    'message': '配置已更新'
                })

            else:
                return jsonify({
                    'success': False,
                    'message': '未知的操作类型'
                }), 400

        except Exception as e:
            logger.error(f"控制追踪错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/calibration', methods=['POST'])
    def upload_calibration():
        try:
            data = request.json
            calib_params = data.get('calibration_params')

            if not calib_params:
                return jsonify({
                    'success': False,
                    'message': '缺少标定参数'
                }), 400

            calib_file = 'calibration_params.json'
            with open(calib_file, 'w') as f:
                json.dump(calib_params, f)

            success = tracking_service.load_camera_calibration(calib_file)

            return jsonify({
                'success': success,
                'message': '标定参数已加载' if success else '标定参数加载失败'
            })

        except Exception as e:
            logger.error(f"上传标定参数错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/stats', methods=['GET'])
    def get_tracking_statistics():
        try:
            stats = tracking_service.get_tracking_stats()

            extended_stats = {
                **stats,
                'uptime': time.time() - stats.get('start_time', time.time()),
                'total_objects_detected': len(tracking_service.tracked_objects),
                'average_processing_time': stats.get('processing_time', 0),
                'detection_rate': stats.get('detection_count', 0) / max(stats.get('frame_count', 1), 1)
            }

            return jsonify({
                'success': True,
                'data': extended_stats
            })
        except Exception as e:
            logger.error(f"获取统计信息错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/ocr-status', methods=['GET'])
    def get_ocr_status():
        try:
            ocr_status = tracking_service.get_all_ocr_status()
            return jsonify({
                'success': True,
                'data': ocr_status
            })
        except Exception as e:
            logger.error(f"获取OCR状态错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/data', methods=['GET'])
    def get_tracking_data():
        try:
            objects = tracking_service.get_current_objects()
            stats = tracking_service.get_tracking_stats()

            data = {
                'objects': objects,
                'frame_id': stats.get('frame_count', 0),
                'timestamp': datetime.now().isoformat(),
                'detections': stats.get('detection_count', 0),
                'fps': stats.get('fps', 0),
                'processing_time': stats.get('processing_time', 0)
            }

            return jsonify({
                'success': True,
                'data': data
            })
        except Exception as e:
            logger.error(f"获取追踪数据错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/reset', methods=['POST'])
    def reset_tracking():
        global tracking_service
        try:
            tracking_service.stop_tracking()

            from services.tracking_service import initialize_tracking_service
            tracking_service = initialize_tracking_service()

            return jsonify({
                'success': True,
                'message': '追踪系统已重置'
            })
        except Exception as e:
            logger.error(f"重置追踪系统错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/frame', methods=['GET'])
    def get_current_frame():
        try:
            frame_type = request.args.get('type', 'raw')

            if frame_type == 'detections':
                frame_data = tracking_service.get_frame_with_detections()
            else:
                frame_data = tracking_service.get_smooth_frame_base64()

            if frame_data:
                return jsonify({
                    'success': True,
                    'data': {
                        'frame': frame_data,
                        'timestamp': datetime.now().isoformat(),
                        'type': frame_type,
                        'smooth': True
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '暂无视频帧数据'
                }), 404

        except Exception as e:
            logger.error(f"获取视频帧失败: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/belt/status', methods=['GET'])
    def get_belt_status():
        try:
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
                avg_velocity = np.mean([abs(obj['velocity']) for obj in tracking_service.tracked_objects.values()])
                belt_status['average_speed'] = round(avg_velocity, 3)

            return jsonify({
                'success': True,
                'data': belt_status
            })

        except Exception as e:
            logger.error(f"获取传送带状态错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @tracking_bp.route('/video_feed')
    def video_feed():
        def generate_frames():
            frame_count = 0
            while True:
                try:
                    frame_data = tracking_service.get_smooth_frame_base64()

                    if frame_data:
                        if frame_data.startswith('data:image/jpeg;base64,'):
                            frame_base64 = frame_data.split(',')[1]
                        else:
                            frame_base64 = frame_data

                        import base64
                        frame_bytes = base64.b64decode(frame_base64)

                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                        frame_count += 1

                        time.sleep(0.033)
                    else:
                        logger.warning("视频流：无可用帧数据")
                        time.sleep(0.1)

                except Exception as e:
                    logger.error(f"视频流生成错误: {e}")
                    error_frame = create_error_frame(f"视频流错误: {str(e)}")
                    if error_frame:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
                    time.sleep(1.0)

        return Response(generate_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')

    @tracking_bp.route('/video_feed_with_detections')
    def video_feed_with_detections():
        def generate_frames_with_detections():
            frame_count = 0
            while True:
                try:
                    frame_data = tracking_service.get_frame_with_detections()

                    if frame_data:
                        if frame_data.startswith('data:image/jpeg;base64,'):
                            frame_base64 = frame_data.split(',')[1]
                        else:
                            frame_base64 = frame_data

                        import base64
                        frame_bytes = base64.b64decode(frame_base64)

                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                        frame_count += 1

                        time.sleep(0.04)
                    else:
                        logger.warning("视频流：无可用帧数据")
                        time.sleep(0.1)

                except Exception as e:
                    logger.error(f"带检测框视频流生成错误: {e}")
                    error_frame = create_error_frame(f"检测视频流错误: {str(e)}")
                    if error_frame:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + error_frame + b'\r\n')
                    time.sleep(1.0)

        return Response(generate_frames_with_detections(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')

__all__ = ['tracking_bp', 'initialize_tracking_routes', 'create_error_frame']