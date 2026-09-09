"""
PyWinAuto MCP — 软件安装与管理示例

演示如何使用 system_* 工具进行软件下载、安装、卸载和检查。
包括 WF101 下载安装包并安装（检查已安装则卸载重装）工作流的完整实现。

运行方式：
    python docs/examples/install_package_demo.py

注意：
- 部分操作需要管理员权限
- 安装/卸载操作会修改系统，请谨慎运行
- 默认使用 --dry-run 模式，只演示不实际安装
"""

import sys
import os
import json
import time

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPT_DIR))

from pywinauto_wrapper import (
    system_download_file,
    system_run_command,
    system_process_running,
    system_file_exists,
    system_get_installed_software,
    system_find_software,
    system_uninstall_software,
    system_install_package,
    system_download_and_install,
)


def demo_1_check_installed_software():
    """演示 1：检查已安装软件列表"""
    print("=" * 60)
    print("演示 1：检查已安装软件")
    print("=" * 60)

    print("\n[1] 获取全部已安装软件...")
    result = system_get_installed_software()
    if result["status"] == "success":
        print(f"    共找到 {result['count']} 个已安装软件")
        print(f"\n    前 10 个:")
        for s in result["software"][:10]:
            version = s.get("version", "")
            publisher = s.get("publisher", "")
            print(f"      - {s['name']:<40} v{version:<15} {publisher}")
    else:
        print(f"    获取失败: {result.get('error')}")

    print("\n[2] 搜索特定软件...")
    search_terms = ["Chrome", "Python", "7-Zip", "Notepad", "Firefox"]
    for term in search_terms:
        result = system_find_software(term)
        if result["status"] == "success":
            status = "✓ 已安装" if result["found"] else "✗ 未安装"
            print(f"    {term:<15} {status} (匹配 {result['match_count']} 个)")
            if result["found"]:
                for m in result["matches"][:2]:
                    print(f"        - {m['name']} v{m.get('version', '')}")


def demo_2_file_and_process_check():
    """演示 2：文件存在检查和进程检查"""
    print("\n" + "=" * 60)
    print("演示 2：文件和进程检查")
    print("=" * 60)

    print("\n[1] 检查文件是否存在...")
    test_paths = [
        r"C:\Windows\notepad.exe",
        r"C:\Windows\System32\calc.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\nonexistent\file.exe",
    ]
    for path in test_paths:
        result = system_file_exists(path)
        status = "✓ 存在" if result.get("exists") else "✗ 不存在"
        size = f" ({result.get('size_mb', 0)}MB)" if result.get("exists") else ""
        print(f"    {status} {path}{size}")

    print("\n[2] 检查进程是否运行...")
    test_processes = ["notepad.exe", "chrome.exe", "explorer.exe", "nonexistent.exe"]
    for proc in test_processes:
        result = system_process_running(proc)
        if result["status"] == "success":
            status = "✓ 运行中" if result["running"] else "✗ 未运行"
            count = f" ({result['process_count']} 个实例)" if result["running"] else ""
            print(f"    {status} {proc}{count}")


def demo_3_run_command():
    """演示 3：执行系统命令"""
    print("\n" + "=" * 60)
    print("演示 3：执行系统命令")
    print("=" * 60)

    print("\n[1] 执行简单命令...")
    commands = [
        ("echo Hello World", "测试 echo"),
        ("ver", "Windows 版本"),
        ("hostname", "主机名"),
        ("whoami", "当前用户"),
    ]

    for cmd, desc in commands:
        result = system_run_command(cmd, timeout=10)
        if result["status"] == "success":
            output = (result.get("stdout") or "").strip()[:60]
            print(f"    ✓ {desc}: {output}")
        else:
            print(f"    ✗ {desc}: {result.get('error', 'Failed')}")

    print("\n[2] 执行带超时的命令...")
    result = system_run_command("timeout /t 2", timeout=5)
    print(f"    超时命令: return_code={result.get('return_code')}, "
          f"timed_out={result.get('timed_out')}, elapsed={result.get('elapsed_time')}s")


