import sys
import os
from pathlib import Path
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware  # 添加CORS支持
import uvicorn
import logging
# main.py 开头添加
from loguru import logger
import asyncio

# 在文件开头添加
import sys
import os
from pathlib import Path

# 判断是否打包环境
if getattr(sys, 'frozen', False):
    base_dir = Path(sys._MEIPASS)
else:
    base_dir = Path(__file__).parent

PROJECT_ROOT = base_dir
sys.path.insert(0, str(PROJECT_ROOT))

# 设置模型路径（重要！）
os.environ["PADDLEOCR_MODEL_PATH"] = str(PROJECT_ROOT / "paddleocr_json")

# 获取当前文件所在目录的绝对路径
current_dir = Path(__file__).parent.absolute()
project_root = current_dir  # 假设main.py在项目根目录

# 将项目根目录添加到系统路径
sys.path.insert(0, str(project_root))

# 尝试导入模块
try:
    from routers import ocr, energy
    ocr_router = ocr.router
    energy_router = energy.router
except ImportError:
    # 尝试手动添加 routers 目录
    routers_dir = project_root / "routers"
    sys.path.insert(0, str(routers_dir))
    try:
        # 直接导入模块中的路由器
        from routers.ocr import router as ocr_router
        from routers.energy import router as energy_router
    except ImportError:
        # 创建空路由器作为回退
        from fastapi import APIRouter
        ocr_router = APIRouter()
        energy_router = APIRouter()

try:
    from ocr_engine.paddle_ocr_wrapper import ocr_engine
except ImportError:
    # 尝试手动添加 ocr_engine 目录
    ocr_engine_dir = project_root / "ocr_engine"
    sys.path.insert(0, str(ocr_engine_dir))
    try:
        from ocr_engine.paddle_ocr_wrapper import ocr_engine
    except ImportError:
        # 创建虚拟引擎作为回退
        class DummyOCR:
            is_ready = True
            def process_image(self, path):
                return {"code": 500, "message": "OCR引擎未正确加载"}
            def close(self):
                pass
        ocr_engine = DummyOCR()

# 确保临时目录存在
(PROJECT_ROOT / "temp").mkdir(exist_ok=True, parents=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期管理 - 包含测试机制"""
    logger.info("服务启动中...")
    # 创建所需目录
    (PROJECT_ROOT / "temp").mkdir(exist_ok=True, parents=True)
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)

    test_image = PROJECT_ROOT / "static/test_images/test.png"
    logger.info(f"测试图片路径: {test_image.absolute()}")

    if test_image.exists():
        logger.info(f"文件大小: {test_image.stat().st_size} bytes")
        try:
            logger.info("正在测试OCR引擎...")
            # 等待引擎初始化完成
            max_wait = 30  # 最大等待30秒
            wait_time = 0
            while not ocr_engine.is_ready and wait_time < max_wait:
                await asyncio.sleep(0.5)
                wait_time += 0.5

            if not ocr_engine.is_ready:
                logger.error("OCR引擎初始化超时")
                yield
                return
            # 使用字符串路径并确保Windows路径格式
            win_path = str(test_image.absolute()).replace('/', '\\')

            # 增加测试图片处理时间
            start_time = time.time()
            result = ocr_engine.process_image(win_path)
            elapsed = time.time() - start_time

            logger.info(f"测试耗时: {elapsed:.2f}秒")
            logger.info(f"测试结果代码: {result.get('code', '未知')}")

            if result.get("code") == 100:
                logger.success("OCR引擎测试成功")
                # 记录识别结果
                data = result.get("data", [])
                logger.info(f"识别到 {len(data)} 个文本块")
                for i, item in enumerate(data[:3]):  # 只显示前3个结果
                    text = item.get('text', '')
                    confidence = item.get('score', 0)
                    logger.info(f"结果[{i+1}]: '{text}' (置信度: {confidence:.3f})")
            else:
                logger.error(f"OCR引擎测试失败: {result}")
                if "message" in result:
                    logger.error(f"失败原因: {result['message']}")
        except Exception as e:
            logger.error(f"OCR引擎测试异常: {e}")
            logger.error(f"异常详情: {type(e).__name__}: {str(e)}")
    else:
        logger.warning("未找到测试图片，跳过引擎测试")
        # 自动创建测试图片
        test_image.parent.mkdir(exist_ok=True, parents=True)
        try:
            from PIL import Image, ImageDraw, ImageFont
            # 创建带文字的测试图片
            img = Image.new('RGB', (300, 100), color='white')
            draw = ImageDraw.Draw(img)
            try:
                # 尝试使用系统字体
                font = ImageFont.truetype("simhei.ttf", 20)
            except:
                font = ImageFont.load_default()
            draw.text((10, 30), "测试文字识别", fill='black', font=font)
            img.save(test_image)
            logger.info(f"已创建测试图片: {test_image}")
        except Exception as create_error:
            logger.warning(f"创建测试图片失败: {create_error}")

    yield

    logger.info("服务关闭中...")
    ocr_engine.close()
    logger.success("服务已安全退出")

app = FastAPI(
    title="Umi-OCR深度定制版",
    description="集成PaddleOCR-json的OCR服务",
    version="1.0",
    lifespan=lifespan
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件和路由
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 包含OCR和能耗识别路由
app.include_router(ocr_router, prefix="/api/ocr", tags=["OCR服务"])
app.include_router(energy_router, prefix="/api/energy", tags=["能耗识别服务"])

@app.get("/")
async def serve_ui(request: Request):
    """提供UI界面"""
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )