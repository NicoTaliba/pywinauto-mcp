#!/usr/bin/env python
"""
PyWinAuto MCP — Environment Self-Check Script

Verifies that all dependencies are installed and the MCP server can start.
Run: python scripts/self_check.py
"""

import sys
import os
import importlib
import json
from datetime import datetime
from typing import Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)


def check_dependency(name: str, import_name: Optional[str] = None) -> dict:
    """Check if a dependency is installed and return version info."""
    import_name = import_name or name
    result = {"name": name, "installed": False, "version": "unknown"}
    try:
        mod = importlib.import_module(import_name)
        result["installed"] = True
        result["version"] = getattr(mod, "__version__", "unknown")
        if result["version"] == "unknown" and hasattr(mod, "version"):
            result["version"] = str(mod.version)
    except ImportError as e:
        result["error"] = str(e)
    return result


def check_python_version() -> dict:
    """Check Python version compatibility."""
    info = sys.version_info
    ok = info.major >= 3 and info.minor >= 10
    return {
        "version": f"{info.major}.{info.minor}.{info.micro}",
        "required": ">= 3.10",
        "ok": ok,
    }


def check_platform() -> dict:
    """Check if running on Windows."""
    import platform
    system = platform.system()
    return {
        "system": system,
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "ok": system == "Windows",
    }


def check_wrapper_import() -> dict:
    """Check if the wrapper module imports correctly."""
    try:
        import pywinauto_wrapper as pw
        return {
            "ok": True,
            "version": getattr(pw, "VERSION", "unknown"),
            "total_functions": len(pw.ALL_FUNCTIONS),
            "total_workflows": len(pw.WORKFLOWS),
            "executable_workflows": sum(1 for w in pw.WORKFLOWS.values() if w["executable"]),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": sys.exc_info()}


def check_mcp_server_import() -> dict:
    """Check if the MCP server module imports correctly."""
    try:
        import mcp_server
        return {
            "ok": True,
            "tool_registry_size": len(mcp_server.TOOL_REGISTRY),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_health() -> dict:
    """Run the wrapper's health check."""
    try:
        import pywinauto_wrapper as pw
        return pw.health_check()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_basic_operations() -> dict:
    """Run basic non-GUI operations to verify functionality."""
    results = {}
    try:
        import pywinauto_wrapper as pw

        # System info
        results["sysinfo"] = {
            "os_arch": pw.sysinfo_os_arch(),
            "is_x64_os": pw.sysinfo_is_x64_os(),
            "is_x64_python": pw.sysinfo_is_x64_python(),
            "ok": True,
        }

        # Timings
        timings = pw.timings_get()
        results["timings"] = {"keys": len(timings), "ok": True}

        # Clipboard
        pw.clipboard_set_data("pywinauto-mcp self-check")
        clipboard_text = pw.clipboard_get_data()
        results["clipboard"] = {
            "roundtrip_ok": clipboard_text == "pywinauto-mcp self-check",
            "ok": True,
        }

        # Find windows
        windows = pw.find_windows()
        results["find_windows"] = {"count": len(windows), "ok": len(windows) > 0}

        # Workflow list
        wf = pw.workflow_list()
        results["workflows"] = {"count": wf["count"], "ok": wf["count"] == 100}

    except Exception as e:
        results["error"] = str(e)
        results["ok"] = False

    return results


def main():
    """Run all self-checks and print a report."""
    print("=" * 70)
    print("  PyWinAuto MCP — Environment Self-Check")
    print(f"  Date: {datetime.now().isoformat()}")
    print("=" * 70)
    print()

    all_ok = True
    sections = []

    # 1. Python
    print("[1/7] Python Version")
    py = check_python_version()
    print(f"  Version: {py['version']} (required: {py['required']})")
    print(f"  Status: {'OK' if py['ok'] else 'FAIL'}")
    all_ok = all_ok and py["ok"]
    sections.append(("Python", py))
    print()

    # 2. Platform
    print("[2/7] Platform")
    plat = check_platform()
    print(f"  System: {plat['system']} {plat['release']} ({plat['machine']})")
    print(f"  Status: {'OK' if plat['ok'] else 'FAIL'}")
    all_ok = all_ok and plat["ok"]
    sections.append(("Platform", plat))
    print()

    # 3. Dependencies
    print("[3/7] Dependencies")
    deps = [
        ("pywinauto", "pywinauto"),
        ("fastmcp", "fastmcp"),
        ("pywin32", "win32api"),
        ("comtypes", "comtypes"),
        ("pydantic", "pydantic"),
        ("six", "six"),
    ]
    for name, import_name in deps:
        dep = check_dependency(name, import_name)
        status = "OK" if dep["installed"] else "MISSING"
        print(f"  {name:15s} {status:8s} v{dep['version']}")
        if not dep["installed"]:
            all_ok = False
    sections.append(("Dependencies", "checked"))
    print()

    # 4. Wrapper import
    print("[4/7] Wrapper Module")
    wrapper = check_wrapper_import()
    if wrapper["ok"]:
        print(f"  Version: {wrapper['version']}")
        print(f"  Functions: {wrapper['total_functions']}")
        print(f"  Workflows: {wrapper['total_workflows']} ({wrapper['executable_workflows']} executable)")
        print(f"  Status: OK")
    else:
        print(f"  Status: FAIL - {wrapper['error']}")
        all_ok = False
    sections.append(("Wrapper", wrapper))
    print()

    # 5. MCP server import
    print("[5/7] MCP Server Module")
    server = check_mcp_server_import()
    if server["ok"]:
        print(f"  Tool registry: {server['tool_registry_size']} tools")
        print(f"  Status: OK")
    else:
        print(f"  Status: FAIL - {server['error']}")
        all_ok = False
    sections.append(("MCP Server", server))
    print()

    # 6. Health check
    print("[6/7] Health Check")
    health = check_health()
    print(f"  Overall: {health.get('status', 'unknown')}")
    print(f"  All OK: {health.get('all_ok', False)}")
    for check_name, check_result in health.get("checks", {}).items():
        status = "OK" if check_result.get("ok") else "FAIL"
        print(f"    {check_name:20s} {status}")
        if not check_result.get("ok"):
            all_ok = False
    sections.append(("Health", health))
    print()

    # 7. Basic operations
    print("[7/7] Basic Operations")
    ops = check_basic_operations()
    for op_name, op_result in ops.items():
        if isinstance(op_result, dict):
            status = "OK" if op_result.get("ok") else "FAIL"
            detail = ", ".join(f"{k}={v}" for k, v in op_result.items() if k != "ok")
            print(f"  {op_name:20s} {status:8s} {detail}")
            if not op_result.get("ok"):
                all_ok = False
    sections.append(("Operations", ops))
    print()

    # Summary
    print("=" * 70)
    if all_ok:
        print("  RESULT: ALL CHECKS PASSED")
        print("  The pywinauto-mcp skill is ready to use.")
    else:
        print("  RESULT: SOME CHECKS FAILED")
        print("  Please review the failures above and install missing dependencies.")
    print("=" * 70)

    # Write JSON report
    report_path = os.path.join(_SCRIPT_DIR, "..", "self_check_report.json")
    report = {
        "timestamp": datetime.now().isoformat(),
        "all_ok": all_ok,
        "sections": {name: result for name, result in sections},
    }
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport written to: {os.path.abspath(report_path)}")
    except Exception as e:
        print(f"\nCould not write report: {e}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
