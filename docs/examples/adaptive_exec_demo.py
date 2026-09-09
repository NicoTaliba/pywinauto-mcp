"""
PyWinAuto MCP — AdaptiveExec 自适应自愈执行示例

演示如何使用 adaptive_execute 执行工作流，
包括自动错误识别、恢复策略应用、指数退避重试。

运行方式：
    python docs/examples/adaptive_exec_demo.py
"""

import sys
import os
import json
import time

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPT_DIR))

from generation_engine import adaptive_execute, _RECOVERY_STRATEGIES, _classify_error


def demo_1_recovery_strategies():
    """演示 1：查看内置恢复策略"""
    print("=" * 60)
    print("演示 1：内置错误恢复策略")
    print("=" * 60)

    print(f"\n共 {len(_RECOVERY_STRATEGIES)} 类错误恢复策略:\n")

    for category, strategies in _RECOVERY_STRATEGIES.items():
        print(f"  [{category}]")
        for i, s in enumerate(strategies, 1):
            print(f"    {i}. {s.get('name', 'unknown')}: {s.get('description', '')}")
        print()


def demo_2_error_classification():
    """演示 2：错误分类"""
    print("=" * 60)
    print("演示 2：错误消息自动分类")
    print("=" * 60)

    test_errors = [
        "Could not find the specified element",
        "The operation timed out after 10 seconds",
        "Element is not enabled",
        "Element is not visible",
        "Permission denied: access is denied",
        "Session not found: app_xxx",
        "Some unknown error occurred",
    ]

    print(f"\n测试 {len(test_errors)} 条错误消息:\n")

    for err in test_errors:
        result = _classify_error(err)
        category = result.get("category", "unknown")
        suggestions = result.get("suggestions", [])
        print(f"  \"{err[:50]}...\"")
        print(f"    -> 分类: {category}")
        print(f"    -> 建议: {suggestions[0] if suggestions else '无'}")
        print()


def demo_3_basic_workflow():
    """演示 3：基础工作流自适应执行"""
    print("=" * 60)
    print("演示 3：基础工作流自适应执行")
    print("=" * 60)

    steps = [
        {
            "tool": "app_start",
            "params": {"cmd_line": "notepad.exe", "backend": "uia"},
            "output_key": "app_id",
            "description": "启动记事本"
        },
        {
            "tool": "app_top_window",
            "params": {"app_id": "$app_id$"},
            "output_key": "wrapper_id",
            "description": "获取主窗口"
        },
        {
            "tool": "control_child_window",
            "params": {"wrapper_id": "$wrapper_id$", "control_type": "Document"},
            "output_key": "edit_id",
            "description": "定位编辑区"
        },
        {
            "tool": "safe_type_text",
            "params": {"wrapper_id": "$edit_id$", "text": "Hello from AdaptiveExec!"},
            "description": "输入文本"
        },
    ]

    print(f"\n工作流: {len(steps)} 步")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step['description']} ({step['tool']})")

    print("\n执行中（启用自动恢复）...")
    result = adaptive_execute(
        json.dumps(steps),
        auto_recover=True,
        max_retries_per_step=3,
        name="记事本输入演示"
    )

    print(f"\n执行结果:")
    print(f"  状态: {result['status']}")
    print(f"  成功步骤: {result['succeeded']}")
    print(f"  失败步骤: {result['errors']}")
    print(f"  自动恢复次数: {result['total_recoveries']}")
    print(f"  总耗时: {result.get('total_time', 0):.2f}s")

    if result.get("recovery_log"):
        print(f"\n恢复日志:")
        for log in result["recovery_log"]:
            print(f"  步骤{log['step']} ({log.get('step_name', '')}):")
            print(f"    错误: {log.get('error', '')[:60]}")
            print(f"    分类: {log.get('error_category', '')}")
            print(f"    策略: {log.get('strategy', '')}")
            print(f"    结果: {log.get('result', '')}")

    if result.get("context"):
        print(f"\n执行上下文:")
        for key, value in result["context"].items():
            val_str = str(value)[:50]
            print(f"  {key}: {val_str}")