def demo_4_download_file():
    """演示 4：下载文件"""
    print("\n" + "=" * 60)
    print("演示 4：下载文件")
    print("=" * 60)

    # 使用一个小文件做演示（Python 官方的 get-pip.py 太大，用一个小测试文件）
    test_url = "https://www.python.org/favicon.ico"
    save_path = os.path.join(os.environ.get("TEMP", "."), "python_favicon.ico")

    print(f"\n[1] 下载测试文件...")
    print(f"    URL: {test_url}")
    print(f"    保存到: {save_path}")

    result = system_download_file(test_url, save_path, timeout=30)

    if result["status"] == "success":
        print(f"    ✓ 下载成功")
        print(f"    文件大小: {result['file_size']} bytes ({result['file_size_mb']} MB)")
        print(f"    下载耗时: {result['download_time']}s")
        print(f"    下载速度: {result['speed_kbps']} KB/s")
    else:
        print(f"    ✗ 下载失败: {result.get('error')}")

    # 验证文件
    check = system_file_exists(save_path)
    print(f"\n[2] 验证文件: {'✓ 存在' if check.get('exists') else '✗ 不存在'}")


def workflow_wf101_download_and_install(url, software_name, save_path=None,
                                          install_args="", silent=True,
                                          timeout=600, skip_uninstall=False,
                                          dry_run=True):
    """WF101: 下载安装包并安装（检查已安装则卸载重装）

    完整实现 WF101 工作流的所有步骤。
    """
    print(f"\n{'='*60}")
    print(f"WF101: 下载安装包并安装")
    print(f"{'='*60}")
    print(f"  软件名称: {software_name}")
    print(f"  下载 URL: {url}")
    print(f"  静默模式: {silent}")
    print(f"  跳过卸载: {skip_uninstall}")
    print(f"  演示模式: {dry_run}")
    print()

    report = {
        "software_name": software_name,
        "url": url,
        "was_installed": False,
        "previous_version": None,
        "uninstall": None,
        "download": None,
        "install": None,
        "new_version": None,
        "status": "pending",
    }

    start_time = time.time()

    # 步骤 1: 检查是否已安装
    print("[步骤 1] 检查软件是否已安装...")
    check_result = system_find_software(software_name)
    if check_result["status"] == "success" and check_result["found"]:
        report["was_installed"] = True
        match = check_result["matches"][0]
        report["previous_version"] = match.get("version", "")
        print(f"  ✓ 已安装: {match['name']} v{match.get('version', '')}")
        print(f"    发布者: {match.get('publisher', '')}")
        print(f"    安装路径: {match.get('install_location', '')}")
    else:
        print(f"  ✗ 未安装，将进行全新安装")

    # 步骤 2: 卸载（如果已安装且不跳过）
    if report["was_installed"] and not skip_uninstall:
        print(f"\n[步骤 2] 卸载旧版本...")
        if dry_run:
            print(f"  [演示] 将执行卸载: {software_name}")
            report["uninstall"] = {"status": "skipped (dry_run)", "return_code": 0}
        else:
            uninstall_result = system_uninstall_software(software_name, silent=silent, timeout=timeout // 2)
            report["uninstall"] = uninstall_result
            if uninstall_result["status"] == "success":
                print(f"  ✓ 卸载成功 (return_code={uninstall_result.get('return_code')})")
            else:
                print(f"  ✗ 卸载失败: {uninstall_result.get('error', 'Unknown')}")
            print(f"  等待 3 秒确保文件释放...")
            time.sleep(3)
    elif report["was_installed"] and skip_uninstall:
        print(f"\n[步骤 2] 跳过卸载（直接安装/升级）")
    else:
        print(f"\n[步骤 2] 无需卸载（全新安装）")

    # 步骤 3: 下载安装包
    print(f"\n[步骤 3] 下载安装包...")
    if dry_run:
        print(f"  [演示] 将下载: {url}")
        report["download"] = {"status": "skipped (dry_run)", "saved_path": save_path or "<temp>"}
    else:
        download_result = system_download_file(url, save_path, timeout=min(timeout, 300))
        report["download"] = download_result
        if download_result["status"] == "success":
            print(f"  ✓ 下载成功")
            print(f"    保存路径: {download_result['saved_path']}")
            print(f"    文件大小: {download_result['file_size_mb']} MB")
            print(f"    下载耗时: {download_result['download_time']}s")
        else:
            print(f"  ✗ 下载失败: {download_result.get('error')}")
            report["status"] = "error"
            report["total_time"] = round(time.time() - start_time, 2)
            return report

    # 步骤 4: 安装
    print(f"\n[步骤 4] 执行安装...")
    if dry_run:
        print(f"  [演示] 将执行安装")
        report["install"] = {"status": "skipped (dry_run)", "return_code": 0}
    else:
        installer_path = report["download"]["saved_path"]
        install_result = system_install_package(installer_path, args=install_args,
                                                   timeout=timeout, silent=silent)
        report["install"] = install_result
        if install_result["status"] == "success":
            print(f"  ✓ 安装成功 (return_code={install_result.get('return_code')})")
        else:
            print(f"  ✗ 安装失败: {install_result.get('error', 'Unknown')}")
            print(f"    stderr: {(install_result.get('stderr') or '')[:200]}")

    # 步骤 5: 验证安装
    print(f"\n[步骤 5] 验证安装...")
    verify_result = system_find_software(software_name)
    if verify_result["status"] == "success" and verify_result["found"]:
        match = verify_result["matches"][0]
        report["new_version"] = match.get("version", "")
        print(f"  ✓ 验证成功: {match['name']} v{match.get('version', '')}")
        report["status"] = "success"
    else:
        print(f"  ⚠ 验证失败: 未在已安装软件列表中找到 '{software_name}'")
        print(f"    （可能是安装程序未注册到系统，或需要手动确认安装）")
        if report["install"] and report["install"].get("status") == "success":
            report["status"] = "success (unverified)"
        else:
            report["status"] = "error"

    report["total_time"] = round(time.time() - start_time, 2)

    print(f"\n{'='*60}")
    print(f"执行报告")
    print(f"{'='*60}")
    print(f"  状态: {report['status']}")
    print(f"  原已安装: {report['was_installed']} (v{report['previous_version'] or 'N/A'})")
    print(f"  新版本: v{report['new_version'] or 'N/A'}")
    print(f"  总耗时: {report['total_time']}s")
    print(f"{'='*60}")

    return report


def demo_5_wf101_dry_run():
    """演示 5：WF101 工作流演示（dry-run 模式，不实际安装）"""
    print("\n" + "=" * 60)
    print("演示 5：WF101 下载安装包并安装（演示模式）")
    print("=" * 60)

    # 使用 7-Zip 作为演示（常见软件，安装包较小）
    # 注意：这是 dry-run 模式，不会实际下载和安装
    result = workflow_wf101_download_and_install(
        url="https://www.7-zip.org/a/7z2301-x64.exe",
        software_name="7-Zip",
        silent=True,
        timeout=300,
        dry_run=True  # 演示模式
    )

    print(f"\n提示: 要实际执行，请设置 dry_run=False")
    print(f"  示例: workflow_wf101_download_and_install(url, name, dry_run=False)")


def demo_6_download_and_install_tool():
    """演示 6：使用 system_download_and_install 一键工具"""
    print("\n" + "=" * 60)
    print("演示 6：一键下载并安装（system_download_and_install）")
    print("=" * 60)

    print("\n这是一个封装好的工具，自动完成下载+安装:")
    print("  result = system_download_and_install(url, save_path, install_args, timeout, silent)")
    print()
    print("返回结果包含:")
    print("  - download: 下载结果（路径、大小、耗时）")
    print("  - install: 安装结果（返回码、输出）")
    print("  - status: 总体状态")
    print()
    print("注意：实际运行需要管理员权限，且会修改系统。")
    print("此处不实际执行，请在测试环境中使用。")


def main():
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "软件安装与管理示例 (WF101-WF105)" + " " * 10 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    print("可用工具:")
    print("  - system_download_file: 下载文件")
    print("  - system_run_command: 执行系统命令")
    print("  - system_process_running: 检查进程")
    print("  - system_file_exists: 检查文件")
    print("  - system_get_installed_software: 获取已安装软件列表")
    print("  - system_find_software: 搜索已安装软件")
    print("  - system_uninstall_software: 卸载软件")
    print("  - system_install_package: 安装软件包")
    print("  - system_download_and_install: 一键下载并安装")
    print()

    # 安全的演示（不修改系统）
    demo_1_check_installed_software()
    demo_2_file_and_process_check()
    demo_3_run_command()
    demo_4_download_file()

    # WF101 完整工作流演示（dry-run）
    demo_5_wf101_dry_run()
    demo_6_download_and_install_tool()

    print("\n" + "=" * 60)
    print("所有演示完成！")
    print("=" * 60)
    print()
    print("安全提示:")
    print("  1. 安装/卸载操作需要管理员权限")
    print("  2. 请在测试环境中验证后再在生产环境使用")
    print("  3. 静默安装标志并非所有安装包都支持")
    print("  4. 杀毒软件可能拦截安装程序")
    print("  5. 大型软件安装请适当增加 timeout")


if __name__ == "__main__":
    main()
