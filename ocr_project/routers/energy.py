import base64
import numpy as np
import cv2
from fastapi import APIRouter, UploadFile, File
from services.energy_detection import detect_energy_label
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["能耗识别服务"])

@router.post("/detect")
async def detect_energy(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return {
                "code": 400,
                "message": "无法读取图像",
                "data": None
            }

        result = detect_energy_label(img)
        
        # 添加调试日志
        logger.info(f"检测结果: energy_level={result['energy_level']}, detected_color_count={result.get('detected_color_count', 0)}")
        logger.info(f"当前颜色: {result.get('current_color', 'None')}")
        logger.info(f"等级颜色: {result.get('level_colors', [])}")

        _, buffer = cv2.imencode('.jpg', result["debug_image"])
        debug_image_base64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode()

        return {
            "code": 100,  # 成功状态码
            "message": "识别成功",
            "data": {
                "energy_level": result["energy_level"],
                "debug_image": debug_image_base64,
                "level_colors": result["level_colors"],
                "current_color": result["current_color"],
                "detected_color_count": result.get("detected_color_count", 0),
                "algorithm_version": result.get("algorithm_version", "unknown")
            }
        }

    except Exception as e:
        logger.error(f"处理图像时出错: {str(e)}")
        return {
            "code": 500,
            "message": f"处理图像时出错: {str(e)}",
            "data": None
        }