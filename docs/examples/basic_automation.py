"""
PyWinAuto MCP — 基础自动化示例

演示如何使用 pywinauto_wrapper 进行基础的 Windows GUI 自动化。
包括：启动应用、获取窗口、定位控件、输入文本、点击按钮、快捷键。

运行方式：
    python docs/examples/basic_automation.py
"""

import sys
import os

# 将 scripts 目录加入路径
SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPT_DIR))

from pywinauto_wrapper import (
    app_start,
    app_top_window,
    control_child_window,
    control_type_keys,
    control_click,
    keyboard_send_keys,
    control_get_text,
    control_close,
    list_sessions,
    close_all_sessions,
)


def example_1_notepad():
    """示例 1：启动记事本，输入文本，保存"""
    print("=" * 60)
    print("示例 1：记事本基础操作")
    print("=" * 60)

    # 1. 启动记事本
    print("\n[1] 启动记事本...")
    app = app_start("notepad.exe", backend="uia", timeout=10)
    print(f"    app_id: {app['app_id']}")
    print(f"    process: {app.get('process_id', 'N/A')}")

    # 2. 获取主窗口
    print("\n[2] 获取主窗口...")
    win = app_top_window(app["app_id"])
    print(f"    wrapper_id: {win['wrapper_id']}")
    print(f"    标题: {win.get('text', 'N/A')}")
    print(f"    类名: {win.get('class_name', 'N/A')}")

    # 3. 定位编辑区（Document 控件）
    print("\n[3] 定位编辑区...")
    edit = control_child_window(win["wrapper_id"], control_type="Document")
    print(f"    wrapper_id: {edit['wrapper_id']}")
    print(f"    控件类型: {edit.get('control_type', 'N/A')}")

    # 4. 输入文本
    print("\n[4] 输入文本...")
    control_type_keys(edit["wrapper_id"], "Hello, PyWinAuto MCP!\n这是一个基础自动化示例。")
    print("    文本输入完成")

    # 5. 读取文本（验证）
    print("\n[5] 读取当前文本...")
    text = control_get_text(edit["wrapper_id"])
    print(f"    文本内容: {text.get('text', 'N/A')[:50]}...")

    # 6. 全选并复制（Ctrl+A, Ctrl+C）
    print("\n[6] 全选并复制...")
    keyboard_send_keys("^a")  # Ctrl+A 全选
    keyboard_send_keys("^c")  # Ctrl+C 复制
    print("    已全选并复制到剪贴板")

    # 7. 保存（Ctrl+S）
    print("\n[7] 打开保存对话框...")
    keyboard_send_keys("^s")  # Ctrl+S 保存
    print("    保存对话框已打开（请手动选择保存位置）")

    # 8. 关闭记事本
    print("\n[8] 关闭记事本...")
    # 注意：如果有未保存的更改，会弹出确认对话框
    # 这里演示如何关闭窗口
    # control_close(win["wrapper_id"])
    print("    （演示中不实际关闭，请手动关闭）")

    print("\n示例 1 完成！")


def example_2_calculator():
    """示例 2：启动计算器，执行简单计算"""
    print("\n" + "=" * 60)
    print("示例 2：计算器操作")
    print("=" * 60)

    # 1. 启动计算器
    print("\n[1] 启动计算器...")
    app = app_start("calc.exe", backend="uia", timeout=10)
    print(f"    app_id: {app['app_id']}")

    # 2. 获取主窗口
    print("\n[2] 获取计算器窗口...")
    win = app_top_window(app["app_id"])
    print(f"    标题: {win.get('text', 'N/A')}")

    # 3. 输入计算式（通过键盘）
    print("\n[3] 输入 123 + 456 = ...")
    keyboard_send_keys("123")
    keyboard_send_keys("{+}")
    keyboard_send_keys("456")
    keyboard_send_keys("=")
    print("    计算完成，结果应显示 579")

    # 4. 清空
    print("\n[4] 清空计算器...")
    keyboard_send_keys("{ESC}")  # Esc 清空
    print("    已清空")

    print("\n示例 2 完成！")


def example_3_session_management():
    """示例 3：会话管理"""
    print("\n" + "=" * 60)
    print("示例 3：会话管理")
    print("=" * 60)

    # 1. 查看当前会话
    print("\n[1] 查看当前会话...")
    sessions = list_sessions()
    print(f"    应用会话: {sessions.get('app_count', 0)} 个")
    print(f"    控件会话: {sessions.get('wrapper_count', 0)} 个")

    # 2. 启动一个应用
    print("\n[2] 启动记事本...")
    app = app_start("notepad.exe", backend="uia")
    win = app_top_window(app["app_id"])

    # 3. 再次查看会话
    print("\n[3] 查看更新后的会话...")
    sessions = list_sessions()
    print(f"    应用会话: {sessions.get('app_count', 0)} 个")
    print(f"    控件会话: {sessions.get('wrapper_count', 0)} 个")

    # 4. 清理全部会话
    print("\n[4] 清理全部会话...")
    result = close_all_sessions()
    print(f"    已关闭: {result.get('closed', 0)} 个会话")

    print("\n示例 3 完成！")


def main():
    """运行所有示例"""
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "PyWinAuto MCP 基础自动化示例" + " " * 15 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    try:
        # 示例 1：记事本操作
        example_1_notepad()

        # 示例 2：计算器操作
        example_2_calculator()

        # 示例 3：会话管理
        example_3_session_management()

        print("\n" + "=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保清理会话
        try:
            close_all_sessions()
        except Exception:
            pass


if __name__ == "__main__":
    main()
