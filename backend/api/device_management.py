from flask import Blueprint, jsonify, request
import logging
from datetime import datetime
from services.device_manager import get_device_manager, ConnectionEvent
from services.device_storage import get_device_storage
from services.device_scanner import DeviceStatus, DeviceType
from services.device_pairing import get_device_pairing_manager, PairingStatus

logger = logging.getLogger(__name__)

device_management_bp = Blueprint('device_management', __name__)

device_manager = get_device_manager()
device_storage = get_device_storage()
device_pairing_manager = get_device_pairing_manager()

@device_management_bp.route('/api/devices', methods=['GET'])
def get_devices():
    try:
        devices = device_manager.get_available_devices()
        return jsonify({
            'success': True,
            'data': devices
        })
    except Exception as e:
        logger.error(f"获取设备列表失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取设备列表失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/connected', methods=['GET'])
def get_connected_devices():
    try:
        connected_devices = device_manager.get_connected_devices()
        return jsonify({
            'success': True,
            'data': connected_devices
        })
    except Exception as e:
        logger.error(f"获取已连接设备列表失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取已连接设备列表失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>/connect', methods=['POST'])
def connect_device(device_id):
    try:
        success = device_manager.connect_device(device_id)
        if success:
            return jsonify({
                'success': True,
                'message': '设备连接成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': '设备连接失败'
            }), 400
    except Exception as e:
        logger.error(f"连接设备失败: {e}")
        return jsonify({
            'success': False,
            'message': f'设备连接失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>/disconnect', methods=['POST'])
def disconnect_device(device_id):
    try:
        device_manager.disconnect_device(device_id)
        return jsonify({
            'success': True,
            'message': '设备已断开连接'
        })
    except Exception as e:
        logger.error(f"断开设备连接失败: {e}")
        return jsonify({
            'success': False,
            'message': f'断开设备连接失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/scan', methods=['POST'])
def scan_devices():
    try:
        device_manager.manual_scan()
        return jsonify({
            'success': True,
            'message': '设备扫描完成'
        })
    except Exception as e:
        logger.error(f"设备扫描失败: {e}")
        return jsonify({
            'success': False,
            'message': f'设备扫描失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/scan/start', methods=['POST'])
def start_auto_scan():
    try:
        device_manager.start_auto_scan()
        return jsonify({
            'success': True,
            'message': '自动扫描已启动'
        })
    except Exception as e:
        logger.error(f"启动自动扫描失败: {e}")
        return jsonify({
            'success': False,
            'message': f'启动自动扫描失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/scan/stop', methods=['POST'])
def stop_auto_scan():
    try:
        device_manager.stop_auto_scan()
        return jsonify({
            'success': True,
            'message': '自动扫描已停止'
        })
    except Exception as e:
        logger.error(f"停止自动扫描失败: {e}")
        return jsonify({
            'success': False,
            'message': f'停止自动扫描失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>', methods=['GET'])
def get_device_details(device_id):
    try:
        device_info = device_storage.get_device(device_id)
        if not device_info:
            return jsonify({
                'success': False,
                'message': '设备不存在'
            }), 404

        device_status = device_manager.get_device_status(device_id)

        connection_history = device_storage.get_connection_history(device_id)

        device_config = device_storage.get_device_config(device_id)

        response_data = {
            'device_info': device_info.to_dict() if device_info else None,
            'device_status': device_status,
            'connection_history': connection_history,
            'device_config': device_config
        }

        return jsonify({
            'success': True,
            'data': response_data
        })
    except Exception as e:
        logger.error(f"获取设备详情失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取设备详情失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>/history', methods=['GET'])
def get_device_history(device_id):
    try:
        limit = request.args.get('limit', 50, type=int)
        history = device_storage.get_connection_history(device_id, limit)
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        logger.error(f"获取设备连接历史失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取设备连接历史失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>/config', methods=['GET'])
def get_device_config(device_id):
    try:
        config = device_storage.get_device_config(device_id)
        return jsonify({
            'success': True,
            'data': config
        })
    except Exception as e:
        logger.error(f"获取设备配置失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取设备配置失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>/config', methods=['POST'])
def save_device_config(device_id):
    try:
        config_data = request.json
        if not config_data:
            return jsonify({
                'success': False,
                'message': '配置数据不能为空'
            }), 400

        success = device_storage.save_device_config(device_id, config_data)
        if success:
            return jsonify({
                'success': True,
                'message': '设备配置已保存'
            })
        else:
            return jsonify({
                'success': False,
                'message': '保存设备配置失败'
            }), 400
    except Exception as e:
        logger.error(f"保存设备配置失败: {e}")
        return jsonify({
            'success': False,
            'message': f'保存设备配置失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/statistics', methods=['GET'])
def get_statistics():
    try:
        statistics = device_manager.get_device_statistics()
        return jsonify({
            'success': True,
            'data': statistics
        })
    except Exception as e:
        logger.error(f"获取设备统计信息失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取设备统计信息失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/cleanup', methods=['POST'])
def cleanup_devices():
    try:
        days = request.json.get('days', 30) if request.json else 30
        cleaned_count = device_manager.cleanup_old_devices(days)
        return jsonify({
            'success': True,
            'message': f'清理了 {cleaned_count} 个旧设备',
            'data': {'cleaned_count': cleaned_count}
        })
    except Exception as e:
        logger.error(f"清理设备失败: {e}")
        return jsonify({
            'success': False,
            'message': f'清理设备失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    try:
        device_manager.disconnect_device(device_id)

        success = device_storage.delete_device(device_id)
        if success:
            return jsonify({
                'success': True,
                'message': '设备已删除'
            })
        else:
            return jsonify({
                'success': False,
                'message': '删除设备失败'
            }), 400
    except Exception as e:
        logger.error(f"删除设备失败: {e}")
        return jsonify({
            'success': False,
            'message': f'删除设备失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>/status', methods=['GET'])
def get_device_status(device_id):
    try:
        status = device_manager.get_device_status(device_id)
        if status:
            return jsonify({
                'success': True,
                'data': status
            })
        else:
            return jsonify({
                'success': False,
                'message': '设备不存在或未连接'
            }), 404
    except Exception as e:
        logger.error(f"获取设备状态失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取设备状态失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>/status/realtime', methods=['GET'])
def get_device_real_time_data(device_id):
    try:
        device_info = device_storage.get_device(device_id)
        if not device_info:
            return jsonify({
                'success': False,
                'message': '设备不存在'
            }), 404

        device_status = device_manager.get_device_status(device_id)

        real_time_data = {
            'device_id': device_id,
            'device_name': device_info.name,
            'device_type': device_info.device_type.value if hasattr(device_info.device_type, 'value') else str(device_info.device_type),
            'status': device_status.get('status', 'unknown') if device_status else 'unknown',
            'temperature': 25 + (hash(device_id) % 30),
            'cpu_usage': 10 + (hash(device_id) % 80),
            'memory_usage': 20 + (hash(device_id) % 60),
            'signal_strength': 70 + (hash(device_id) % 30),
            'last_connection_time': device_info.last_seen,
            'health_score': 85 + (hash(device_id) % 15),
            'timestamp': datetime.now().isoformat()
        }

        return jsonify({
            'success': True,
            'data': real_time_data
        })
    except Exception as e:
        logger.error(f"获取设备实时数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取设备实时数据失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/status/realtime/batch', methods=['POST', 'OPTIONS'])
def get_devices_real_time_data_batch():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.json
        if not data or 'device_ids' not in data:
            return jsonify({
                'success': False,
                'message': '缺少设备ID列表'
            }), 400

        device_ids = data['device_ids']
        if not isinstance(device_ids, list):
            return jsonify({
                'success': False,
                'message': 'device_ids 必须是数组'
            }), 400

        max_devices = 20
        if len(device_ids) > max_devices:
            device_ids = device_ids[:max_devices]
            logger.warning(f"设备数量超过限制，只处理前 {max_devices} 个设备")

        real_time_data_list = []

        device_infos = {}
        for device_id in device_ids:
            try:
                device_info = device_storage.get_device(device_id)
                if device_info:
                    device_infos[device_id] = device_info
            except Exception as e:
                logger.error(f"获取设备 {device_id} 信息失败: {e}")

        for device_id in device_ids:
            try:
                if device_id not in device_infos:
                    continue

                device_info = device_infos[device_id]

                device_status = device_manager.get_device_status(device_id)

                real_time_data = {
                    'device_id': device_id,
                    'device_name': device_info.name,
                    'device_type': device_info.device_type.value if hasattr(device_info.device_type, 'value') else str(device_info.device_type),
                    'status': device_status.get('status', 'unknown') if device_status else 'unknown',
                    'temperature': 25 + (hash(device_id) % 30),
                    'cpu_usage': 10 + (hash(device_id) % 80),
                    'memory_usage': 20 + (hash(device_id) % 60),
                    'signal_strength': 70 + (hash(device_id) % 30),
                    'last_connection_time': device_info.last_seen,
                    'health_score': 85 + (hash(device_id) % 15),
                    'timestamp': datetime.now().isoformat()
                }

                real_time_data_list.append(real_time_data)

            except Exception as e:
                logger.error(f"获取设备 {device_id} 实时数据失败: {e}")

        return jsonify({
            'success': True,
            'data': real_time_data_list
        })

    except Exception as e:
        logger.error(f"批量获取设备实时数据失败: {e}")
        return jsonify({
            'success': False,
            'message': f'批量获取设备实时数据失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/pairing/request', methods=['POST'])
def create_pairing_request():
    try:
        device_id = request.json.get('device_id')
        if not device_id:
            return jsonify({
                'success': False,
                'message': '设备ID不能为空'
            }), 400

        pairing_id = device_pairing_manager.create_pairing_request(device_id)
        if pairing_id:
            return jsonify({
                'success': True,
                'data': {
                    'pairing_id': pairing_id
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '创建设备配对请求失败'
            }), 400

    except Exception as e:
        logger.error(f"创建设备配对请求失败: {e}")
        return jsonify({
            'success': False,
            'message': f'创建设备配对请求失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/pairing/confirm', methods=['POST'])
def confirm_pairing():
    try:
        pairing_id = request.json.get('pairing_id')
        device_type_str = request.json.get('device_type')
        custom_name = request.json.get('custom_name')
        auto_connect = request.json.get('auto_connect', True)

        if not pairing_id or not device_type_str:
            return jsonify({
                'success': False,
                'message': '配对ID和设备类型不能为空'
            }), 400

        try:
            device_type = DeviceType(device_type_str)
            logger.info(f"确认配对 - 设备类型解析成功: {device_type_str} -> {device_type}")
        except ValueError:
            logger.error(f"确认配对 - 无效的设备类型: {device_type_str}")
            return jsonify({
                'success': False,
                'message': f'无效的设备类型: {device_type_str}'
            }), 400

        logger.info(f"确认配对 - 开始配对: pairing_id={pairing_id}, device_type={device_type.value}, custom_name={custom_name}, auto_connect={auto_connect}")

        success = device_pairing_manager.confirm_pairing(
            pairing_id, device_type, custom_name, auto_connect
        )

        if success:
            logger.info(f"确认配对 - 配对成功: {pairing_id}")
            return jsonify({
                'success': True,
                'message': '设备配对成功'
            })
        else:
            logger.error(f"确认配对 - 配对失败: {pairing_id}")
            return jsonify({
                'success': False,
                'message': '设备配对失败'
            }), 400

    except Exception as e:
        logger.error(f"确认设备配对失败: {e}")
        return jsonify({
            'success': False,
            'message': f'确认设备配对失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/pairing/cancel', methods=['POST'])
def cancel_pairing():
    try:
        pairing_id = request.json.get('pairing_id')
        if not pairing_id:
            return jsonify({
                'success': False,
                'message': '配对ID不能为空'
            }), 400

        success = device_pairing_manager.cancel_pairing(pairing_id)
        if success:
            return jsonify({
                'success': True,
                'message': '配对已取消'
            })
        else:
            return jsonify({
                'success': False,
                'message': '取消配对失败'
            }), 400

    except Exception as e:
        logger.error(f"取消设备配对失败: {e}")
        return jsonify({
            'success': False,
            'message': f'取消设备配对失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>/unpair', methods=['POST'])
def unpair_device(device_id):
    try:
        success = device_pairing_manager.unpair_device(device_id)
        if success:
            return jsonify({
                'success': True,
                'message': '设备已取消配对'
            })
        else:
            return jsonify({
                'success': False,
                'message': '取消设备配对失败'
            }), 400

    except Exception as e:
        logger.error(f"取消设备配对失败: {e}")
        return jsonify({
            'success': False,
            'message': f'取消设备配对失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/pairing/history', methods=['GET'])
def get_pairing_history():
    try:
        history = device_pairing_manager.get_pairing_history()
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        logger.error(f"获取配对历史失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取配对历史失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/pairing/paired', methods=['GET'])
def get_paired_devices():
    try:
        paired_devices = device_pairing_manager.get_paired_devices()
        return jsonify({
            'success': True,
            'data': paired_devices
        })
    except Exception as e:
        logger.error(f"获取已配对设备失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取已配对设备失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/pairing/statistics', methods=['GET'])
def get_pairing_statistics():
    try:
        statistics = device_pairing_manager.get_statistics()
        return jsonify({
            'success': True,
            'data': statistics
        })
    except Exception as e:
        logger.error(f"获取配对统计信息失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取配对统计信息失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/pairing/auto-connect/start', methods=['POST'])
def start_auto_connect():
    try:
        device_pairing_manager.start_auto_connect()
        return jsonify({
            'success': True,
            'message': '自动连接已启动'
        })
    except Exception as e:
        logger.error(f"启动自动连接失败: {e}")
        return jsonify({
            'success': False,
            'message': f'启动自动连接失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/pairing/auto-connect/stop', methods=['POST'])
def stop_auto_connect():
    try:
        device_pairing_manager.stop_auto_connect()
        return jsonify({
            'success': True,
            'message': '自动连接已停止'
        })
    except Exception as e:
        logger.error(f"停止自动连接失败: {e}")
        return jsonify({
            'success': False,
            'message': f'停止自动连接失败: {str(e)}'
        }), 500

@device_management_bp.route('/api/devices/<device_id>/pairing', methods=['PUT'])
def update_pairing_settings(device_id):
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': '更新数据不能为空'
            }), 400

        success = device_pairing_manager.update_pairing_record(device_id, **data)
        if success:
            return jsonify({
                'success': True,
                'message': '配对设置已更新'
            })
        else:
            return jsonify({
                'success': False,
                'message': '更新配对设置失败'
            }), 400

    except Exception as e:
        logger.error(f"更新配对设置失败: {e}")
        return jsonify({
            'success': False,
            'message': f'更新配对设置失败: {str(e)}'
        }), 500

def initialize_device_management_routes(socketio):

    def on_device_connected(data):
        socketio.emit('device_connected', data)
        logger.info(f"设备连接: {data.get('name', '未知设备')}")

        device_pairing_manager.record_connection_attempt(data.get('device_id'), True)

    def on_device_disconnected(data):
        socketio.emit('device_disconnected', data)
        logger.info(f"设备断开连接: {data.get('name', '未知设备')}")

    def on_device_error(data):
        socketio.emit('device_error', data)
        logger.error(f"设备错误: {data.get('device_id', '未知设备')} - {data.get('error', '未知错误')}")

        device_pairing_manager.record_connection_attempt(data.get('device_id'), False)

    def on_status_updated(data):
        socketio.emit('device_status_updated', data)

    device_manager.add_event_handler(ConnectionEvent.DEVICE_CONNECTED, on_device_connected)
    device_manager.add_event_handler(ConnectionEvent.DEVICE_DISCONNECTED, on_device_disconnected)
    device_manager.add_event_handler(ConnectionEvent.DEVICE_ERROR, on_device_error)
    device_manager.add_event_handler(ConnectionEvent.STATUS_UPDATED, on_status_updated)

    device_manager.start_auto_scan()

    device_pairing_manager.start_auto_connect()

    logger.info("设备管理路由和WebSocket事件已初始化")