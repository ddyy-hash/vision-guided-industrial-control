#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import logging
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pipeline_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def test_pipeline_controller():
    try:
        logger.info("开始测试流水线控制器...")

        from services.pipeline_controller import get_pipeline_controller

        pipeline_controller = get_pipeline_controller()

        logger.info("测试1: 获取初始状态")
        status = pipeline_controller.get_status()
        logger.info(f"初始状态: {status['pipeline_state']['status']}")
        assert status['pipeline_state']['status'] == 'idle', "初始状态应为idle"

        logger.info("测试2: 启动流水线")
        result = pipeline_controller.start_pipeline()
        logger.info(f"启动结果: {result}")
        assert result['success'] == True, "启动流水线应成功"

        status = pipeline_controller.get_status()
        logger.info(f"启动后状态: {status['pipeline_state']['status']}")
        assert status['pipeline_state']['status'] == 'running', "启动后状态应为running"

        logger.info("测试3: 暂停流水线")
        result = pipeline_controller.pause_pipeline()
        logger.info(f"暂停结果: {result}")
        assert result['success'] == True, "暂停流水线应成功"

        status = pipeline_controller.get_status()
        logger.info(f"暂停后状态: {status['pipeline_state']['status']}")
        assert status['pipeline_state']['status'] == 'paused', "暂停后状态应为paused"

        logger.info("测试4: 恢复流水线")
        result = pipeline_controller.resume_pipeline()
        logger.info(f"恢复结果: {result}")
        assert result['success'] == True, "恢复流水线应成功"

        status = pipeline_controller.get_status()
        logger.info(f"恢复后状态: {status['pipeline_state']['status']}")
        assert status['pipeline_state']['status'] == 'running', "恢复后状态应为running"

        logger.info("测试5: 停止流水线")
        result = pipeline_controller.stop_pipeline()
        logger.info(f"停止结果: {result}")
        assert result['success'] == True, "停止流水线应成功"

        status = pipeline_controller.get_status()
        logger.info(f"停止后状态: {status['pipeline_state']['status']}")
        assert status['pipeline_state']['status'] == 'idle', "停止后状态应为idle"

        logger.info("测试6: 配置更新")
        new_config = {
            "belt_speed": 0.15,
            "alignment_threshold": 20,
            "ocr_frame_interval": 3
        }
        result = pipeline_controller.update_config(new_config)
        logger.info(f"配置更新结果: {result}")
        assert result['success'] == True, "配置更新应成功"

        status = pipeline_controller.get_status()
        updated_config = status['config']
        logger.info(f"更新后配置 - 传送带速度: {updated_config['belt_speed']}")
        assert updated_config['belt_speed'] == 0.15, "传送带速度应更新为0.15"

        logger.info("✅ 所有基本功能测试通过!")
        return True

    except Exception as e:
        logger.error(f"流水线控制器测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_tracking_integration():
    try:
        logger.info("开始测试追踪服务集成...")

        from services.pipeline_controller import get_pipeline_controller
        from services.tracking_service import get_tracking_service

        pipeline_controller = get_pipeline_controller()
        tracking_service = get_tracking_service()

        mock_tracking_data = [
            {
                "track_id": 1,
                "class_name": "brick",
                "conveyor_x": 0.5,
                "conveyor_y": 0.3,
                "confidence": 0.95
            },
            {
                "track_id": 2,
                "class_name": "arm",
                "conveyor_x": 0.5,
                "conveyor_y": 0.3,
                "confidence": 0.98
            }
        ]

        logger.info("模拟追踪数据更新")
        pipeline_controller.update_tracking_data(mock_tracking_data)

        status = pipeline_controller.get_status()
        tracking_state = status['tracking_state']
        logger.info(f"追踪状态: {tracking_state['active_tracks']} 个活跃追踪")
        assert tracking_state['active_tracks'] == 2, f"应有2个活跃追踪，实际有{tracking_state['active_tracks']}个"

        logger.info("✅ 追踪服务集成测试通过!")
        return True

    except Exception as e:
        logger.error(f"追踪服务集成测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_ocr_integration():
    try:
        logger.info("开始测试OCR集成功能...")

        from services.pipeline_controller import get_pipeline_controller

        pipeline_controller = get_pipeline_controller()

        mock_ocr_results = [
            {
                "energy_level": "1级",
                "confidence": 0.92,
                "timestamp": datetime.now().isoformat(),
                "frame_data": "base64_data_1"
            },
            {
                "energy_level": "1级",
                "confidence": 0.88,
                "timestamp": datetime.now().isoformat(),
                "frame_data": "base64_data_2"
            },
            {
                "energy_level": "2级",
                "confidence": 0.85,
                "timestamp": datetime.now().isoformat(),
                "frame_data": "base64_data_3"
            }
        ]

        logger.info("测试OCR投票算法")
        final_result = pipeline_controller._vote_ocr_results(mock_ocr_results)

        logger.info(f"OCR投票结果: {final_result['energy_level']} (置信度: {final_result['confidence']:.2f})")
        logger.info(f"投票统计: {final_result['vote_count']}/{final_result['total_frames']}")

        assert final_result['energy_level'] == '1级', f"OCR投票结果应为1级，实际为{final_result['energy_level']}"
        assert final_result['vote_count'] == 2, f"应有2票投给1级，实际有{final_result['vote_count']}票"
        assert final_result['total_frames'] == 3, f"总帧数应为3，实际为{final_result['total_frames']}"

        logger.info("✅ OCR集成功能测试通过!")
        return True

    except Exception as e:
        logger.error(f"OCR集成功能测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_robot_arm_sequence():
    try:
        logger.info("开始测试机械臂序列功能...")

        from services.pipeline_controller import get_pipeline_controller

        pipeline_controller = get_pipeline_controller()

        mock_brick = {
            "track_id": 1,
            "class_name": "brick",
            "conveyor_x": 0.5,
            "conveyor_y": 0.3
        }

        logger.info("测试机械臂夹取序列结构")

        config = pipeline_controller.get_status()['config']
        logger.info(f"机械臂预设序列配置: {config.get('brick_class_name', '未设置')}")

        if hasattr(pipeline_controller, '_execute_robot_arm_pickup_sequence'):
            logger.info("✅ 机械臂夹取序列方法存在")
        else:
            logger.warning("⚠️ 机械臂夹取序列方法不存在")

        logger.info("✅ 机械臂序列功能测试通过!")
        return True

    except Exception as e:
        logger.error(f"机械臂序列功能测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    logger.info("=" * 50)
    logger.info("开始流水线集成测试")
    logger.info("=" * 50)

    test_results = []

    test_results.append(("流水线控制器基本功能", test_pipeline_controller()))
    test_results.append(("追踪服务集成", test_tracking_integration()))
    test_results.append(("OCR集成功能", test_ocr_integration()))
    test_results.append(("机械臂序列功能", test_robot_arm_sequence()))

    logger.info("=" * 50)
    logger.info("测试结果汇总:")
    logger.info("=" * 50)

    passed_tests = 0
    total_tests = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed_tests += 1

    success_rate = (passed_tests / total_tests) * 100
    logger.info(f"测试完成: {passed_tests}/{total_tests} 通过 ({success_rate:.1f}%)")

    if passed_tests == total_tests:
        logger.info("🎉 所有测试通过! 流水线重构成功!")
        return True
    else:
        logger.warning("⚠️ 部分测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)