"""
PyWinAuto MCP — NL2Workflow 自然语言转工作流示例

演示如何使用 generation_engine 的 generate_workflow 和 generate_and_execute
将自然语言描述转换为可执行的工作流步骤。

运行方式：
    python docs/examples/nl2workflow_demo.py
"""

import sys
import os
import json

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPT_DIR))

from generation_engine import generate_workflow, generate_and_execute


def demo_1_basic():
    """演示 1：基础自然语言生成"""
    print("=" * 60)
    print("演示 1：基础自然语言生成")
    print("=" * 60)

    description = "启动记事本，输入Hello World，然后保存"
    print(f"\n输入: \"{description}\"")

    result = generate_workflow(description)

    print(f"\n生成结果:")
    print(f"  步骤数: {result['step_count']}")
    print(f"  置信度: {result['confidence']}")
    print(f"  验证通过: {result['validation']['valid']}")

    print(f"\n推理过程:")
    for r in result["reasoning"]:
        tool = r.get("tool", "-")
        action = r.get("action", "unknown")
        sentence = r.get("sentence", "")
        print(f"  - \"{sentence}\" -> {action} -> {tool}")

    print(f"\n工作流步骤:")
    for i, step in enumerate(result["steps"], 1):
        desc = step.get("description", "")
        tool = step["tool"]
        params = step.get("params", {})
        print(f"  {i}. [{tool}] {desc}")
        if params:
            for k, v in params.items():
                print(f"       {k}: {v}")

    print(f"\nJSON 格式（可直接用于 workflow_execute_custom）:")
    print(json.dumps(result["steps"], ensure_ascii=False, indent=2)[:500] + "...")


def demo_2_complex():
    """演示 2：复杂多步骤任务"""
    print("\n" + "=" * 60)
    print("演示 2：复杂多步骤任务")
    print("=" * 60)

    description = "启动计算器，输入123，加号，456，等号，然后截图，最后关闭"
    print(f"\n输入: \"{description}\"")

    result = generate_workflow(description)

    print(f"\n生成结果:")
    print(f"  步骤数: {result['step_count']}")
    print(f"  置信度: {result['confidence']}")
    print(f"  验证通过: {result['validation']['valid']}")

    print(f"\n工作流步骤:")
    for i, step in enumerate(result["steps"], 1):
        desc = step.get("description", "")
        tool = step["tool"]
        print(f"  {i}. [{tool}] {desc}")


def demo_3_with_context():
    """演示 3：带上下文的生成"""
    print("\n" + "=" * 60)
    print("演示 3：带上下文的生成")
    print("=" * 60)

    description = "在当前窗口输入测试文本，然后点击确定按钮"
    context = {
        "app_id": "app_demo123456",
        "wrapper_id": "ctrl_demo123456",
        "app_name": "演示应用"
    }

    print(f"\n输入: \"{description}\"")
    print(f"上下文: {json.dumps(context, ensure_ascii=False)}")

    result = generate_workflow(description, context_json=json.dumps(context))

    print(f"\n生成结果:")
    print(f"  步骤数: {result['step_count']}")
    print(f"  置信度: {result['confidence']}")

    print(f"\n工作流步骤:")
    for i, step in enumerate(result["steps"], 1):
        desc = step.get("description", "")
        tool = step["tool"]
        params = step.get("params", {})
        print(f"  {i}. [{tool}] {desc}")
        for k, v in params.items():
            print(f"       {k}: {v}")


def demo_4_various_tasks():
    """演示 4：各种任务类型"""
    print("\n" + "=" * 60)
    print("演示 4：各种任务类型")
    print("=" * 60)

    tasks = [
        "启动记事本",
        "关闭当前应用",
        "最大化窗口",
        "最小化窗口",
        "截取当前窗口",
        "输入用户名admin",
        "点击登录按钮",
        "双击文件",
        "右键点击",
        "按Ctrl+C复制",
        "按Ctrl+V粘贴",
        "按Ctrl+S保存",
        "按Alt+F4关闭",
        "等待3秒",
        "打开文件菜单",
    ]

    print(f"\n测试 {len(tasks)} 种任务描述:\n")

    for task in tasks:
        result = generate_workflow(task)
        status = "✓" if result["validation"]["valid"] else "✗"
        first_step = result["steps"][0]["tool"] if result["steps"] else "-"
        print(f"  {status} \"{task}\" -> {result['step_count']}步 ({first_step}) 置信度={result['confidence']}")


def demo_5_generate_and_execute():
    """演示 5：生成并执行（需要真实环境）"""
    print("\n" + "=" * 60)
    print("演示 5：生成并执行")
    print("=" * 60)

    description = "启动记事本，输入Hello from NL2Workflow"
    print(f"\n输入: \"{description}\"")
    print("\n注意：此演示会实际启动记事本并输入文本")
    print("按 Enter 继续，或 Ctrl+C 取消...")

    try:
        input()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return

    print("\n执行中...")
    result = generate_and_execute(description)

    print(f"\n执行结果:")
    print(f"  状态: {result.get('status', 'unknown')}")
    print(f"  步骤数: {result.get('step_count', 0)}")
    if result.get("error"):
        print(f"  错误: {result['error']}")


def main():
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 12 + "NL2Workflow 自然语言转工作流演示" + " " * 12 + "║")
    print("╚" + "═" * 58 + "╝")

    demo_1_basic()
    demo_2_complex()
    demo_3_with_context()
    demo_4_various_tasks()

    # 演示 5 需要用户确认
    print("\n" + "=" * 60)
    print("演示 5（生成并执行）需要实际操作 GUI")
    print("运行 python docs/examples/nl2workflow_demo.py --execute 来启用")
    print("=" * 60)

    if "--execute" in sys.argv:
        demo_5_generate_and_execute()

    print("\n所有演示完成！")


if __name__ == "__main__":
    main()
