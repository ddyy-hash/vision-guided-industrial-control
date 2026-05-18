from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import time
from ocr_engine.paddle_ocr_wrapper import ocr_engine
from ocr_engine.utils import temp_image_file
from core.config import Config

router = APIRouter()

@router.post("/image")
async def ocr_from_image(file: UploadFile = File(...), enable_yolo: bool = True, target_class_id: int = 0, max_repair_time: float = 2.0):
    """通过图片文件进行OCR"""
    start_time = time.time()

    # 创建 temp 目录（如果不存在）
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True, parents=True)

    # 保存临时文件
    temp_path = temp_dir / file.filename
    with temp_path.open("wb") as buffer:
        buffer.write(await file.read())

    # OCR处理
    result = ocr_engine.process_image(
        str(temp_path.absolute()),
        enable_preprocessing=True,
        enable_yolo=enable_yolo,
        target_class_id=target_class_id,
        max_repair_time=max_repair_time
    )
    temp_path.unlink()  # 删除临时文件

    return {
        "time_cost": round(time.time() - start_time, 2),
        "result": result,
        "yolo_enabled": enable_yolo,
        "target_class_id": target_class_id
    }

@router.post("/base64")
async def ocr_from_base64(data: dict):
    """通过Base64编码进行OCR"""
    start_time = time.time()

    if "image" not in data:
        raise HTTPException(400, "缺少image参数")

    try:
        # 创建 temp 目录（如果不存在）
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True, parents=True)

        temp_path = temp_image_file(data["image"])
        result = ocr_engine.process_image(str(temp_path.absolute()))
        temp_path.unlink()  # 删除临时文件
    except Exception as e:
        raise HTTPException(500, str(e))

    return {
        "time_cost": round(time.time() - start_time, 2),
        "result": result
    }

@router.get("/health")
def health_check():
    """服务健康检查"""
    return {"status": "alive", "engine": "PaddleOCR"}