def demo_4_with_deliberate_error():
    """演示 4：故意制造错误，观察自愈过程"""
    print("\n" + "=" * 60)
    print("演示 4：错误自愈演示")
    print("=" * 60)

    # 第一步使用不存在的应用，观察错误处理
    steps = [
        {
            "tool": "app_start",
            "params": {"cmd_line": "nonexistent_app_xyz123.exe"},
            "output_key": "app_id",
            "description": "启动不存在的应用（会失败）"
        },
        {
            "tool": "sysinfo_os_arch",
            "params": {},
            "output_key": "os_arch",
            "description": "获取系统架构（应该能成功）"
        },
    ]

    print(f"\n工作流: {len(steps)} 步")
    print(f"  1. 启动不存在的应用（预期失败，观察恢复策略）")
    print(f"  2. 获取系统架构（预期成功）")

    print("\n执行中（stop_on_error=False，继续执行后续步骤）...")
    result = adaptive_execute(
        json.dumps(steps),
        auto_recover=True,
        max_retries_per_step=2,
        stop_on_error=False,
        name="错误自愈演示"
    )

    print(f"\n执行结果:")
    print(f"  状态: {result['status']}")
    print(f"  成功: {result['succeeded']}, 失败: {result['errors']}")
    print(f"  恢复次数: {result['total_recoveries']}")

    if result.get("recovery_log"):
        print(f"\n恢复日志:")
        for log in result["recovery_log"]:
            print(f"  步骤{log['step']}: {log.get('error_category', '')} -> {log.get('strategy', '')}")


def demo_5_step_level_features():
    """演示 5：步骤级高级特性"""
    print("\n" + "=" * 60)
    print("演示 5：步骤级高级特性")
    print("=" * 60)

    steps = [
        {
            "tool": "sysinfo_os_arch",
            "params": {},
            "output_key": "os_arch",
            "description": "获取系统架构",
            "timeout": 5,
            "retry": 2
        },
        {
            "tool": "timings_get",
            "params": {},
            "output_key": "timings",
            "description": "获取时序配置",
            "wait": 0.5
        },
        {
            "tool": "sysinfo_is_x64_python",
            "params": {},
            "output_key": "is_x64",
            "description": "检查 Python 是否为 64 位",
            "condition": "$os_arch$ == 'AMD64'",
            "ignore_error": True
        },
    ]

    print(f"\n工作流特性演示:")
    print(f"  步骤1: timeout=5s, retry=2")
    print(f"  步骤2: wait=0.5s（执行后等待）")
    print(f"  步骤3: condition=\"$os_arch$ == 'AMD64'\"（条件执行）, ignore_error=True")

    print("\n执行中...")
    result = adaptive_execute(json.dumps(steps), auto_recover=True)

    print(f"\n执行结果:")
    print(f"  状态: {result['status']}")
    print(f"  成功: {result['succeeded']}, 失败: {result['errors']}")

    if result.get("context"):
        print(f"\n上下文变量:")
        for key, value in result["context"].items():
            print(f"  {key}: {value}")


def main():
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 11 + "AdaptiveExec 自适应自愈执行演示" + " " * 11 + "║")
    print("╚" + "═" * 58 + "╝")

    # 纯算法演示
    demo_1_recovery_strategies()
    demo_2_error_classification()

    # 需要 GUI 的演示
    if "--no-gui" not in sys.argv:
        try:
            demo_3_basic_workflow()
            demo_4_with_deliberate_error()
        except Exception as e:
            print(f"\n⚠️  GUI 演示出错: {e}")
    else:
        print("\n（已跳过 GUI 演示）")

    # 步骤级特性演示（不需要 GUI）
    demo_5_step_level_features()

    # 清理
    try:
        from pywinauto_wrapper import close_all_sessions
        close_all_sessions()
    except Exception:
        pass

    print("\n所有演示完成！")


if __name__ == "__main__":
    main()
