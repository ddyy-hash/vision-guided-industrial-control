import os
from pathlib import Path

class Config:
    # OCR引擎路径配置
    OCR_EXE_PATH = Path(__file__).parent.parent / "paddleocr_json" / "PaddleOCR-json.exe"
    MODEL_DIR = Path(__file__).parent.parent / "paddleocr_json" / "models"
    
    # 指定加载的语言模型（中英文）
    LANGUAGES = "ch,en"

    # 性能配置
    OCR_TIMEOUT = 120  # 单次OCR超时时间(秒)
    MAX_IMAGE_SIZE = 1024 * 1024 * 20  # 20MB图片大小限制
    CPU_THREADS = 4
    USE_ANGLE_CLS = False

    # 日志配置
    LOG_DIR = Path("logs")
    LOG_LEVEL = "DEBUG"

    @classmethod
    def validate_paths(cls):
        """验证所有必需路径"""
        if not cls.OCR_EXE_PATH.exists():
            raise FileNotFoundError(f"OCR可执行文件不存在: {cls.OCR_EXE_PATH}")
        if not cls.MODEL_DIR.exists():
            raise NotADirectoryError(f"模型目录不存在: {cls.MODEL_DIR}")

        # 验证可执行权限
        if not os.access(cls.OCR_EXE_PATH, os.X_OK):
            raise PermissionError(f"OCR可执行文件无执行权限: {cls.OCR_EXE_PATH}")

        # 验证测试图片目录
        test_dir = Path("static/test_images")
        test_dir.mkdir(exist_ok=True, parents=True)

        # 创建测试图片（如果不存在）
        test_image = test_dir / "test.png"
        if not test_image.exists():
            # 创建一个简单的测试图片
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='white')
            img.save(test_image)

# 初始化时验证路径
Config.validate_paths()