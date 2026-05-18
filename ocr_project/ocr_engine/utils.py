import base64
import uuid
from pathlib import Path
from PIL import Image
import io
from core.config import Config

def temp_image_file(b64_str: str) -> Path:
    """Base64转临时图片文件 - 修复导入错误"""
    try:
        # 处理可能的 data URI 格式 (data:image/png;base64,...)
        if b64_str.startswith("data:"):
            b64_str = b64_str.split(",")[1]

        img_data = base64.b64decode(b64_str)

        # 验证图片大小
        if len(img_data) > Config.MAX_IMAGE_SIZE:
            raise ValueError(
                f"图片大小超过限制 ({len(img_data) / 1024 / 1024:.1f}MB > {Config.MAX_IMAGE_SIZE / 1024 / 1024}MB)")

        # 创建临时目录
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True, parents=True)

        # 生成唯一文件名
        temp_path = temp_dir / f"{uuid.uuid4().hex}.png"

        # 保存图片
        with temp_path.open("wb") as f:
            f.write(img_data)

        return temp_path
    except Exception as e:
        raise RuntimeError(f"图片处理失败: {str(e)}")