import time
import logging
from flask import Blueprint, jsonify, request
from flask_socketio import emit
from datetime import datetime

from services.energy_detection_service import get_energy_detection_service

logger = logging.getLogger(__name__)

realtime_energy_bp = Blueprint('realtime_energy', __name__, url_prefix='/api/realtime')

energy_service = get_energy_detection_service()

def initialize_realtime_energy_routes(socketio):

    @socketio.on('start_realtime_energy_detection')
    def handle_start_realtime_energy_detection(data):
        try:
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

            success = energy_service.start_detection(camera_source)

            if success:
                emit('realtime_energy_status', {
                    'status': 'running',
                    'message': '实时能效检测已启动',
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("实时能效检测启动成功，WebSocket事件将开始发送")
            else:
                emit('realtime_energy_status', {
                    'status': 'error',
                    'message': '实时能效检测启动失败',
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"启动实时能效检测错误: {e}")
            emit('realtime_energy_status', {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })

    @socketio.on('stop_realtime_energy_detection')
    def handle_stop_realtime_energy_detection():
        try:
            energy_service.stop_detection()
            emit('realtime_energy_status', {
                'status': 'stopped',
                'message': '实时能效检测已停止',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"停止实时能效检测错误: {e}")
            emit('realtime_energy_status', {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })

    @socketio.on('get_realtime_energy_status')
    def handle_get_realtime_energy_status():
        try:
            status = energy_service.get_service_status()
            latest_result = energy_service.get_latest_result()

            emit('realtime_energy_data', {
                'status': status,
                'latest_result': latest_result,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"获取实时能效检测状态错误: {e}")
            emit('realtime_energy_error', {
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })

    def on_frame_captured(frame_data):
        try:
            socketio.emit('realtime_frame_captured', {
                'frame_data': frame_data,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"帧捕获回调错误: {e}")

    def on_energy_detected(detection_result):
        try:
            socketio.emit('realtime_energy_detected', {
                'detection_result': detection_result,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"能效检测回调错误: {e}")

    def on_detection_error(error_data):
        try:
            socketio.emit('realtime_energy_error', {
                'error': error_data,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"检测错误回调错误: {e}")

    energy_service.add_callback('on_frame_captured', on_frame_captured)
    energy_service.add_callback('on_energy_detected', on_energy_detected)
    energy_service.add_callback('on_detection_error', on_detection_error)

    @realtime_energy_bp.route('/status', methods=['GET'])
    def get_realtime_energy_status():
        try:
            status = energy_service.get_service_status()
            latest_result = energy_service.get_latest_result()

            return jsonify({
                'success': True,
                'data': {
                    'status': status,
                    'latest_result': latest_result
                }
            })
        except Exception as e:
            logger.error(f"获取实时能效检测状态错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @realtime_energy_bp.route('/control', methods=['POST'])
    def control_realtime_energy_detection():
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

                success = energy_service.start_detection(camera_source)
                return jsonify({
                    'success': success,
                    'message': '实时能效检测已启动' if success else '实时能效检测启动失败'
                })

            elif action == 'stop':
                energy_service.stop_detection()
                return jsonify({
                    'success': True,
                    'message': '实时能效检测已停止'
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
            logger.error(f"控制实时能效检测错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @realtime_energy_bp.route('/results', methods=['GET'])
    def get_realtime_energy_results():
        try:
            limit = request.args.get('limit', 5, type=int)
            results = energy_service.get_detection_results(limit)

            return jsonify({
                'success': True,
                'data': {
                    'results': results,
                    'count': len(results)
                }
            })
        except Exception as e:
            logger.error(f"获取实时能效检测结果错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @realtime_energy_bp.route('/frame', methods=['GET'])
    def get_realtime_frame():
        try:
            frame_base64 = energy_service.get_current_frame()

            if frame_base64:
                return jsonify({
                    'success': True,
                    'data': {
                        'frame': frame_base64,
                        'timestamp': datetime.now().isoformat()
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '暂无视频帧数据'
                }), 404

        except Exception as e:
            logger.error(f"获取实时视频帧错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @realtime_energy_bp.route('/latest', methods=['GET'])
    def get_latest_energy_result():
        try:
            latest_result = energy_service.get_latest_result()

            if latest_result:
                return jsonify({
                    'success': True,
                    'data': latest_result
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '暂无检测结果'
                }), 404

        except Exception as e:
            logger.error(f"获取最新能效检测结果错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @realtime_energy_bp.route('/stats', methods=['GET'])
    def get_realtime_energy_statistics():
        try:
            status = energy_service.get_service_status()
            latest_result = energy_service.get_latest_result()
            recent_results = energy_service.get_detection_results(10)

            total_detections = len(recent_results)
            successful_detections = sum(1 for r in recent_results if r.get('success', False))
            success_rate = (successful_detections / total_detections * 100) if total_detections > 0 else 0

            energy_levels = {}
            for result in recent_results:
                if result.get('success'):
                    level = result.get('energy_level', '未知')
                    energy_levels[level] = energy_levels.get(level, 0) + 1

            statistics = {
                'total_detections': total_detections,
                'successful_detections': successful_detections,
                'success_rate': round(success_rate, 2),
                'energy_level_distribution': energy_levels,
                'service_status': status,
                'latest_energy_level': latest_result.get('energy_level', '未知') if latest_result else '未知',
                'average_confidence': round(
                    sum(r.get('confidence', 0) for r in recent_results if r.get('success')) /
                    max(successful_detections, 1), 2
                )
            }

            return jsonify({
                'success': True,
                'data': statistics
            })

        except Exception as e:
            logger.error(f"获取实时能效检测统计信息错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @realtime_energy_bp.route('/reset', methods=['POST'])
    def reset_realtime_energy_detection():
        global energy_service
        try:
            energy_service.stop_detection()

            from services.energy_detection_service import initialize_energy_detection_service
            energy_service = initialize_energy_detection_service()

            return jsonify({
                'success': True,
                'message': '实时能效检测系统已重置'
            })
        except Exception as e:
            logger.error(f"重置实时能效检测系统错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

__all__ = ['realtime_energy_bp', 'initialize_realtime_energy_routes']