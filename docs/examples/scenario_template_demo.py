"""
PyWinAuto MCP — ScenarioLib & ScriptGen 场景模板与脚本生成示例

演示如何使用场景模板快速生成工作流，以及如何将工作流导出为
独立可运行的 pywinauto Python 脚本。

运行方式：
    python docs/examples/scenario_template_demo.py
"""

import sys
import os
import json

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPT_DIR))

from generation_engine import (
    list_scenarios,
    apply_scenario,
    generate_script,
    SCENARIOS,
)


def demo_1_list_scenarios():
    """演示 1：列出所有场景模板"""
    print("=" * 60)
    print("演示 1：可用场景模板")
    print("=" * 60)

    result = list_scenarios()
    print(f"\n共 {result['count']} 个场景模板:\n")

    # 按类别分组
    categories = {}
    for s in result["scenarios"]:
        cat = s.get("category", "其他")
        categories.setdefault(cat, []).append(s)

    for cat, scenarios in categories.items():
        print(f"  [{cat}]")
        for s in scenarios:
            print(f"    - {s['id']:<25} {s['name']:<20} ({s['step_count']}步)")
        print()


def demo_2_scenario_details():
    """演示 2：查看场景详细信息"""
    print("=" * 60)
    print("演示 2：场景详细信息")
    print("=" * 60)

    scenario_ids = ["notepad_basic", "calculator_math", "form_fill", "dialog_confirm"]

    for sid in scenario_ids:
        scenario = SCENARIOS.get(sid)
        if not scenario:
            continue

        print(f"\n--- {sid}: {scenario['name']} ---")
        print(f"  描述: {scenario.get('description', '')}")
        print(f"  类别: {scenario.get('category', '')}")
        print(f"  步骤数: {scenario.get('step_count', 0)}")

        params = scenario.get("params", [])
        if params:
            print(f"  参数:")
            for p in params:
                default = p.get("default", "")
                required = "必填" if p.get("required") else "可选"
                print(f"    - {p['name']} ({p['type']}, {required}): {p.get('description', '')} [默认: {default}]")

        steps = scenario.get("steps", [])
        if steps:
            print(f"  步骤:")
            for i, step in enumerate(steps, 1):
                tool = step.get("tool", "")
                desc = step.get("description", "")
                print(f"    {i}. [{tool}] {desc}")


def demo_3_apply_notepad():
    """演示 3：应用记事本场景"""
    print("\n" + "=" * 60)
    print("演示 3：应用记事本场景")
    print("=" * 60)

    params = {"text": "Hello from Scenario Template!", "save": False}
    print(f"\n场景: notepad_basic")
    print(f"参数: {json.dumps(params, ensure_ascii=False)}")

    result = apply_scenario("notepad_basic", params_json=json.dumps(params))

    print(f"\n生成结果:")
    print(f"  场景名称: {result['scenario_name']}")
    print(f"  步骤数: {result['step_count']}")
    print(f"  验证通过: {result['validation']['valid']}")

    print(f"\n工作流步骤:")
    for i, step in enumerate(result["steps"], 1):
        tool = step["tool"]
        desc = step.get("description", "")
        params_str = json.dumps(step.get("params", {}), ensure_ascii=False)
        print(f"  {i}. [{tool}] {desc}")
        print(f"     参数: {params_str}")


def demo_4_apply_calculator():
    """演示 4：应用计算器场景"""
    print("\n" + "=" * 60)
    print("演示 4：应用计算器场景")
    print("=" * 60)

    params = {"expression": "123+456"}
    print(f"\n场景: calculator_math")
    print(f"参数: {json.dumps(params, ensure_ascii=False)}")

    result = apply_scenario("calculator_math", params_json=json.dumps(params))

    print(f"\n生成结果:")
    print(f"  步骤数: {result['step_count']}")
    print(f"  验证通过: {result['validation']['valid']}")

    print(f"\n工作流步骤:")
    for i, step in enumerate(result["steps"], 1):
        tool = step["tool"]
        desc = step.get("description", "")
        print(f"  {i}. [{tool}] {desc}")


