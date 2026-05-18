# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import os

# 排除不必要的模块以减小体积
excluded_modules = [
    'tkinter', 
    'matplotlib',
    'scipy',
    'pytest',
    'unittest'
]

# 包含OCR引擎和静态资源
def get_data_files():
    data = []
    
    # 包含paddleocr_json目录
    ocr_engine_path = os.path.join('paddleocr_json')
    for root, dirs, files in os.walk(ocr_engine_path):
        for file in files:
            src = os.path.join(root, file)
            dest = root
            data.append((src, dest))
    
    # 包含static静态资源
    static_path = os.path.join('static')
    for root, dirs, files in os.walk(static_path):
        for file in files:
            src = os.path.join(root, file)
            dest = root
            data.append((src, dest))
    
    return data

# 主配置
a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=get_data_files(),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

# 单文件打包配置
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 可执行文件配置
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ocr_project',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 启用UPX压缩
    console=True,  # 显示控制台窗口
    disable_windowed_tracker=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)

# 构建后清理选项（删除build目录）
def _clean_build():
    import shutil
    build_dir = os.path.join(os.getcwd(), 'build')
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)

# 注册清理函数
import atexit
atexit.register(_clean_build)