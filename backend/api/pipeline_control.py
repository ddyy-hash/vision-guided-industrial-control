#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from flask import Blueprint, jsonify, request
from flask_socketio import emit
from datetime import datetime

logger = logging.getLogger(__name__)

pipeline_bp = Blueprint('pipeline', __name__, url_prefix='/api/pipeline')

pipeline_controller = None
socketio = None

def initialize_pipeline_routes(app, socketio_instance, belt_controller, robot_arm, tracking_service, energy_detection_service):
    global pipeline_controller, socketio

    socketio = socketio_instance

    from services.pipeline_controller import get_pipeline_controller
    pipeline_controller = get_pipeline_controller(socketio_instance)

    if pipeline_controller is None:
        logger.error("流水线控制器初始化失败")
        return

    @socketio_instance.on('start_pipeline')
    def handle_start_pipeline():
        try:
            logger.info("收到WebSocket启动流水线请求")

            if not pipeline_controller:
                logger.error("流水线控制器未初始化")
                emit('pipeline_status', {
                    'status': 'error',
                    'message': '流水线控制器未初始化',
                    'timestamp': datetime.now().isoformat()
                })
                return

            result = pipeline_controller.start_pipeline()
            logger.info(f"流水线启动结果: {result}")

            if result.get("success", False):
                emit('pipeline_status', {
                    'status': 'running',
                    'message': result.get("message", "流水线控制已启动"),
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("流水线控制已通过WebSocket启动")
            else:
                emit('pipeline_status', {
                    'status': 'error',
                    'message': result.get("message", "流水线启动失败"),
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"启动流水线错误: {e}", exc_info=True)
            try:
                emit('pipeline_status', {
                    'status': 'error',
                    'message': f'启动失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as emit_error:
                logger.error(f"WebSocket消息发送失败: {emit_error}")

    @socketio_instance.on('stop_pipeline')
    def handle_stop_pipeline():
        try:
            logger.info("收到WebSocket停止流水线请求")

            if not pipeline_controller:
                logger.error("流水线控制器未初始化")
                emit('pipeline_status', {
                    'status': 'error',
                    'message': '流水线控制器未初始化',
                    'timestamp': datetime.now().isoformat()
                })
                return

            result = pipeline_controller.stop_pipeline()
            logger.info(f"流水线停止结果: {result}")

            if result.get("success", False):
                emit('pipeline_status', {
                    'status': 'stopped',
                    'message': result.get("message", "流水线控制已停止"),
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("流水线控制已通过WebSocket停止")
            else:
                emit('pipeline_status', {
                    'status': 'error',
                    'message': result.get("message", "流水线停止失败"),
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"停止流水线错误: {e}", exc_info=True)
            try:
                emit('pipeline_status', {
                    'status': 'error',
                    'message': f'停止失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as emit_error:
                logger.error(f"WebSocket消息发送失败: {emit_error}")

    @socketio_instance.on('pause_pipeline')
    def handle_pause_pipeline():
        try:
            logger.info("收到WebSocket暂停流水线请求")

            if not pipeline_controller:
                logger.error("流水线控制器未初始化")
                emit('pipeline_status', {
                    'status': 'error',
                    'message': '流水线控制器未初始化',
                    'timestamp': datetime.now().isoformat()
                })
                return

            result = pipeline_controller.pause_pipeline()
            logger.info(f"流水线暂停结果: {result}")

            if result.get("success", False):
                emit('pipeline_status', {
                    'status': 'paused',
                    'message': result.get("message", "流水线控制已暂停"),
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("流水线控制已通过WebSocket暂停")
            else:
                emit('pipeline_status', {
                    'status': 'error',
                    'message': result.get("message", "流水线暂停失败"),
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"暂停流水线错误: {e}", exc_info=True)
            try:
                emit('pipeline_status', {
                    'status': 'error',
                    'message': f'暂停失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as emit_error:
                logger.error(f"WebSocket消息发送失败: {emit_error}")

    @socketio_instance.on('resume_pipeline')
    def handle_resume_pipeline():
        try:
            logger.info("收到WebSocket恢复流水线请求")

            if not pipeline_controller:
                logger.error("流水线控制器未初始化")
                emit('pipeline_status', {
                    'status': 'error',
                    'message': '流水线控制器未初始化',
                    'timestamp': datetime.now().isoformat()
                })
                return

            result = pipeline_controller.resume_pipeline()
            logger.info(f"流水线恢复结果: {result}")

            if result.get("success", False):
                emit('pipeline_status', {
                    'status': 'running',
                    'message': result.get("message", "流水线控制已恢复"),
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("流水线控制已通过WebSocket恢复")
            else:
                emit('pipeline_status', {
                    'status': 'error',
                    'message': result.get("message", "流水线恢复失败"),
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"恢复流水线错误: {e}", exc_info=True)
            try:
                emit('pipeline_status', {
                    'status': 'error',
                    'message': f'恢复失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as emit_error:
                logger.error(f"WebSocket消息发送失败: {emit_error}")

    @socketio_instance.on('get_pipeline_status')
    def handle_get_pipeline_status():
        try:
            logger.info("收到WebSocket获取流水线状态请求")

            if not pipeline_controller:
                logger.error("流水线控制器未初始化")
                emit('pipeline_error', {
                    'message': '流水线控制器未初始化',
                    'timestamp': datetime.now().isoformat()
                })
                return

            status = pipeline_controller.get_status()
            logger.info(f"获取流水线状态成功: {status.get('pipeline_state', {}).get('status', 'unknown')}")

            emit('pipeline_status_update', {
                'status': status,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"获取流水线状态错误: {e}", exc_info=True)
            try:
                emit('pipeline_error', {
                    'message': f'获取状态失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as emit_error:
                logger.error(f"WebSocket消息发送失败: {emit_error}")

    @socketio_instance.on('update_pipeline_config')
    def handle_update_pipeline_config(data):
        try:
            logger.info("收到WebSocket更新流水线配置请求")
            config = data.get('config', {})

            if not pipeline_controller:
                logger.error("流水线控制器未初始化")
                emit('pipeline_config_updated', {
                    'success': False,
                    'message': '流水线控制器未初始化',
                    'timestamp': datetime.now().isoformat()
                })
                return

            result = pipeline_controller.update_config(config)
            logger.info(f"流水线配置更新结果: {result}")

            if result.get("success", False):
                emit('pipeline_config_updated', {
                    'success': True,
                    'message': result.get("message", "配置已更新"),
                    'timestamp': datetime.now().isoformat()
                })
                logger.info("流水线配置已通过WebSocket更新")
            else:
                emit('pipeline_config_updated', {
                    'success': False,
                    'message': result.get("message", "配置更新失败"),
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"更新流水线配置错误: {e}", exc_info=True)
            try:
                emit('pipeline_config_updated', {
                    'success': False,
                    'message': f'配置更新失败: {str(e)}',
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as emit_error:
                logger.error(f"WebSocket消息发送失败: {emit_error}")

    @pipeline_bp.route('/status', methods=['GET'])
    def get_pipeline_status():
        try:
            if not pipeline_controller:
                return jsonify({
                    'success': False,
                    'message': '流水线控制器未初始化'
                }), 500

            status = pipeline_controller.get_status()
            return jsonify({
                'success': True,
                'data': status
            })
        except Exception as e:
            logger.error(f"获取流水线状态错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @pipeline_bp.route('/control', methods=['POST'])
    def control_pipeline():
        try:
            data = request.json
            action = data.get('action')

            if not pipeline_controller:
                return jsonify({
                    'success': False,
                    'message': '流水线控制器未初始化'
                }), 500

            result = None
            if action == 'start':
                result = pipeline_controller.start_pipeline()
            elif action == 'stop':
                result = pipeline_controller.stop_pipeline()
            elif action == 'pause':
                result = pipeline_controller.pause_pipeline()
            elif action == 'resume':
                result = pipeline_controller.resume_pipeline()
            else:
                return jsonify({
                    'success': False,
                    'message': '未知的操作类型'
                }), 400

            return jsonify(result)

        except Exception as e:
            logger.error(f"控制流水线错误: {e}")
            error_msg = str(e)
            if 'datetime' in error_msg.lower():
                error_msg = "内部服务器错误"
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500

    @pipeline_bp.route('/config', methods=['GET', 'POST'])
    def pipeline_config():
        try:
            if not pipeline_controller:
                return jsonify({
                    'success': False,
                    'message': '流水线控制器未初始化'
                }), 500

            if request.method == 'GET':
                status = pipeline_controller.get_status()
                return jsonify({
                    'success': True,
                    'data': status.get('config', {})
                })

            elif request.method == 'POST':
                data = request.json
                config = data.get('config', {})

                result = pipeline_controller.update_config(config)

                return jsonify(result)

        except Exception as e:
            logger.error(f"配置操作错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @pipeline_bp.route('/history', methods=['GET'])
    def get_processing_history():
        try:
            if not pipeline_controller:
                return jsonify({
                    'success': False,
                    'message': '流水线控制器未初始化'
                }), 500

            limit = request.args.get('limit', 10, type=int)
            history = pipeline_controller.get_processing_history(limit)

            return jsonify({
                'success': True,
                'data': {
                    'history': history,
                    'count': len(history)
                }
            })
        except Exception as e:
            logger.error(f"获取处理历史错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @pipeline_bp.route('/stats', methods=['GET'])
    def get_pipeline_statistics():
        try:
            if not pipeline_controller:
                return jsonify({
                    'success': False,
                    'message': '流水线控制器未初始化'
                }), 500

            status = pipeline_controller.get_status()
            pipeline_state = status.get('pipeline_state', {})

            stats = {
                'total_processed': pipeline_state.get('processed_count', 0),
                'error_count': pipeline_state.get('error_count', 0),
                'current_state': pipeline_state.get('status', 'unknown'),
                'current_step': pipeline_state.get('current_step', 'unknown'),
                'progress': pipeline_state.get('progress', 0),
                'uptime': status.get('uptime', 0),
                'ocr_history_count': status.get('ocr_history_count', 0),
                'processing_history_count': status.get('processing_history_count', 0)
            }

            return jsonify({
                'success': True,
                'data': stats
            })
        except Exception as e:
            logger.error(f"获取统计信息错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @pipeline_bp.route('/reset', methods=['POST'])
    def reset_pipeline():
        try:
            if not pipeline_controller:
                return jsonify({
                    'success': False,
                    'message': '流水线控制器未初始化'
                }), 500

            pipeline_controller.stop_pipeline()

            result = pipeline_controller.reset_statistics()

            return jsonify(result)
        except Exception as e:
            logger.error(f"重置流水线错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @pipeline_bp.route('/arm_sequence', methods=['POST'])
    def set_arm_sequence():
        try:
            if not pipeline_controller:
                return jsonify({
                    'success': False,
                    'message': '流水线控制器未初始化'
                }), 500

            data = request.json
            sequence = data.get('sequence', [])

            if not sequence or not isinstance(sequence, list):
                return jsonify({
                    'success': False,
                    'message': '无效的序列格式'
                }), 400

            for i, step in enumerate(sequence):
                if not isinstance(step, dict):
                    return jsonify({
                        'success': False,
                        'message': f'步骤 {i+1} 格式错误：必须是对象'
                    }), 400

                if 'name' not in step or 'duration' not in step or 'actions' not in step:
                    return jsonify({
                        'success': False,
                        'message': f'步骤 {i+1} 缺少必要字段：name, duration, actions'
                    }), 400

                if not isinstance(step['actions'], list) or len(step['actions']) == 0:
                    return jsonify({
                        'success': False,
                        'message': f'步骤 {i+1} 的actions必须是包含动作的数组'
                    }), 400

                for j, action in enumerate(step['actions']):
                    if not isinstance(action, dict):
                        return jsonify({
                            'success': False,
                            'message': f'步骤 {i+1} 的动作 {j+1} 格式错误'
                        }), 400

                    if ('jointId' not in action and 'joint' not in action) or 'angle' not in action:
                        return jsonify({
                            'success': False,
                            'message': f'步骤 {i+1} 的动作 {j+1} 缺少必要字段：jointId/joint 和 angle'
                        }), 400

            result = pipeline_controller.update_config({
                'custom_arm_sequence': sequence
            })

            if result.get('success', False):
                logger.info(f"自定义机械臂序列已设置，共 {len(sequence)} 个步骤")
                return jsonify({
                    'success': True,
                    'message': f'自定义机械臂序列已设置，共 {len(sequence)} 个步骤',
                    'sequence_count': len(sequence)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('message', '设置序列失败')
                })

        except Exception as e:
            logger.error(f"设置自定义机械臂序列错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @pipeline_bp.route('/arm_sequence', methods=['GET'])
    def get_arm_sequence():
        try:
            if not pipeline_controller:
                return jsonify({
                    'success': False,
                    'message': '流水线控制器未初始化'
                }), 500

            status = pipeline_controller.get_status()
            custom_sequence = status.get('config', {}).get('custom_arm_sequence', [])

            return jsonify({
                'success': True,
                'data': {
                    'sequence': custom_sequence,
                    'count': len(custom_sequence)
                }
            })

        except Exception as e:
            logger.error(f"获取自定义机械臂序列错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @pipeline_bp.route('/health', methods=['GET'])
    def pipeline_health():
        try:
            if not pipeline_controller:
                return jsonify({
                    'success': False,
                    'message': '流水线控制器未初始化'
                }), 500

            status = pipeline_controller.get_status()

            health_status = {
                'status': 'healthy',
                'system_running': status.get('pipeline_state', {}).get('status') == 'running',
                'current_state': status.get('pipeline_state', {}).get('status', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }

            return jsonify({
                'success': True,
                'data': health_status
            })
        except Exception as e:
            logger.error(f"健康检查错误: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    app.register_blueprint(pipeline_bp)

    logger.info("流水线控制路由初始化完成")

__all__ = ['pipeline_bp', 'initialize_pipeline_routes']