def demo_5_generate_script_from_workflow():
    """演示 5：从工作流 ID 生成脚本"""
    print("\n" + "=" * 60)
    print("演示 5：从工作流生成独立 Python 脚本")
    print("=" * 60)

    workflow_id = "WF001"
    script_name = "start_notepad"

    print(f"\n工作流 ID: {workflow_id}")
    print(f"脚本名称: {script_name}")

    result = generate_script(workflow_id=workflow_id, script_name=script_name)

    print(f"\n生成结果:")
    print(f"  状态: {result['status']}")
    print(f"  代码行数: {result['lines_of_code']}")
    print(f"  支持的步骤: {result.get('supported_steps', 0)}")
    print(f"  不支持的步骤: {result.get('unsupported_steps', 0)}")

    print(f"\n生成的脚本:\n")
    print("-" * 60)
    print(result["script"])
    print("-" * 60)

    # 保存到文件
    output_path = os.path.join(os.path.dirname(__file__), "generated_start_notepad.py")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result["script"])
    print(f"\n脚本已保存到: {output_path}")
    print(f"可以直接运行: python {output_path}")


def demo_6_generate_script_from_scenario():
    """演示 6：从场景模板生成脚本"""
    print("\n" + "=" * 60)
    print("演示 6：从场景模板生成脚本")
    print("=" * 60)

    result = generate_script(scenario_id="notepad_basic", script_name="notepad_scenario")

    print(f"\n生成结果:")
    print(f"  状态: {result['status']}")
    print(f"  代码行数: {result['lines_of_code']}")

    print(f"\n生成的脚本（前 30 行）:\n")
    lines = result["script"].split("\n")
    for i, line in enumerate(lines[:30]):
        print(f"  {i+1:3d} | {line}")
    if len(lines) > 30:
        print(f"  ... ({len(lines) - 30} more lines)")


def demo_7_generate_script_from_custom():
    """演示 7：从自定义步骤生成脚本"""
    print("\n" + "=" * 60)
    print("演示 7：从自定义步骤生成脚本")
    print("=" * 60)

    custom_steps = [
        {"tool": "app_start", "params": {"cmd_line": "calc.exe"}, "output_key": "app_id", "description": "启动计算器"},
        {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "win", "description": "获取窗口"},
        {"tool": "keyboard_send_keys", "params": {"keys": "123+456="}, "description": "输入计算式"},
    ]

    print(f"\n自定义步骤: {len(custom_steps)} 步")
    for i, step in enumerate(custom_steps, 1):
        print(f"  {i}. {step['description']}")

    result = generate_script(steps_json=json.dumps(custom_steps), script_name="custom_calc")

    print(f"\n生成结果:")
    print(f"  状态: {result['status']}")
    print(f"  代码行数: {result['lines_of_code']}")

    print(f"\n生成的脚本:\n")
    print("-" * 60)
    print(result["script"])
    print("-" * 60)


def main():
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 8 + "ScenarioLib & ScriptGen 场景模板与脚本生成演示" + " " * 8 + "║")
    print("╚" + "═" * 58 + "╝")

    # 场景模板演示
    demo_1_list_scenarios()
    demo_2_scenario_details()
    demo_3_apply_notepad()
    demo_4_apply_calculator()

    # 脚本生成演示
    demo_5_generate_script_from_workflow()
    demo_6_generate_script_from_scenario()
    demo_7_generate_script_from_custom()

    print("\n所有演示完成！")
    print("\n提示:")
    print("  - 生成的脚本不依赖 MCP 服务器，可以直接运行")
    print("  - 可以根据需要修改生成的脚本")
    print("  - 不支持的工具会标记为 TODO，需要手动实现")


if __name__ == "__main__":
    main()
