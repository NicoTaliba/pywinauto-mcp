"""
PyWinAuto MCP — SmartLocator 智能元素定位示例

演示如何使用 smart_find 通过自然语言描述智能查找控件，
包括模糊匹配、语义排序、多维度评分。

运行方式：
    python docs/examples/smart_locator_demo.py
"""

import sys
import os

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPT_DIR))

from generation_engine import smart_find, _fuzzy_match_score, _detect_control_type
from pywinauto_wrapper import app_start, app_top_window


def demo_1_control_type_detection():
    """演示 1：控件类型自动检测"""
    print("=" * 60)
    print("演示 1：控件类型自动检测")
    print("=" * 60)

    descriptions = [
        "确定按钮",
        "用户名输入框",
        "文件下拉菜单",
        "是否记住密码复选框",
        "设置选项卡",
        "文件树",
        "音量滑块",
        "进度条",
        "列表框",
        "确定",
    ]

    print(f"\n测试 {len(descriptions)} 种描述:\n")
    for desc in descriptions:
        result = _detect_control_type(desc)
        ctype = result.get("control_type", "unknown")
        keywords = result.get("matched_keywords", [])
        print(f"  \"{desc}\" -> {ctype} (关键词: {keywords})")


def demo_2_fuzzy_matching():
    """演示 2：模糊匹配算法"""
    print("\n" + "=" * 60)
    print("演示 2：模糊匹配算法")
    print("=" * 60)

    test_cases = [
        ("确定", "确定"),
        ("确定", "确定并关闭"),
        ("确定", "取消"),
        ("OK", "确定"),
        ("保存", "保存文件"),
        ("文件", "文件(F)"),
        ("编辑", "编辑(E)"),
        ("用户名", "UserName"),
        ("密码", "Password"),
        ("登录", "Login"),
    ]

    print(f"\n测试 {len(test_cases)} 组匹配:\n")
    print(f"  {'搜索词':<12} {'目标文本':<15} {'匹配度':<8} {'匹配方式'}")
    print(f"  {'-'*12} {'-'*15} {'-'*8} {'-'*10}")

    for search, target in test_cases:
        result = _fuzzy_match_score(search, target)
        score = result["score"]
        method = result["match_type"]
        print(f"  {search:<12} {target:<15} {score:<8.2f} {method}")


def demo_3_smart_find_notepad():
    """演示 3：在记事本中智能查找控件"""
    print("\n" + "=" * 60)
    print("演示 3：在记事本中智能查找控件")
    print("=" * 60)

    print("\n[1] 启动记事本...")
    app = app_start("notepad.exe", backend="uia", timeout=10)
    win = app_top_window(app["app_id"])
    print(f"    窗口: {win.get('text', 'N/A')}")

    # 查找编辑区
    print("\n[2] 智能查找 \"文本编辑区\"...")
    result = smart_find("文本编辑区", wrapper_id=win["wrapper_id"], max_results=5)
    print(f"    找到 {result['matches_found']} 个匹配")
    for m in result["matches"][:3]:
        print(f"      - {m['text'][:30]:<32} ({m['control_type']}) score={m['score']}")
    print(f"    最佳匹配 wrapper_id: {result.get('best_match_wrapper_id', 'N/A')}")

    # 查找菜单栏
    print("\n[3] 智能查找 \"文件菜单\"...")
    result = smart_find("文件菜单", wrapper_id=win["wrapper_id"], max_results=5)
    print(f"    找到 {result['matches_found']} 个匹配")
    for m in result["matches"][:3]:
        print(f"      - {m['text'][:30]:<32} ({m['control_type']}) score={m['score']}")

    # 查找状态栏
    print("\n[4] 智能查找 \"状态栏\"...")
    result = smart_find("状态栏", wrapper_id=win["wrapper_id"], max_results=5)
    print(f"    找到 {result['matches_found']} 个匹配")
    for m in result["matches"][:3]:
        print(f"      - {m['text'][:30]:<32} ({m['control_type']}) score={m['score']}")

    print("\n演示 3 完成！")


def demo_4_search_depth():
    """演示 4：搜索深度对比"""
    print("\n" + "=" * 60)
    print("演示 4：搜索深度对比")
    print("=" * 60)

    # 使用桌面作为搜索范围
    print("\n在桌面范围内搜索 \"按钮\"，对比不同搜索深度:\n")

    for depth in [1, 2, 3]:
        result = smart_find("按钮", search_depth=depth, max_results=10)
        print(f"  深度={depth}: 扫描 {result.get('elements_scanned', 0)} 个元素, "
              f"找到 {result['matches_found']} 个匹配")


def demo_5_best_match_auto_register():
    """演示 5：最佳匹配自动注册"""
    print("\n" + "=" * 60)
    print("演示 5：最佳匹配自动注册为会话")
    print("=" * 60)

    print("\n[1] 启动记事本...")
    app = app_start("notepad.exe", backend="uia", timeout=10)
    win = app_top_window(app["app_id"])

    print("\n[2] 智能查找编辑区，最佳匹配会自动注册...")
    result = smart_find("文本编辑区", wrapper_id=win["wrapper_id"], max_results=3)

    best_id = result.get("best_match_wrapper_id")
    if best_id:
        print(f"    最佳匹配已注册: {best_id}")
        print(f"    可以直接用于后续操作，例如:")
        print(f"      control_type_text('{best_id}', 'Hello')")
        print(f"      control_get_text('{best_id}')")
    else:
        print("    未找到匹配")

    print("\n演示 5 完成！")


def main():
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 13 + "SmartLocator 智能元素定位演示" + " " * 13 + "║")
    print("╚" + "═" * 58 + "╝")

    # 纯算法演示（不需要 GUI）
    demo_1_control_type_detection()
    demo_2_fuzzy_matching()

    # 需要 GUI 的演示
    if "--no-gui" not in sys.argv:
        try:
            demo_3_smart_find_notepad()
            demo_4_search_depth()
            demo_5_best_match_auto_register()
        except Exception as e:
            print(f"\n⚠️  GUI 演示出错: {e}")
            print("    可以使用 --no-gui 参数跳过 GUI 演示")
    else:
        print("\n（已跳过 GUI 演示）")

    # 清理
    try:
        from pywinauto_wrapper import close_all_sessions
        close_all_sessions()
    except Exception:
        pass

    print("\n所有演示完成！")


if __name__ == "__main__":
    main()
