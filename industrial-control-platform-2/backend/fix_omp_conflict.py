
import os
import sys
import logging
import warnings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenMPConflictFixer:

    def __init__(self):
        self.fix_applied = False
        self.original_env = {}

    def apply_fixes(self):
        if self.fix_applied:
            logger.info("OpenMP修复已应用，跳过重复应用")
            return True

        try:
            logger.info("开始应用OpenMP库冲突修复...")

            self._save_original_env()

            self._set_omp_environment()

            self._adjust_library_loading()

            self._configure_thread_settings()

            self._suppress_omp_warnings()

            self.fix_applied = True
            logger.info("OpenMP库冲突修复应用成功")
            return True

        except Exception as e:
            logger.error(f"应用OpenMP修复失败: {e}")
            return False

    def _save_original_env(self):
        env_vars = [
            'KMP_DUPLICATE_LIB_OK', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
            'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'
        ]

        for var in env_vars:
            self.original_env[var] = os.environ.get(var)

    def _set_omp_environment(self):
        os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

        cpu_count = os.cpu_count() or 4
        threads = min(cpu_count, 8)

        os.environ['OMP_NUM_THREADS'] = str(threads)
        os.environ['MKL_NUM_THREADS'] = str(threads)
        os.environ['OPENBLAS_NUM_THREADS'] = str(threads)
        os.environ['VECLIB_MAXIMUM_THREADS'] = str(threads)

        logger.info(f"设置OpenMP线程数: {threads} (CPU核心: {cpu_count})")

    def _adjust_library_loading(self):
        pass

    def _configure_thread_settings(self):
        try:
            os.environ['KMP_AFFINITY'] = 'granularity=fine,compact,1,0'
        except:
            pass

        try:
            os.environ['OMP_STACKSIZE'] = '64M'
        except:
            pass

    def _suppress_omp_warnings(self):
        warnings.filterwarnings('ignore', category=UserWarning, module='torch')
        warnings.filterwarnings('ignore', category=UserWarning, module='numpy')

        os.environ['PYTHONWARNINGS'] = 'ignore'

    def restore_original_env(self):
        if not self.original_env:
            return

        for var, value in self.original_env.items():
            if value is None:
                if var in os.environ:
                    del os.environ[var]
            else:
                os.environ[var] = value

        self.fix_applied = False
        logger.info("原始环境变量已恢复")

    def check_omp_status(self):
        status = {
            'fix_applied': self.fix_applied,
            'environment_vars': {},
            'library_status': {}
        }

        env_vars = [
            'KMP_DUPLICATE_LIB_OK', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
            'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'
        ]

        for var in env_vars:
            status['environment_vars'][var] = os.environ.get(var)

        try:
            import torch
            status['library_status']['pytorch'] = {
                'available': True,
                'version': torch.__version__,
                'cuda_available': torch.cuda.is_available(),
                'openmp_available': hasattr(torch, '__config__')
            }
        except ImportError:
            status['library_status']['pytorch'] = {'available': False}

        try:
            import numpy as np
            status['library_status']['numpy'] = {
                'available': True,
                'version': np.__version__,
                'openmp_available': hasattr(np, '__config__')
            }
        except ImportError:
            status['library_status']['numpy'] = {'available': False}

        try:
            import cv2
            status['library_status']['opencv'] = {
                'available': True,
                'version': cv2.__version__
            }
        except ImportError:
            status['library_status']['opencv'] = {'available': False}

        return status

_omp_fixer = None

def get_omp_fixer():
    global _omp_fixer
    if _omp_fixer is None:
        _omp_fixer = OpenMPConflictFixer()
    return _omp_fixer

def apply_omp_fixes():
    fixer = get_omp_fixer()
    return fixer.apply_fixes()

def check_omp_health():
    fixer = get_omp_fixer()
    return fixer.check_omp_status()

apply_omp_fixes()

if __name__ == '__main__':
    print("=== OpenMP库冲突修复测试 ===")

    fixer = get_omp_fixer()
    status = fixer.check_omp_status()

    print(f"修复状态: {'已应用' if status['fix_applied'] else '未应用'}")
    print("\n环境变量:")
    for var, value in status['environment_vars'].items():
        print(f"  {var}: {value}")

    print("\n库状态:")
    for lib, info in status['library_status'].items():
        if info['available']:
            print(f"  {lib}: 可用 (版本: {info.get('version', '未知')})")
        else:
            print(f"  {lib}: 不可用")

    print("\n=== 测试完成 ===")
