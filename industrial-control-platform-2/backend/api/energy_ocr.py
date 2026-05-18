import requests
import base64
import io
import logging
from flask import Blueprint, request, jsonify
from PIL import Image
import cv2
import numpy as np

logger = logging.getLogger(__name__)

energy_ocr_bp = Blueprint('energy_ocr', __name__, url_prefix='/api')

OCR_SERVICE_URL = "http://localhost:8000"

@energy_ocr_bp.route('/ocr/image', methods=['POST'])
def ocr_image():
    try:
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "未提供文件",
                "code": 400
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "未选择文件",
                "code": 400
            }), 400

        files = {'file': (file.filename, file.stream, file.content_type)}
        data = {
            'enable_yolo': request.form.get('enable_yolo', 'true') == 'true',
            'target_class_id': int(request.form.get('target_class_id', 0)),
            'max_repair_time': float(request.form.get('max_repair_time', 2.0))
        }

        response = requests.post(
            f"{OCR_SERVICE_URL}/api/ocr/image",
            files=files,
            data=data,
            timeout=30
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "success": False,
                "message": f"OCR服务错误: {response.status_code}",
                "code": response.status_code
            }), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"OCR服务连接失败: {e}")
        return jsonify({
            "success": False,
            "message": f"OCR服务连接失败: {str(e)}",
            "code": 503
        }), 503
    except Exception as e:
        logger.error(f"OCR处理异常: {e}")
        return jsonify({
            "success": False,
            "message": f"处理异常: {str(e)}",
            "code": 500
        }), 500

@energy_ocr_bp.route('/energy/detect', methods=['POST'])
def energy_detect():
    try:
        if 'file' not in request.files:
            return jsonify({
                "code": 400,
                "message": "未提供文件",
                "data": None
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "code": 400,
                "message": "未选择文件",
                "data": None
            }), 400

        files = {'file': (file.filename, file.stream, file.content_type)}

        response = requests.post(
            f"{OCR_SERVICE_URL}/api/energy/detect",
            files=files,
            timeout=30
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "code": response.status_code,
                "message": f"能效检测服务错误: {response.status_code}",
                "data": None
            }), response.status_code

    except requests.exceptions.RequestException as e:
        logger.error(f"能效检测服务连接失败: {e}")
        return jsonify({
            "code": 503,
            "message": f"能效检测服务连接失败: {str(e)}",
            "data": None
        }), 503
    except Exception as e:
        logger.error(f"能效检测处理异常: {e}")
        return jsonify({
            "code": 500,
            "message": f"处理异常: {str(e)}",
            "data": None
        }), 500

@energy_ocr_bp.route('/ocr/health', methods=['GET'])
def ocr_health():
    try:
        response = requests.get(f"{OCR_SERVICE_URL}/api/ocr/health", timeout=5)
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "status": "connected",
                "ocr_service": response.json()
            })
        else:
            return jsonify({
                "success": False,
                "status": "error",
                "message": f"OCR服务响应异常: {response.status_code}"
            }), 503
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "status": "disconnected",
            "message": f"OCR服务连接失败: {str(e)}"
        }), 503

@energy_ocr_bp.route('/camera/capture', methods=['POST'])
def camera_capture():
    try:
        from services.tracking_service import get_tracking_service

        tracking_service = get_tracking_service()

        frame_base64 = tracking_service.get_smooth_frame_base64()
        if not frame_base64:
            return jsonify({
                "success": False,
                "message": "无法获取摄像头画面",
                "code": 404
            }), 404

        image_data = base64.b64decode(frame_base64.split(',')[1])

        files = {'file': ('camera_capture.jpg', image_data, 'image/jpeg')}

        ocr_response = requests.post(
            f"{OCR_SERVICE_URL}/api/ocr/image",
            files=files,
            data={'enable_yolo': True, 'target_class_id': 0},
            timeout=30
        )

        energy_response = requests.post(
            f"{OCR_SERVICE_URL}/api/energy/detect",
            files={'file': ('camera_capture.jpg', image_data, 'image/jpeg')},
            timeout=30
        )

        result = {
            "success": True,
            "camera_frame": frame_base64,
            "ocr_result": ocr_response.json() if ocr_response.status_code == 200 else None,
            "energy_result": energy_response.json() if energy_response.status_code == 200 else None
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"摄像头捕获识别失败: {e}")
        return jsonify({
            "success": False,
            "message": f"摄像头捕获识别失败: {str(e)}",
            "code": 500
        }), 500

@energy_ocr_bp.route('/energy/combined', methods=['POST'])
def energy_combined():
    try:
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "未提供文件",
                "code": 400
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "未选择文件",
                "code": 400
            }), 400

        file_content = file.read()

        files = {'file': (file.filename, file_content, file.content_type)}

        ocr_response = requests.post(
            f"{OCR_SERVICE_URL}/api/ocr/image",
            files=files,
            data={'enable_yolo': True, 'target_class_id': 0},
            timeout=30
        )

        energy_response = requests.post(
            f"{OCR_SERVICE_URL}/api/energy/detect",
            files={'file': (file.filename, file_content, file.content_type)},
            timeout=30
        )

        ocr_data = ocr_response.json() if ocr_response.status_code == 200 else None
        energy_data = energy_response.json() if energy_response.status_code == 200 else None

        energy_level = None
        if energy_data and energy_data.get('code') == 100:
            energy_level = energy_data.get('data', {}).get('energy_level')

        ocr_text = ""
        if ocr_data and ocr_data.get('result', {}).get('code') == 100:
            ocr_result = ocr_data['result']
            if 'data' in ocr_result:
                for item in ocr_result['data']:
                    ocr_text += item.get('text', '') + '\n'

        return jsonify({
            "success": True,
            "energy_level": energy_level,
            "ocr_text": ocr_text.strip(),
            "ocr_result": ocr_data,
            "energy_result": energy_data,
            "combined_timestamp": __import__('datetime').datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"综合识别失败: {e}")
        return jsonify({
            "success": False,
            "message": f"综合识别失败: {str(e)}",
            "code": 500
        }), 500

__all__ = ['energy_ocr_bp']