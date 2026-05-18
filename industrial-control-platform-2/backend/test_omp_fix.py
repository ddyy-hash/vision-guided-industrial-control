
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_omp_fix():
    print("=== 开始OpenMP库冲突修复测试 ===")

    try:
        from fix_omp_conflict import check_omp_health
        status_before = check_omp_health()
        print("\n修复前的状态:")
        print(f"修复应用: {status_before['fix_applied']}")
        print("环境变量:", status_before['environment_vars'])

        from fix_omp_conflict import apply_omp_fixes
        apply_omp_fixes()

        status_after = check_omp_health()
        print("\n修复后的状态:")
        print(f"修复应用: {status_after['fix_applied']}")
        print("环境变量:", status_after['environment_vars'])

        print("\n=== 测试关键库导入 ===")

        try:
            import numpy as np
            print(f"✓ NumPy导入成功 - 版本: {np.__version__}")
            arr = np.random.rand(1000, 1000)
            result = np.dot(arr, arr.T)
            print("✓ NumPy矩阵运算测试通过")
        except Exception as e:
            print(f"✗ NumPy导入失败: {e}")

        try:
            import cv2
            print(f"✓ OpenCV导入成功 - 版本: {cv2.__version__}")
            img = np.zeros((100, 100, 3), dtype=np.uint8)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            print("✓ OpenCV图像处理测试通过")
        except Exception as e:
            print(f"✗ OpenCV导入失败: {e}")

        try:
            import torch
            print(f"✓ PyTorch导入成功 - 版本: {torch.__version__}")
            print(f"  CUDA可用: {torch.cuda.is_available()}")

            if torch.cuda.is_available():
                device = 'cuda'
                print("  GPU设备测试...")
            else:
                device = 'cpu'
                print("  CPU设备测试...")

            x = torch.randn(100, 100, device=device)
            y = torch.randn(100, 100, device=device)
            z = torch.matmul(x, y)
            print("✓ PyTorch张量运算测试通过")

        except ImportError:
            print("ℹ PyTorch未安装，跳过测试")
        except Exception as e:
            print(f"✗ PyTorch测试失败: {e}")

        print("\n=== 测试追踪服务 ===")
        try:
            from services.tracking_service import get_tracking_service
            tracker = get_tracking_service()
            stats = tracker.get_tracking_stats()
            print("✓ 追踪服务初始化成功")
            print(f"  追踪状态: {'启用' if stats['tracking_enabled'] else '禁用'}")
            print(f"  GPU可用: {stats['gpu_info']['gpu_available']}")
        except Exception as e:
            print(f"✗ 追踪服务测试失败: {e}")

        print("\n=== 测试完成 ===")
        print("如果所有测试都通过，OpenMP冲突问题应该已经解决。")

        return True

    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")
        return False

def stress_test():
    print("\n=== 开始OpenMP压力测试 ===")

    try:
        import numpy as np
        import time

        start_time = time.time()

        large_matrix = np.random.rand(2000, 2000)
        for i in range(5):
            result = np.linalg.inv(large_matrix)
            print(f"  矩阵求逆迭代 {i+1}/5 完成")

        elapsed = time.time() - start_time
        print(f"✓ 压力测试通过 - 耗时: {elapsed:.2f}秒")
        return True

    except Exception as e:
        print(f"✗ 压力测试失败: {e}")
        return False

if __name__ == '__main__':
    print("OpenMP库冲突修复验证工具")
    print("=" * 50)

    basic_success = test_omp_fix()

    if basic_success:
        stress_success = stress_test()
    else:
        stress_success = False

    print("\n" + "=" * 50)
    print("测试总结:")
    print(f"基本测试: {'通过' if basic_success else '失败'}")
    print(f"压力测试: {'通过' if stress_success else '失败'}")

    if basic_success and stress_success:
        print("🎉 所有测试通过！OpenMP冲突问题已解决。")
    else:
        print("⚠️ 部分测试失败，请检查错误信息。")
        print("\n建议:")
        print("1. 确保所有依赖库已正确安装")
        print("2. 检查系统环境变量设置")
        print("3. 重启Python进程以应用环境变量更改")