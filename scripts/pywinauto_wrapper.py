"""
PyWinAuto Comprehensive API Wrapper.

Wraps ALL public pywinauto APIs into a clean, JSON-serializable interface
with session management for Application and Window/Control objects.

Modules covered:
  - pywinauto.application (Application, WindowSpecification)
  - pywinauto.keyboard (send_keys, key press/release)
  - pywinauto.mouse (click, double_click, move, press, release, scroll, drag)
  - pywinauto.clipboard (get_data, set_data, empty)
  - pywinauto.timings (Timings config, wait_until, wait_until_passes)
  - pywinauto.sysinfo (is_x64_python, is_x64_os, os_arch, python_bitness)
  - pywinauto.findwindows (find_windows, find_elements, enumerate_windows)
  - pywinauto.taskbar (taskbar operations)
  - pywinauto.base_wrapper (BaseWrapper methods)
  - pywinauto.controls.hwndwrapper (HwndWrapper)
  - pywinauto.controls.uiawrapper (UIAWrapper)
  - pywinauto.controls.common_controls (all common control wrappers)
  - pywinauto.controls.win32_controls (win32 control wrappers)
  - pywinauto.controls.uia_controls (UIA control wrappers)
  - pywinauto.controls.menuwrapper (MenuWrapper, MenuItemWrapper)
"""

from __future__ import annotations

import inspect
import json
import logging
import platform
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Version & capabilities
# ---------------------------------------------------------------------------

VERSION = "2.0.0"
BUILD_DATE = "2026-09-09"

# ---------------------------------------------------------------------------
# Thread-safe session registry with TTL
# ---------------------------------------------------------------------------

_session_lock = threading.RLock()
_app_sessions: dict[str, dict[str, Any]] = {}
_wrapper_sessions: dict[str, dict[str, Any]] = {}
_SESSION_TTL = timedelta(hours=2)  # Auto-expire sessions after 2 hours
_call_stats: dict[str, dict[str, Any]] = {"total_calls": 0, "errors": 0, "by_tool": {}}


def _new_app_id() -> str:
    return f"app_{uuid.uuid4().hex[:12]}"


def _new_wrapper_id() -> str:
    return f"ctrl_{uuid.uuid4().hex[:12]}"


def _register_app(app: Any) -> str:
    app_id = _new_app_id()
    with _session_lock:
        _app_sessions[app_id] = {"app": app, "created": datetime.now(), "last_used": datetime.now()}
    return app_id


def _get_app(app_id: str) -> Any:
    with _session_lock:
        if app_id not in _app_sessions:
            raise KeyError(f"Application session '{app_id}' not found. "
                           f"Active: {list(_app_sessions.keys())}")
        entry = _app_sessions[app_id]
        entry["last_used"] = datetime.now()
        return entry["app"]


def _register_wrapper(wrapper: Any) -> str:
    wid = _new_wrapper_id()
    with _session_lock:
        _wrapper_sessions[wid] = {"wrapper": wrapper, "created": datetime.now(), "last_used": datetime.now()}
    return wid


def _get_wrapper(wrapper_id: str) -> Any:
    with _session_lock:
        if wrapper_id not in _wrapper_sessions:
            raise KeyError(f"Wrapper session '{wrapper_id}' not found. "
                           f"Active: {list(_wrapper_sessions.keys())}")
        entry = _wrapper_sessions[wrapper_id]
        entry["last_used"] = datetime.now()
        return entry["wrapper"]


def _release_wrapper(wrapper_id: str) -> None:
    with _session_lock:
        _wrapper_sessions.pop(wrapper_id, None)


def _cleanup_expired_sessions() -> dict[str, Any]:
    """Remove sessions older than TTL. Returns counts of removed sessions."""
    now = datetime.now()
    removed_apps = []
    removed_wrappers = []
    with _session_lock:
        for app_id in list(_app_sessions.keys()):
            if now - _app_sessions[app_id]["last_used"] > _SESSION_TTL:
                removed_apps.append(app_id)
                del _app_sessions[app_id]
        for wid in list(_wrapper_sessions.keys()):
            if now - _wrapper_sessions[wid]["last_used"] > _SESSION_TTL:
                removed_wrappers.append(wid)
                del _wrapper_sessions[wid]
    return {"removed_apps": removed_apps, "removed_wrappers": removed_wrappers}


def _record_call(tool_name: str, success: bool, duration: float) -> None:
    """Record tool call statistics."""
    with _session_lock:
        _call_stats["total_calls"] += 1
        if not success:
            _call_stats["errors"] += 1
        if tool_name not in _call_stats["by_tool"]:
            _call_stats["by_tool"][tool_name] = {"calls": 0, "errors": 0, "total_time": 0}
        stat = _call_stats["by_tool"][tool_name]
        stat["calls"] += 1
        if not success:
            stat["errors"] += 1
        stat["total_time"] += duration


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

_VALID_BACKENDS = {"uia", "win32"}
_VALID_MOUSE_BUTTONS = {"left", "right", "middle"}
_VALID_SCROLL_DIRECTIONS = {"up", "down", "left", "right"}
_VALID_WAIT_STATES = {"exists", "visible", "enabled", "ready", "active", "not exists", "not visible"}


def _validate_backend(backend: str) -> str:
    if backend not in _VALID_BACKENDS:
        raise ValueError(f"Invalid backend '{backend}'. Must be one of: {_VALID_BACKENDS}")
    return backend


def _validate_mouse_button(button: str) -> str:
    if button not in _VALID_MOUSE_BUTTONS:
        raise ValueError(f"Invalid mouse button '{button}'. Must be one of: {_VALID_MOUSE_BUTTONS}")
    return button


def _validate_scroll_direction(direction: str) -> str:
    if direction not in _VALID_SCROLL_DIRECTIONS:
        raise ValueError(f"Invalid scroll direction '{direction}'. Must be one of: {_VALID_SCROLL_DIRECTIONS}")
    return direction


def _validate_nonempty(value: str, name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"Parameter '{name}' must be a non-empty string")
    return value


def _validate_positive(value: float, name: str) -> float:
    if value <= 0:
        raise ValueError(f"Parameter '{name}' must be positive, got {value}")
    return value


def _validate_timeout(timeout: Optional[float]) -> Optional[float]:
    if timeout is not None and timeout <= 0:
        raise ValueError(f"Timeout must be positive, got {timeout}")
    if timeout is not None and timeout > 300:
        logger.warning("Timeout %.1fs exceeds 300s recommendation", timeout)
    return timeout


def _validate_workflow_id(wf_id: str) -> str:
    if not re.match(r"^WF\d{3}$", wf_id):
        raise ValueError(f"Invalid workflow ID '{wf_id}'. Expected format: WF001-WF100")
    return wf_id


# ---------------------------------------------------------------------------
# Retry & timeout helpers
# ---------------------------------------------------------------------------

class OperationTimeoutError(Exception):
    """Raised when an operation exceeds its timeout."""
    pass


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, message: str, attempts: int, last_error: Optional[Exception] = None):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


def _with_retry(func: Callable[..., Any], retries: int = 3, delay: float = 0.5,
                 backoff: float = 2.0, retry_on: tuple[type, ...] = (Exception,),
                 *args: Any, **kwargs: Any) -> Any:
    """Execute a function with exponential backoff retry.

    Args:
        func: Function to execute
        retries: Number of retry attempts (total attempts = retries + 1)
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        retry_on: Exception types that trigger a retry
    """
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            return func(*args, **kwargs)
        except retry_on as e:
            last_error = e
            if attempt < retries:
                wait = delay * (backoff ** attempt)
                logger.debug("Retry %d/%d for %s after %.2fs: %s",
                             attempt + 1, retries, func.__name__, wait, e)
                time.sleep(wait)
            else:
                logger.warning("Retry exhausted for %s after %d attempts: %s",
                               func.__name__, retries + 1, e)
    raise RetryExhaustedError(
        f"Function '{func.__name__}' failed after {retries + 1} attempts",
        attempts=retries + 1, last_error=last_error)


def _with_timeout(func: Callable[..., Any], timeout: float, *args: Any, **kwargs: Any) -> Any:
    """Execute a function with a timeout (uses threading for sync functions).

    Note: For pywinauto operations that may block, this provides a best-effort
    timeout. The thread may continue running after timeout but the caller gets control back.
    """
    result: dict[str, Any] = {}
    error: dict[str, Exception] = {}

    def target() -> None:
        try:
            result["value"] = func(*args, **kwargs)
        except Exception as e:
            error["value"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        raise OperationTimeoutError(f"Operation timed out after {timeout}s")
    if "value" in error:
        raise error["value"]
    return result.get("value")


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

def _classify_error(e: Exception) -> dict[str, Any]:
    """Classify an exception into a structured error with recovery suggestions."""
    error_type = type(e).__name__
    msg = str(e)
    suggestions: list[str] = []

    if "not found" in msg.lower() or "could not find" in msg.lower():
        category = "element_not_found"
        suggestions.extend([
            "检查定位条件是否正确（title/auto_id/control_type）",
            "使用 window_dump_tree 查看控件树结构",
            "增加超时时间或使用 window_wait 等待元素出现",
            "确认应用是否已启动且窗口可见",
        ])
    elif "timed out" in msg.lower() or "timeout" in msg.lower():
        category = "timeout"
        suggestions.extend([
            "增加 timeout 参数",
            "使用 timings_slow() 降低操作速度",
            "检查应用是否响应（CPU 使用率是否过高）",
        ])
    elif "element is not enabled" in msg.lower() or "disabled" in msg.lower():
        category = "element_disabled"
        suggestions.extend([
            "控件当前不可用，等待前置条件满足",
            "检查是否需要先勾选/填写其他字段",
        ])
    elif "element is not visible" in msg.lower():
        category = "element_not_visible"
        suggestions.extend([
            "控件不可见，可能需要先展开父容器或切换标签页",
            "滚动到控件可见位置",
        ])
    elif "session" in msg.lower() and "not found" in msg.lower():
        category = "session_expired"
        suggestions.extend([
            "会话已过期，重新执行 app_start/app_connect",
            "服务器重启后所有会话失效",
        ])
    elif "permission" in msg.lower() or "access denied" in msg.lower():
        category = "permission_denied"
        suggestions.extend([
            "目标应用需要管理员权限，以管理员身份运行 MCP 服务器",
            "UAC 弹窗需要手动确认",
        ])
    else:
        category = "unknown"
        suggestions.append("查看服务器日志获取详细错误信息")

    return {
        "error_type": error_type,
        "category": category,
        "message": msg,
        "suggestions": suggestions,
    }


def list_sessions() -> dict[str, Any]:
    """List all active application and wrapper sessions with metadata."""
    with _session_lock:
        apps = []
        for app_id, entry in _app_sessions.items():
            apps.append({
                "app_id": app_id,
                "created": entry["created"].isoformat(),
                "last_used": entry["last_used"].isoformat(),
                "age_seconds": (datetime.now() - entry["created"]).total_seconds(),
                "idle_seconds": (datetime.now() - entry["last_used"]).total_seconds(),
            })
        wrappers = []
        for wid, entry in _wrapper_sessions.items():
            wrappers.append({
                "wrapper_id": wid,
                "created": entry["created"].isoformat(),
                "last_used": entry["last_used"].isoformat(),
                "age_seconds": (datetime.now() - entry["created"]).total_seconds(),
                "idle_seconds": (datetime.now() - entry["last_used"]).total_seconds(),
            })
    return {"applications": apps, "wrappers": wrappers,
            "app_count": len(apps), "wrapper_count": len(wrappers)}


def close_session(app_id: str) -> dict[str, Any]:
    """Close an application session and release associated wrappers."""
    with _session_lock:
        entry = _app_sessions.pop(app_id, None)
        released = []
        for wid in list(_wrapper_sessions.keys()):
            released.append(wid)
            _wrapper_sessions.pop(wid, None)
    return {"closed": app_id, "found": entry is not None, "released_wrappers": released}


def close_all_sessions() -> dict[str, Any]:
    """Close all sessions."""
    with _session_lock:
        apps = list(_app_sessions.keys())
        wrappers = list(_wrapper_sessions.keys())
        _app_sessions.clear()
        _wrapper_sessions.clear()
    return {"closed_apps": apps, "released_wrappers": wrappers,
            "app_count": len(apps), "wrapper_count": len(wrappers)}


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _rect_to_dict(rect: Any) -> dict[str, Any]:
    return {
        "left": rect.left,
        "top": rect.top,
        "right": rect.right,
        "bottom": rect.bottom,
        "width": rect.width(),
        "height": rect.height(),
    }


def _safe_call(obj: Any, method: str, *args, **kwargs) -> Any:
    """Safely call a method on an object, returning result or error."""
    func = getattr(obj, method, None)
    if func is None:
        raise AttributeError(f"Object {type(obj).__name__} has no method '{method}'")
    return func(*args, **kwargs)


def _wrapper_info(wrapper: Any) -> dict[str, Any]:
    """Extract standard info from a wrapper object."""
    info: dict[str, Any] = {}
    try:
        info["class_name"] = wrapper.class_name()
    except Exception:
        pass
    try:
        info["text"] = wrapper.window_text()
    except Exception:
        pass
    try:
        info["control_id"] = wrapper.control_id()
    except Exception:
        pass
    try:
        info["process_id"] = wrapper.process_id()
    except Exception:
        pass
    try:
        info["is_visible"] = wrapper.is_visible()
    except Exception:
        pass
    try:
        info["is_enabled"] = wrapper.is_enabled()
    except Exception:
        pass
    try:
        info["handle"] = wrapper.handle
    except Exception:
        pass
    try:
        info["rect"] = _rect_to_dict(wrapper.rectangle())
    except Exception:
        pass
    try:
        if hasattr(wrapper, "automation_id"):
            info["automation_id"] = wrapper.automation_id()
    except Exception:
        pass
    try:
        if hasattr(wrapper, "element_info") and wrapper.element_info:
            ei = wrapper.element_info
            info["name"] = getattr(ei, "name", None)
            info["control_type"] = str(getattr(ei, "control_type", None))
    except Exception:
        pass
    info["wrapper_type"] = type(wrapper).__name__
    return info


# ===========================================================================
# 1. APPLICATION MANAGEMENT
# ===========================================================================

def app_start(cmd_line: str, backend: str = "uia", timeout: Optional[float] = None,
              work_dir: Optional[str] = None, wait_for_idle: bool = True) -> dict[str, Any]:
    """Start an application.

    Args:
        cmd_line: Command line to start (e.g. 'notepad.exe', 'calc.exe')
        backend: 'uia' or 'win32'
        timeout: Timeout for start
        work_dir: Working directory
        wait_for_idle: Whether to wait for idle after start

    Returns:
        Dict with app_id and basic info
    """
    from pywinauto.application import Application
    app = Application(backend=backend)
    kwargs: dict[str, Any] = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if work_dir is not None:
        kwargs["work_dir"] = work_dir
    kwargs["wait_for_idle"] = wait_for_idle
    app.start(cmd_line, **kwargs)
    app_id = _register_app(app)
    return {
        "app_id": app_id,
        "backend": backend,
        "cmd_line": cmd_line,
        "process_id": getattr(app, "process", None),
    }


def app_connect(backend: str = "uia", **kwargs: Any) -> dict[str, Any]:
    """Connect to an already running application.

    Provide exactly one of: process, handle, path, title, title_re,
    class_name, class_name_re, active_window.

    Args:
        backend: 'uia' or 'win32'
        **kwargs: Connection criteria (process=, handle=, path=, title=, etc.)

    Returns:
        Dict with app_id
    """
    from pywinauto.application import Application
    app = Application(backend=backend)
    app.connect(**kwargs)
    app_id = _register_app(app)
    return {
        "app_id": app_id,
        "backend": backend,
        "process_id": getattr(app, "process", None),
        "connected_via": list(kwargs.keys()),
    }


def app_kill(app_id: str, soft: bool = False) -> dict[str, Any]:
    """Kill the application.

    Args:
        app_id: Application session ID
        soft: If True, try to close gently first
    """
    app = _get_app(app_id)
    app.kill(soft=soft)
    return {"killed": app_id, "soft": soft}


def app_windows(app_id: str, **kwargs: Any) -> dict[str, Any]:
    """Return list of top-level windows of the application.

    Returns list of wrapper session IDs and their info.
    """
    app = _get_app(app_id)
    windows = app.windows(**kwargs)
    result = []
    for w in windows:
        wid = _register_wrapper(w)
        result.append({"wrapper_id": wid, **_wrapper_info(w)})
    return {"count": len(result), "windows": result}


def app_top_window(app_id: str) -> dict[str, Any]:
    """Return the current top window of the application."""
    app = _get_app(app_id)
    win_spec = app.top_window()
    wrapper = win_spec.wrapper_object()
    wid = _register_wrapper(wrapper)
    return {"wrapper_id": wid, **_wrapper_info(wrapper)}


def app_active_window(app_id: str) -> dict[str, Any]:
    """Return the active window of the application."""
    app = _get_app(app_id)
    win_spec = app.active()
    wrapper = win_spec.wrapper_object()
    wid = _register_wrapper(wrapper)
    return {"wrapper_id": wid, **_wrapper_info(wrapper)}


def app_window(app_id: str, **kwargs: Any) -> dict[str, Any]:
    """Find a window by criteria and return a wrapper session.

    Criteria: title, title_re, class_name, class_name_re, control_type,
    auto_id, control_id, handle, found_index, etc.
    """
    app = _get_app(app_id)
    win_spec = app.window(**kwargs)
    wrapper = win_spec.wrapper_object()
    wid = _register_wrapper(wrapper)
    return {"wrapper_id": wid, **_wrapper_info(wrapper)}


def app_cpu_usage(app_id: str, interval: Optional[float] = None) -> dict[str, Any]:
    """Return CPU usage percent."""
    app = _get_app(app_id)
    usage = app.cpu_usage(interval=interval) if interval else app.cpu_usage()
    return {"cpu_usage_percent": usage}


def app_is64bit(app_id: str) -> dict[str, Any]:
    """Return True if the process is 64-bit."""
    app = _get_app(app_id)
    return {"is_64bit": app.is64bit()}


def app_is_process_running(app_id: str) -> dict[str, Any]:
    """Check if the process is running."""
    app = _get_app(app_id)
    return {"is_running": app.is_process_running()}


def app_wait_cpu_usage_lower(app_id: str, threshold: float = 2.5,
                               timeout: Optional[float] = None,
                               usage_interval: Optional[float] = None) -> dict[str, Any]:
    """Wait until CPU usage is below threshold."""
    app = _get_app(app_id)
    kwargs: dict[str, Any] = {"threshold": threshold}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if usage_interval is not None:
        kwargs["usage_interval"] = usage_interval
    app.wait_cpu_usage_lower(**kwargs)
    return {"waited": True, "threshold": threshold}


def app_wait_for_process_exit(app_id: str, timeout: Optional[float] = None,
                                retry_interval: Optional[float] = None) -> dict[str, Any]:
    """Wait for the process to exit."""
    app = _get_app(app_id)
    kwargs: dict[str, Any] = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if retry_interval is not None:
        kwargs["retry_interval"] = retry_interval
    app.wait_for_process_exit(**kwargs)
    return {"process_exited": True}


# ===========================================================================
# 2. WINDOW / CONTROL SPECIFICATION & RESOLUTION
# ===========================================================================

def window_find(app_id: Optional[str] = None, **kwargs: Any) -> dict[str, Any]:
    """Find a window/control on the desktop or within an app.

    If app_id is provided, searches within that application.
    Otherwise searches the whole desktop.

    Criteria: title, title_re, class_name, class_name_re, control_type,
    auto_id, control_id, handle, found_index, process, etc.
    """
    if app_id:
        return app_window(app_id, **kwargs)
    from pywinauto import Desktop
    backend = kwargs.pop("backend", "uia")
    desktop = Desktop(backend=backend)
    win_spec = desktop.window(**kwargs)
    wrapper = win_spec.wrapper_object()
    wid = _register_wrapper(wrapper)
    return {"wrapper_id": wid, **_wrapper_info(wrapper)}


def window_exists(wrapper_id: str, timeout: Optional[float] = None,
                  retry_interval: Optional[float] = None) -> dict[str, Any]:
    """Check if a window/control exists (via its parent WindowSpecification).

    Note: This works on wrapper sessions by re-checking the underlying element.
    """
    wrapper = _get_wrapper(wrapper_id)
    try:
        # Re-resolve to check existence
        wrapper.element_info
        exists = True
    except Exception:
        exists = False
    return {"exists": exists}


def window_wait(wrapper_id: str, wait_for: str = "visible",
                timeout: Optional[float] = None,
                retry_interval: Optional[float] = None) -> dict[str, Any]:
    """Wait for the window to be in a particular state.

    States: 'exists', 'visible', 'enabled', 'ready' (visible + enabled).
    Combine with space: 'visible enabled'.
    """
    wrapper = _get_wrapper(wrapper_id)
    # We need a WindowSpecification to call wait().
    # Re-create one from the wrapper's element info.
    from pywinauto import Desktop
    backend = "uia" if "uia" in type(wrapper).__module__ else "win32"
    desktop = Desktop(backend=backend)
    handle = getattr(wrapper, "handle", None)
    if handle:
        win_spec = desktop.window(handle=handle)
    else:
        win_spec = desktop.window(title=wrapper.window_text())
    kwargs: dict[str, Any] = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if retry_interval is not None:
        kwargs["retry_interval"] = retry_interval
    win_spec.wait(wait_for, **kwargs)
    return {"waited_for": wait_for, "result": "success"}


def window_dump_tree(wrapper_id: str, depth: Optional[int] = None) -> dict[str, Any]:
    """Dump the control tree identifiers."""
    wrapper = _get_wrapper(wrapper_id)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        wrapper.dump_tree(depth=depth)
    return {"dump_tree": buf.getvalue()}


def window_print_control_identifiers(wrapper_id: str, depth: Optional[int] = None) -> dict[str, Any]:
    """Print control identifiers (same as dump_tree)."""
    return window_dump_tree(wrapper_id, depth=depth)


def window_get_wrapper(wrapper_id: str) -> dict[str, Any]:
    """Get full info about a wrapper session."""
    wrapper = _get_wrapper(wrapper_id)
    return _wrapper_info(wrapper)


def window_release(wrapper_id: str) -> dict[str, Any]:
    """Release a wrapper session."""
    _release_wrapper(wrapper_id)
    return {"released": wrapper_id}


# ===========================================================================
# 3. CONTROL ACTIONS (BaseWrapper + HwndWrapper + UIAWrapper methods)
# ===========================================================================

def control_click(wrapper_id: str, button: str = "left",
                  coords: Optional[tuple[int, int]] = None,
                  double: bool = False) -> dict[str, Any]:
    """Click on the control.

    Args:
        wrapper_id: Wrapper session ID
        button: 'left', 'right', 'middle'
        coords: (x, y) relative to control, or None for center
        double: If True, double-click
    """
    wrapper = _get_wrapper(wrapper_id)
    kwargs: dict[str, Any] = {"button": button}
    if coords:
        kwargs["coords"] = coords
    if double:
        wrapper.double_click(**kwargs)
    else:
        wrapper.click(**kwargs)
    return {"clicked": True, "button": button, "double": double}


def control_double_click(wrapper_id: str, button: str = "left",
                          coords: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Double-click the control."""
    return control_click(wrapper_id, button=button, coords=coords, double=True)


def control_right_click(wrapper_id: str, coords: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Right-click the control."""
    return control_click(wrapper_id, button="right", coords=coords)


def control_type_keys(wrapper_id: str, keys: str, with_spaces: bool = False,
                      with_tabs: bool = False, with_newlines: bool = False,
                      turn_off_numlock: bool = True, set_foreground: bool = True,
                      pause: Optional[float] = None) -> dict[str, Any]:
    """Type keys into the control (supports pywinauto key syntax).

    Examples: '^a' (Ctrl+A), '%{F4}' (Alt+F4), 'hello world'
    """
    wrapper = _get_wrapper(wrapper_id)
    kwargs: dict[str, Any] = {
        "with_spaces": with_spaces,
        "with_tabs": with_tabs,
        "with_newlines": with_newlines,
        "turn_off_numlock": turn_off_numlock,
        "set_foreground": set_foreground,
    }
    if pause is not None:
        kwargs["pause"] = pause
    wrapper.type_keys(keys, **kwargs)
    return {"typed": keys}


def control_set_text(wrapper_id: str, text: str) -> dict[str, Any]:
    """Set the text of an edit control (via SetText)."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.set_text(text)
    return {"text_set": text}


def control_set_edit_text(wrapper_id: str, text: str) -> dict[str, Any]:
    """Set edit text via UIA patterns (more reliable for UIA)."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "set_edit_text"):
        wrapper.set_edit_text(text)
    else:
        wrapper.set_text(text)
    return {"text_set": text}


def control_get_text(wrapper_id: str) -> dict[str, Any]:
    """Get the window/control text."""
    wrapper = _get_wrapper(wrapper_id)
    return {"text": wrapper.window_text()}


def control_select(wrapper_id, item: Optional[str] = None, index: Optional[int] = None) -> dict[str, Any]:
    """Select an item in a list/combo box.

    Provide either item (text) or index.
    """
    wrapper = _get_wrapper(wrapper_id)
    if index is not None:
        wrapper.select(index)
    elif item is not None:
        wrapper.select(item)
    else:
        wrapper.select()
    return {"selected": item if item else index}


def control_check(wrapper_id: str) -> dict[str, Any]:
    """Check a checkbox/toggle."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "check"):
        wrapper.check()
    elif hasattr(wrapper, "toggle"):
        wrapper.toggle()
    return {"checked": True}


def control_uncheck(wrapper_id: str) -> dict[str, Any]:
    """Uncheck a checkbox/toggle."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "uncheck"):
        wrapper.uncheck()
    elif hasattr(wrapper, "toggle"):
        wrapper.toggle()
    return {"unchecked": True}


def control_is_checked(wrapper_id: str) -> dict[str, Any]:
    """Get check state of a checkbox/toggle."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "is_checked"):
        return {"is_checked": wrapper.is_checked()}
    if hasattr(wrapper, "get_toggle_state"):
        return {"toggle_state": wrapper.get_toggle_state()}
    return {"is_checked": None, "note": "Control does not support check state"}


def control_expand(wrapper_id: str) -> dict[str, Any]:
    """Expand a collapsible element (tree node, combo box, etc.)."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "expand"):
        wrapper.expand()
    elif hasattr(wrapper, "expand_expand"):
        wrapper.expand_expand()
    return {"expanded": True}


def control_collapse(wrapper_id: str) -> dict[str, Any]:
    """Collapse an expandable element."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "collapse"):
        wrapper.collapse()
    elif hasattr(wrapper, "collapse_collapse"):
        wrapper.collapse_collapse()
    return {"collapsed": True}


def control_get_expand_state(wrapper_id: str) -> dict[str, Any]:
    """Get expand/collapse state."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_expand_state"):
        return {"expand_state": wrapper.get_expand_state()}
    return {"expand_state": None, "note": "Control does not support expand state"}


def control_set_focus(wrapper_id: str) -> dict[str, Any]:
    """Set keyboard focus to the control."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.set_focus()
    return {"focus_set": True}


def control_close(wrapper_id: str) -> dict[str, Any]:
    """Close the window."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.close()
    return {"closed": True}


def control_minimize(wrapper_id: str) -> dict[str, Any]:
    """Minimize the window."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.minimize()
    return {"minimized": True}


def control_maximize(wrapper_id: str) -> dict[str, Any]:
    """Maximize the window."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.maximize()
    return {"maximized": True}


def control_restore(wrapper_id: str) -> dict[str, Any]:
    """Restore the window."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.restore()
    return {"restored": True}


def control_get_show_state(wrapper_id: str) -> dict[str, Any]:
    """Get the window show state (maximized/minimized/restored)."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_show_state"):
        return {"show_state": wrapper.get_show_state()}
    return {"show_state": None}


def control_move_window(wrapper_id: str, x: int, y: int,
                         width: Optional[int] = None,
                         height: Optional[int] = None) -> dict[str, Any]:
    """Move and optionally resize the window."""
    wrapper = _get_wrapper(wrapper_id)
    kwargs: dict[str, Any] = {}
    if width is not None:
        kwargs["width"] = width
    if height is not None:
        kwargs["height"] = height
    wrapper.move_window(x, y, **kwargs)
    return {"moved_to": {"x": x, "y": y, "width": width, "height": height}}


def control_resize(wrapper_id: str, width: int, height: int) -> dict[str, Any]:
    """Resize the window/control."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "resize"):
        wrapper.resize(width, height)
    else:
        rect = wrapper.rectangle()
        wrapper.move_window(rect.left, rect.top, width, height)
    return {"resized": {"width": width, "height": height}}


def control_menu_select(wrapper_id: str, path: str) -> dict[str, Any]:
    """Select a menu item by path (e.g. 'File->Save', 'File->New->Document').

    For UIA apps, use the menu item path with '->' separators.
    """
    wrapper = _get_wrapper(wrapper_id)
    wrapper.menu_select(path)
    return {"menu_selected": path}


def control_drag_mouse(wrapper_id: str, dst: tuple[int, int],
                        src: Optional[tuple[int, int]] = None,
                        button: str = "left", pressed: str = "") -> dict[str, Any]:
    """Drag the mouse from src to dst on the control.

    Args:
        dst: Destination (x, y) relative to control
        src: Source (x, y) relative to control, or None for center
        button: 'left', 'right', 'middle'
        pressed: '' for press at start, 'start' for already pressed
    """
    wrapper = _get_wrapper(wrapper_id)
    kwargs: dict[str, Any] = {"button": button, "pressed": pressed}
    if src:
        kwargs["src"] = src
    wrapper.drag_mouse(dst, **kwargs)
    return {"dragged": {"src": src, "dst": dst, "button": button}}


def control_scroll(wrapper_id: str, direction: str = "down",
                    amount: int = 1, count: int = 1) -> dict[str, Any]:
    """Scroll the control.

    Args:
        direction: 'up', 'down', 'left', 'right'
        amount: scroll amount (1-5 typically)
        count: number of scroll actions
    """
    wrapper = _get_wrapper(wrapper_id)
    wrapper.scroll(direction, amount, count)
    return {"scrolled": {"direction": direction, "amount": amount, "count": count}}


def control_scroll_at_point(wrapper_id: str, direction: str = "down",
                              amount: int = 1, count: int = 1,
                              x: Optional[int] = None, y: Optional[int] = None) -> dict[str, Any]:
    """Scroll at a specific point on the control."""
    wrapper = _get_wrapper(wrapper_id)
    kwargs: dict[str, Any] = {}
    if x is not None and y is not None:
        kwargs["x"] = x
        kwargs["y"] = y
    wrapper.scroll_at_point(direction, amount, count, **kwargs)
    return {"scrolled_at_point": {"direction": direction, "amount": amount, "count": count}}


def control_get_properties(wrapper_id: str) -> dict[str, Any]:
    """Get all available properties of the control."""
    wrapper = _get_wrapper(wrapper_id)
    try:
        props = wrapper.get_properties()
        # Convert non-serializable values
        serializable = {}
        for k, v in props.items():
            try:
                import json
                json.dumps(v)
                serializable[k] = v
            except (TypeError, ValueError):
                serializable[k] = str(v)
        return serializable
    except Exception as e:
        return {"error": str(e), "fallback": _wrapper_info(wrapper)}


def control_get_rectangle(wrapper_id: str) -> dict[str, Any]:
    """Get the bounding rectangle of the control."""
    wrapper = _get_wrapper(wrapper_id)
    return _rect_to_dict(wrapper.rectangle())


def control_get_class_name(wrapper_id: str) -> dict[str, Any]:
    """Get the class name."""
    wrapper = _get_wrapper(wrapper_id)
    return {"class_name": wrapper.class_name()}


def control_get_backend(wrapper_id: str) -> dict[str, Any]:
    """Get the backend name."""
    wrapper = _get_wrapper(wrapper_id)
    return {"backend": getattr(wrapper, "backend", None) or type(wrapper).__module__}


def control_get_handle(wrapper_id: str) -> dict[str, Any]:
    """Get the window handle."""
    wrapper = _get_wrapper(wrapper_id)
    return {"handle": getattr(wrapper, "handle", None)}


def control_is_active(wrapper_id: str) -> dict[str, Any]:
    """Check if the window is active."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "is_active"):
        return {"is_active": wrapper.is_active()}
    return {"is_active": None}


def control_is_visible(wrapper_id: str) -> dict[str, Any]:
    """Check if the control is visible."""
    wrapper = _get_wrapper(wrapper_id)
    return {"is_visible": wrapper.is_visible()}


def control_is_enabled(wrapper_id: str) -> dict[str, Any]:
    """Check if the control is enabled."""
    wrapper = _get_wrapper(wrapper_id)
    return {"is_enabled": wrapper.is_enabled()}


def control_capture_as_image(wrapper_id: str, save_path: Optional[str] = None) -> dict[str, Any]:
    """Capture the control as an image.

    Returns the image path if save_path is provided, otherwise base64.
    """
    wrapper = _get_wrapper(wrapper_id)
    img = wrapper.capture_as_image()
    if save_path:
        img.save(save_path)
        return {"image_saved": save_path, "size": img.size}
    import base64
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {"image_base64": base64.b64encode(buf.getvalue()).decode(), "size": img.size}


def control_child_window(wrapper_id: str, **kwargs: Any) -> dict[str, Any]:
    """Find a child control by criteria.

    Criteria: title, title_re, class_name, class_name_re, control_type,
    auto_id, control_id, found_index, etc.
    """
    wrapper = _get_wrapper(wrapper_id)
    child_spec = wrapper.child_window(**kwargs)
    child = child_spec.wrapper_object()
    wid = _register_wrapper(child)
    return {"wrapper_id": wid, **_wrapper_info(child)}


def control_children(wrapper_id: str, **kwargs: Any) -> dict[str, Any]:
    """Get immediate children of the control."""
    wrapper = _get_wrapper(wrapper_id)
    children = wrapper.children(**kwargs) if hasattr(wrapper, "children") else []
    result = []
    for c in children:
        wid = _register_wrapper(c)
        result.append({"wrapper_id": wid, **_wrapper_info(c)})
    return {"count": len(result), "children": result}


def control_descendants(wrapper_id: str, **kwargs: Any) -> dict[str, Any]:
    """Get all descendants of the control."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "descendants"):
        descs = wrapper.descendants(**kwargs)
    else:
        descs = []
    result = []
    for d in descs:
        wid = _register_wrapper(d)
        result.append({"wrapper_id": wid, **_wrapper_info(d)})
    return {"count": len(result), "descendants": result}


def control_invoke(wrapper_id: str) -> dict[str, Any]:
    """Invoke the default action (UIA Invoke pattern)."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "invoke"):
        wrapper.invoke()
        return {"invoked": True}
    return {"invoked": False, "note": "Control does not support Invoke pattern"}


def control_get_value(wrapper_id: str) -> dict[str, Any]:
    """Get the Value pattern value."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_value"):
        return {"value": wrapper.get_value()}
    return {"value": None, "note": "Control does not support Value pattern"}


def control_set_value(wrapper_id: str, value: str) -> dict[str, Any]:
    """Set the Value pattern value."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "set_value"):
        wrapper.set_value(value)
        return {"value_set": value}
    return {"value_set": False, "note": "Control does not support Value pattern"}


def control_get_range_value(wrapper_id: str) -> dict[str, Any]:
    """Get the RangeValue pattern value (sliders, progress bars)."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_value") and "range" in type(wrapper).__name__.lower():
        return {"range_value": wrapper.get_value()}
    if hasattr(wrapper, "range_value"):
        return {"range_value": wrapper.range_value()}
    return {"range_value": None}


def control_get_item_texts(wrapper_id: str) -> dict[str, Any]:
    """Get text of all items in a list/combo box."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "item_texts"):
        return {"items": wrapper.item_texts()}
    return {"items": [], "note": "Control does not support item_texts"}


def control_selected_index(wrapper_id: str) -> dict[str, Any]:
    """Get the selected index in a list/combo box."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "selected_index"):
        return {"selected_index": wrapper.selected_index()}
    return {"selected_index": None}


def control_selected_text(wrapper_id: str) -> dict[str, Any]:
    """Get the selected text in a list/combo box."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "selected_text"):
        return {"selected_text": wrapper.selected_text()}
    return {"selected_text": None}


def control_click_input(wrapper_id: str, button: str = "left",
                         coords: Optional[tuple[int, int]] = None,
                         double: bool = False) -> dict[str, Any]:
    """Click using send_message (more realistic, activates window first)."""
    wrapper = _get_wrapper(wrapper_id)
    kwargs: dict[str, Any] = {"button": button}
    if coords:
        kwargs["coords"] = coords
    if double:
        wrapper.double_click_input(**kwargs)
    else:
        wrapper.click_input(**kwargs)
    return {"click_input": True, "button": button, "double": double}


def control_press_mouse(wrapper_id: str, button: str = "left",
                         coords: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Press a mouse button on the control."""
    wrapper = _get_wrapper(wrapper_id)
    kwargs: dict[str, Any] = {"button": button}
    if coords:
        kwargs["coords"] = coords
    wrapper.press_mouse(**kwargs)
    return {"mouse_pressed": button}


def control_release_mouse(wrapper_id: str, button: str = "left",
                           coords: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Release a mouse button on the control."""
    wrapper = _get_wrapper(wrapper_id)
    kwargs: dict[str, Any] = {"button": button}
    if coords:
        kwargs["coords"] = coords
    wrapper.release_mouse(**kwargs)
    return {"mouse_released": button}


def control_move_mouse(wrapper_id: str, coords: Optional[tuple[int, int]] = None,
                        pressed: str = "") -> dict[str, Any]:
    """Move the mouse over the control."""
    wrapper = _get_wrapper(wrapper_id)
    kwargs: dict[str, Any] = {"pressed": pressed}
    if coords:
        kwargs["coords"] = coords
    wrapper.move_mouse(**kwargs)
    return {"mouse_moved": True}


def control_get_tool_tip(wrapper_id: str) -> dict[str, Any]:
    """Get the tooltip text."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_tool_tip"):
        return {"tooltip": wrapper.get_tool_tip()}
    return {"tooltip": None}


def control_verify_action(wrapper_id: str, action: str = "click") -> dict[str, Any]:
    """Verify that an action can be performed (returns True/False)."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "verify_action"):
        return {"can_perform": wrapper.verify_action(action)}
    return {"can_perform": None}


def control_get_boundary_rect(wrapper_id: str) -> dict[str, Any]:
    """Get the UIA boundary rectangle."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_boundary_rect"):
        rect = wrapper.get_boundary_rect()
        return {"boundary_rect": {"left": rect.left, "top": rect.top,
                                    "right": rect.right, "bottom": rect.bottom}}
    return {"boundary_rect": None}


def control_get_legacy_iaccessible_property(wrapper_id: str, property_name: str) -> dict[str, Any]:
    """Get a legacy IAccessible property (UIA only)."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_legacy_iaccessible_property_value"):
        val = wrapper.get_legacy_iaccessible_property_value(property_name)
        return {property_name: str(val)}
    return {property_name: None, "note": "Not supported"}


# ===========================================================================
# 4. KEYBOARD
# ===========================================================================

def keyboard_send_keys(keys: str, with_spaces: bool = False,
                       with_tabs: bool = False, with_newlines: bool = False,
                       turn_off_numlock: bool = True,
                       pause: Optional[float] = None) -> dict[str, Any]:
    """Send keys to the active window.

    Supports pywinauto key syntax:
      - '^a' = Ctrl+A, '%{F4}' = Alt+F4, '+{INS}' = Shift+Ins
      - '{ENTER}', '{TAB}', '{ESC}', '{F1}'..'{F24}'
      - '{VK_SHIFT down}' ... '{VK_SHIFT up}' for hold/release
      - Use '{^}' to type literal '^', '{{}' for literal '{'
    """
    from pywinauto.keyboard import send_keys
    kwargs: dict[str, Any] = {
        "with_spaces": with_spaces,
        "with_tabs": with_tabs,
        "with_newlines": with_newlines,
        "turn_off_numlock": turn_off_numlock,
    }
    if pause is not None:
        kwargs["pause"] = pause
    send_keys(keys, **kwargs)
    return {"sent_keys": keys}


def keyboard_key_press(key: str) -> dict[str, Any]:
    """Press and hold a key (use keyboard_key_release to release)."""
    from pywinauto.keyboard import key_press as _key_press
    _key_press(key)
    return {"key_pressed": key}


def keyboard_key_release(key: str) -> dict[str, Any]:
    """Release a previously pressed key."""
    from pywinauto.keyboard import key_release as _key_release
    _key_release(key)
    return {"key_released": key}


# ===========================================================================
# 5. MOUSE (global)
# ===========================================================================

def mouse_click(button: str = "left", coords: Optional[tuple[int, int]] = None,
                double: bool = False) -> dict[str, Any]:
    """Click at screen coordinates (or current position if None)."""
    from pywinauto.mouse import click as _click, double_click as _dclick
    if double:
        _dclick(button=button, coords=coords)
    else:
        _click(button=button, coords=coords)
    return {"mouse_clicked": {"button": button, "coords": coords, "double": double}}


def mouse_double_click(button: str = "left", coords: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Double-click at screen coordinates."""
    return mouse_click(button=button, coords=coords, double=True)


def mouse_right_click(coords: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Right-click at screen coordinates."""
    return mouse_click(button="right", coords=coords)


def mouse_move(coords: tuple[int, int]) -> dict[str, Any]:
    """Move the mouse to screen coordinates."""
    from pywinauto.mouse import move as _move
    _move(coords=coords)
    return {"mouse_moved_to": coords}


def mouse_press(button: str = "left", coords: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Press a mouse button at screen coordinates."""
    from pywinauto.mouse import press as _press
    _press(button=button, coords=coords)
    return {"mouse_pressed": {"button": button, "coords": coords}}


def mouse_release(button: str = "left", coords: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Release a mouse button at screen coordinates."""
    from pywinauto.mouse import release as _release
    _release(button=button, coords=coords)
    return {"mouse_released": {"button": button, "coords": coords}}


def mouse_scroll(direction: str = "up", amount: int = 1,
                  coords: Optional[tuple[int, int]] = None) -> dict[str, Any]:
    """Scroll the mouse wheel.

    Args:
        direction: 'up' or 'down'
        amount: number of scroll steps
        coords: where to scroll (None = current position)
    """
    from pywinauto.mouse import scroll as _scroll
    _scroll(direction=direction, amount=amount, coords=coords)
    return {"mouse_scrolled": {"direction": direction, "amount": amount, "coords": coords}}


def mouse_drag(src: tuple[int, int], dst: tuple[int, int],
                button: str = "left") -> dict[str, Any]:
    """Drag from src to dst at screen coordinates."""
    from pywinauto.mouse import press, move, release
    press(button=button, coords=src)
    move(coords=dst)
    release(button=button, coords=dst)
    return {"mouse_dragged": {"src": src, "dst": dst, "button": button}}


def mouse_get_position() -> dict[str, Any]:
    """Get current mouse position."""
    from pywinauto.mouse import get_position
    pos = get_position()
    return {"position": {"x": pos[0], "y": pos[1]}}


# ===========================================================================
# 6. CLIPBOARD
# ===========================================================================

def clipboard_get_data() -> dict[str, Any]:
    """Get text from the clipboard."""
    from pywinauto.clipboard import GetClipboardFormats, GetData
    formats = GetClipboardFormats()
    try:
        text = GetData()
    except Exception:
        text = ""
    return {"text": text, "formats": formats}


def clipboard_set_data(text: str) -> dict[str, Any]:
    """Set text to the clipboard."""
    import win32clipboard
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text)
    finally:
        win32clipboard.CloseClipboard()
    return {"clipboard_set": text}


def clipboard_empty() -> dict[str, Any]:
    """Empty the clipboard."""
    from pywinauto.clipboard import EmptyClipboard
    EmptyClipboard()
    return {"clipboard_emptied": True}


def clipboard_get_formats() -> dict[str, Any]:
    """Get available clipboard formats."""
    from pywinauto.clipboard import GetClipboardFormats
    return {"formats": GetClipboardFormats()}


# ===========================================================================
# 7. TIMINGS
# ===========================================================================

def timings_get() -> dict[str, Any]:
    """Get current timing configuration (all available timing keys)."""
    from pywinauto.timings import Timings
    # Access internal _timings dict via object.__getattribute__ to bypass
    # TimeConfig.__getattribute__ which only allows known timing keys
    timings_dict = object.__getattribute__(Timings, "_timings")
    return dict(timings_dict)


def timings_set(**kwargs: Any) -> dict[str, Any]:
    """Set timing configuration values.

    Available keys include: window_find_timeout, window_find_retry,
    app_start_timeout, app_start_retry, exists_timeout, exists_retry,
    after_click_wait, after_menu_wait, after_sendkeys_key_wait,
    drag_n_drop_move_mouse_wait, before_drag_wait, before_drop_wait,
    after_drag_n_drop_wait, scroll_step_wait, etc.
    Use timings_get() to see the full list.
    """
    from pywinauto.timings import Timings
    updated = {}
    for key, value in kwargs.items():
        try:
            setattr(Timings, key, value)
            updated[key] = value
        except AttributeError:
            logger.warning("Unknown timing setting: %s", key)
    return {"timings_updated": updated}


def timings_defaults() -> dict[str, Any]:
    """Reset timings to default values."""
    from pywinauto.timings import Timings
    Timings.defaults()
    return {"timings_reset": "defaults"}


def timings_slow() -> dict[str, Any]:
    """Set timings to slow mode (for debugging)."""
    from pywinauto.timings import Timings
    Timings.slow()
    return {"timings_set": "slow"}


def timings_fast() -> dict[str, Any]:
    """Set timings to fast mode."""
    from pywinauto.timings import Timings
    Timings.fast()
    return {"timings_set": "fast"}


def wait_until(timeout: float, retry_interval: float, func: str,
               *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Wait until a function returns a truthy value.

    Note: func is a string expression evaluated in the wrapper context.
    For simple waiting, use window_wait instead.
    """
    from pywinauto.timings import wait_until as _wait_until
    # This is a simplified version - in practice callers use window_wait
    return {"note": "Use window_wait for window state waiting. "
                     "wait_until requires a callable which is not directly serializable."}


def wait_until_passes(timeout: float, retry_interval: float,
                       func: Any, exceptions: tuple = (Exception,),
                       *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Wait until a function passes without raising exceptions."""
    from pywinauto.timings import wait_until_passes as _wup
    return {"note": "Use window_wait for window state waiting."}


# ===========================================================================
# 8. SYSTEM INFO
# ===========================================================================

def sysinfo_is_x64_python() -> dict[str, Any]:
    """Check if Python is 64-bit."""
    from pywinauto.sysinfo import is_x64_Python
    return {"is_x64_python": is_x64_Python()}


def sysinfo_is_x64_os() -> dict[str, Any]:
    """Check if the OS is 64-bit."""
    from pywinauto.sysinfo import is_x64_OS
    return {"is_x64_os": is_x64_OS()}


def sysinfo_os_arch() -> dict[str, Any]:
    """Get OS architecture."""
    from pywinauto.sysinfo import os_arch
    return {"os_arch": os_arch()}


def sysinfo_python_bitness() -> dict[str, Any]:
    """Get Python bitness."""
    from pywinauto.sysinfo import python_bitness
    return {"python_bitness": python_bitness()}


# ===========================================================================
# 9. FIND WINDOWS / ELEMENTS
# ===========================================================================

def find_windows(backend: str = "uia", **kwargs: Any) -> dict[str, Any]:
    """Find windows matching criteria.

    Criteria: title, title_re, class_name, class_name_re, process,
    handle, enabled_only, visible_only, top_level_only, etc.

    Returns list of window handles.
    """
    from pywinauto.findwindows import find_windows as _find_windows
    handles = _find_windows(backend=backend, **kwargs)
    return {"count": len(handles), "handles": handles}


def find_elements(backend: str = "uia", **kwargs: Any) -> dict[str, Any]:
    """Find elements matching criteria (UIA only).

    Returns list of element info dicts.
    """
    from pywinauto.findwindows import find_elements as _find_elements
    elements = _find_elements(backend=backend, **kwargs)
    result = []
    for el in elements:
        info = {
            "handle": getattr(el, "handle", None),
            "name": getattr(el, "name", None),
            "class_name": getattr(el, "class_name", None),
            "control_type": str(getattr(el, "control_type", None)),
            "auto_id": getattr(el, "auto_id", None),
            "process_id": getattr(el, "process_id", None),
            "runtime_id": getattr(el, "runtime_id", None),
        }
        result.append(info)
    return {"count": len(result), "elements": result}


def enumerate_windows(backend: str = "uia") -> dict[str, Any]:
    """Enumerate all top-level windows."""
    from pywinauto import Desktop
    desktop = Desktop(backend=backend)
    windows = desktop.windows()
    result = []
    for w in windows:
        try:
            result.append({
                "handle": w.handle,
                "title": w.window_text(),
                "class_name": w.class_name(),
                "is_visible": w.is_visible(),
                "is_enabled": w.is_enabled(),
                "process_id": w.process_id(),
            })
        except Exception:
            pass
    return {"count": len(result), "windows": result}


# ===========================================================================
# 10. TASKBAR
# ===========================================================================

def taskbar_click_on_button(text: str, by: str = "title") -> dict[str, Any]:
    """Click a button on the taskbar.

    Args:
        text: Button text or index
        by: 'title' or 'index'
    """
    from pywinauto.taskbar import TaskBar
    tb = TaskBar()
    if by == "index":
        tb.button(int(text)).click()
    else:
        tb.button(text).click()
    return {"taskbar_button_clicked": text}


def taskbar_get_button(text: str) -> dict[str, Any]:
    """Get a taskbar button wrapper."""
    from pywinauto.taskbar import TaskBar
    tb = TaskBar()
    btn = tb.button(text)
    wid = _register_wrapper(btn)
    return {"wrapper_id": wid, **_wrapper_info(btn)}


def taskbar_get_start_button() -> dict[str, Any]:
    """Get the Start button wrapper."""
    from pywinauto.taskbar import TaskBar
    tb = TaskBar()
    btn = tb.StartButton
    wid = _register_wrapper(btn)
    return {"wrapper_id": wid, **_wrapper_info(btn)}


def taskbar_get_search_edit() -> dict[str, Any]:
    """Get the search box edit wrapper."""
    from pywinauto.taskbar import TaskBar
    tb = TaskBar()
    edit = tb.SearchEdit
    wid = _register_wrapper(edit)
    return {"wrapper_id": wid, **_wrapper_info(edit)}


def taskbar_get_system_tray() -> dict[str, Any]:
    """Get the system tray (notification area) wrapper."""
    from pywinauto.taskbar import TaskBar
    tb = TaskBar()
    tray = tb.SystemTray
    wid = _register_wrapper(tray)
    return {"wrapper_id": wid, **_wrapper_info(tray)}


# ===========================================================================
# 11. DESKTOP
# ===========================================================================

def desktop_windows(backend: str = "uia") -> dict[str, Any]:
    """Get all top-level desktop windows as wrapper sessions."""
    from pywinauto import Desktop
    desktop = Desktop(backend=backend)
    windows = desktop.windows()
    result = []
    for w in windows:
        wid = _register_wrapper(w)
        result.append({"wrapper_id": wid, **_wrapper_info(w)})
    return {"count": len(result), "windows": result}


def desktop_active_window(backend: str = "uia") -> dict[str, Any]:
    """Get the currently active desktop window."""
    from pywinauto import Desktop
    desktop = Desktop(backend=backend)
    win = desktop.active()
    wrapper = win.wrapper_object()
    wid = _register_wrapper(wrapper)
    return {"wrapper_id": wid, **_wrapper_info(wrapper)}


def desktop_window(backend: str = "uia", **kwargs: Any) -> dict[str, Any]:
    """Find a desktop window by criteria."""
    from pywinauto import Desktop
    desktop = Desktop(backend=backend)
    win_spec = desktop.window(**kwargs)
    wrapper = win_spec.wrapper_object()
    wid = _register_wrapper(wrapper)
    return {"wrapper_id": wid, **_wrapper_info(wrapper)}


# ===========================================================================
# 12. MENU OPERATIONS
# ===========================================================================

def menu_get_items(wrapper_id: str, path: Optional[str] = None) -> dict[str, Any]:
    """Get menu items from a menu wrapper or window.

    Args:
        wrapper_id: Wrapper session ID (window or menu)
        path: Optional menu path to navigate first (e.g. 'File')
    """
    wrapper = _get_wrapper(wrapper_id)
    try:
        if path:
            menu = wrapper.menu()
            items = menu.menu_items(path)
        else:
            menu = wrapper.menu()
            items = menu.items()
        result = []
        for item in items:
            result.append({
                "text": item.text(),
                "is_enabled": item.is_enabled(),
                "is_checked": item.is_checked() if hasattr(item, "is_checked") else None,
                "state": item.state if hasattr(item, "state") else None,
            })
        return {"count": len(result), "items": result}
    except Exception as e:
        return {"error": str(e)}


def menu_click_item(wrapper_id: str, path: str) -> dict[str, Any]:
    """Click a menu item by path (e.g. 'File->Save')."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.menu_select(path)
    return {"menu_item_clicked": path}


# ===========================================================================
# 13. COMBO BOX / LIST / TAB / TREE SPECIFIC OPERATIONS
# ===========================================================================

def combobox_select(wrapper_id: str, item: str) -> dict[str, Any]:
    """Select an item in a combo box by text."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.select(item)
    return {"combobox_selected": item}


def combobox_get_items(wrapper_id: str) -> dict[str, Any]:
    """Get all items in a combo box."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "item_texts"):
        return {"items": wrapper.item_texts()}
    return {"items": []}


def listbox_select(wrapper_id: str, item: str) -> dict[str, Any]:
    """Select an item in a list box by text."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.select(item)
    return {"listbox_selected": item}


def listbox_get_selected(wrapper_id: str) -> dict[str, Any]:
    """Get selected items in a list box."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "selected_items"):
        return {"selected_items": wrapper.selected_items()}
    if hasattr(wrapper, "selected_text"):
        return {"selected_text": wrapper.selected_text()}
    return {"selected": None}


def tab_select(wrapper_id: str, tab: str) -> dict[str, Any]:
    """Select a tab by text or index."""
    wrapper = _get_wrapper(wrapper_id)
    wrapper.select(tab)
    return {"tab_selected": tab}


def tab_get_selected(wrapper_id: str) -> dict[str, Any]:
    """Get the selected tab."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_selected_tab"):
        return {"selected_tab": wrapper.get_selected_tab()}
    return {"selected_tab": None}


def tree_get_selected(wrapper_id: str) -> dict[str, Any]:
    """Get the selected tree node."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_selected"):
        return {"selected": wrapper.get_selected()}
    return {"selected": None}


def tree_select(wrapper_id: str, path: str) -> dict[str, Any]:
    """Select a tree node by path (e.g. 'Root\\Child\\Grandchild')."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_item"):
        item = wrapper.get_item(path)
        item.select()
        return {"tree_selected": path}
    return {"tree_selected": False, "note": "Control does not support tree selection"}


def tree_expand(wrapper_id: str, path: str) -> dict[str, Any]:
    """Expand a tree node by path."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_item"):
        item = wrapper.get_item(path)
        item.expand()
        return {"tree_expanded": path}
    return {"tree_expanded": False}


def tree_collapse(wrapper_id: str, path: str) -> dict[str, Any]:
    """Collapse a tree node by path."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_item"):
        item = wrapper.get_item(path)
        item.collapse()
        return {"tree_collapsed": path}
    return {"tree_collapsed": False}


def slider_get_position(wrapper_id: str) -> dict[str, Any]:
    """Get slider position."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_value"):
        return {"position": wrapper.get_value()}
    return {"position": None}


def slider_set_position(wrapper_id: str, value: float) -> dict[str, Any]:
    """Set slider position."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "set_value"):
        wrapper.set_value(value)
        return {"position_set": value}
    return {"position_set": False}


def progress_get_position(wrapper_id: str) -> dict[str, Any]:
    """Get progress bar position."""
    wrapper = _get_wrapper(wrapper_id)
    if hasattr(wrapper, "get_value"):
        return {"position": wrapper.get_value()}
    return {"position": None}


# ===========================================================================
# 14. UTILITY: GENERIC METHOD CALL
# ===========================================================================

def control_call_method(wrapper_id: str, method: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Call any method on a wrapper object (escape hatch for APIs not explicitly wrapped).

    Args:
        wrapper_id: Wrapper session ID
        method: Method name to call
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Method result (JSON-serialized if possible)
    """
    wrapper = _get_wrapper(wrapper_id)
    result = _safe_call(wrapper, method, *args, **kwargs)
    # Try to serialize
    try:
        import json
        json.dumps(result)
        return {"result": result}
    except (TypeError, ValueError):
        return {"result": str(result), "result_type": type(result).__name__}


def control_get_attribute(wrapper_id: str, attribute: str) -> dict[str, Any]:
    """Get any attribute from a wrapper object.

    Args:
        wrapper_id: Wrapper session ID
        attribute: Attribute name
    """
    wrapper = _get_wrapper(wrapper_id)
    value = getattr(wrapper, attribute, None)
    if callable(value):
        return {"attribute": attribute, "value": str(value), "is_callable": True}
    try:
        import json
        json.dumps(value)
        return {"attribute": attribute, "value": value}
    except (TypeError, ValueError):
        return {"attribute": attribute, "value": str(value), "value_type": type(value).__name__}


# ===========================================================================
# Export all functions for MCP tool registration
# ===========================================================================

ALL_FUNCTIONS = {
    # Session management
    "list_sessions": list_sessions,
    "close_session": close_session,
    "close_all_sessions": close_all_sessions,
    # Application
    "app_start": app_start,
    "app_connect": app_connect,
    "app_kill": app_kill,
    "app_windows": app_windows,
    "app_top_window": app_top_window,
    "app_active_window": app_active_window,
    "app_window": app_window,
    "app_cpu_usage": app_cpu_usage,
    "app_is64bit": app_is64bit,
    "app_is_process_running": app_is_process_running,
    "app_wait_cpu_usage_lower": app_wait_cpu_usage_lower,
    "app_wait_for_process_exit": app_wait_for_process_exit,
    # Window/Control resolution
    "window_find": window_find,
    "window_exists": window_exists,
    "window_wait": window_wait,
    "window_dump_tree": window_dump_tree,
    "window_print_control_identifiers": window_print_control_identifiers,
    "window_get_wrapper": window_get_wrapper,
    "window_release": window_release,
    # Control actions
    "control_click": control_click,
    "control_double_click": control_double_click,
    "control_right_click": control_right_click,
    "control_click_input": control_click_input,
    "control_type_keys": control_type_keys,
    "control_set_text": control_set_text,
    "control_set_edit_text": control_set_edit_text,
    "control_get_text": control_get_text,
    "control_select": control_select,
    "control_check": control_check,
    "control_uncheck": control_uncheck,
    "control_is_checked": control_is_checked,
    "control_expand": control_expand,
    "control_collapse": control_collapse,
    "control_get_expand_state": control_get_expand_state,
    "control_set_focus": control_set_focus,
    "control_close": control_close,
    "control_minimize": control_minimize,
    "control_maximize": control_maximize,
    "control_restore": control_restore,
    "control_get_show_state": control_get_show_state,
    "control_move_window": control_move_window,
    "control_resize": control_resize,
    "control_menu_select": control_menu_select,
    "control_drag_mouse": control_drag_mouse,
    "control_scroll": control_scroll,
    "control_scroll_at_point": control_scroll_at_point,
    "control_press_mouse": control_press_mouse,
    "control_release_mouse": control_release_mouse,
    "control_move_mouse": control_move_mouse,
    "control_get_properties": control_get_properties,
    "control_get_rectangle": control_get_rectangle,
    "control_get_class_name": control_get_class_name,
    "control_get_backend": control_get_backend,
    "control_get_handle": control_get_handle,
    "control_is_active": control_is_active,
    "control_is_visible": control_is_visible,
    "control_is_enabled": control_is_enabled,
    "control_capture_as_image": control_capture_as_image,
    "control_child_window": control_child_window,
    "control_children": control_children,
    "control_descendants": control_descendants,
    "control_invoke": control_invoke,
    "control_get_value": control_get_value,
    "control_set_value": control_set_value,
    "control_get_range_value": control_get_range_value,
    "control_get_item_texts": control_get_item_texts,
    "control_selected_index": control_selected_index,
    "control_selected_text": control_selected_text,
    "control_get_tool_tip": control_get_tool_tip,
    "control_verify_action": control_verify_action,
    "control_get_boundary_rect": control_get_boundary_rect,
    "control_get_legacy_iaccessible_property": control_get_legacy_iaccessible_property,
    # Keyboard
    "keyboard_send_keys": keyboard_send_keys,
    "keyboard_key_press": keyboard_key_press,
    "keyboard_key_release": keyboard_key_release,
    # Mouse
    "mouse_click": mouse_click,
    "mouse_double_click": mouse_double_click,
    "mouse_right_click": mouse_right_click,
    "mouse_move": mouse_move,
    "mouse_press": mouse_press,
    "mouse_release": mouse_release,
    "mouse_scroll": mouse_scroll,
    "mouse_drag": mouse_drag,
    "mouse_get_position": mouse_get_position,
    # Clipboard
    "clipboard_get_data": clipboard_get_data,
    "clipboard_set_data": clipboard_set_data,
    "clipboard_empty": clipboard_empty,
    "clipboard_get_formats": clipboard_get_formats,
    # Timings
    "timings_get": timings_get,
    "timings_set": timings_set,
    "timings_defaults": timings_defaults,
    "timings_slow": timings_slow,
    "timings_fast": timings_fast,
    # System info
    "sysinfo_is_x64_python": sysinfo_is_x64_python,
    "sysinfo_is_x64_os": sysinfo_is_x64_os,
    "sysinfo_os_arch": sysinfo_os_arch,
    "sysinfo_python_bitness": sysinfo_python_bitness,
    # Find
    "find_windows": find_windows,
    "find_elements": find_elements,
    "enumerate_windows": enumerate_windows,
    # Taskbar
    "taskbar_click_on_button": taskbar_click_on_button,
    "taskbar_get_button": taskbar_get_button,
    "taskbar_get_start_button": taskbar_get_start_button,
    "taskbar_get_search_edit": taskbar_get_search_edit,
    "taskbar_get_system_tray": taskbar_get_system_tray,
    # Desktop
    "desktop_windows": desktop_windows,
    "desktop_active_window": desktop_active_window,
    "desktop_window": desktop_window,
    # Menu
    "menu_get_items": menu_get_items,
    "menu_click_item": menu_click_item,
    # Specific controls
    "combobox_select": combobox_select,
    "combobox_get_items": combobox_get_items,
    "listbox_select": listbox_select,
    "listbox_get_selected": listbox_get_selected,
    "tab_select": tab_select,
    "tab_get_selected": tab_get_selected,
    "tree_select": tree_select,
    "tree_expand": tree_expand,
    "tree_collapse": tree_collapse,
    "tree_get_selected": tree_get_selected,
    "slider_get_position": slider_get_position,
    "slider_set_position": slider_set_position,
    "progress_get_position": progress_get_position,
    # Generic escape hatch
    "control_call_method": control_call_method,
    "control_get_attribute": control_get_attribute,
}


# ===========================================================================
# ENHANCED UTILITY TOOLS (v2.0)
# ===========================================================================

def health_check() -> dict[str, Any]:
    """Perform a comprehensive health check of the MCP server and dependencies.

    Returns:
        Dict with overall status, dependency versions, and individual checks.
    """
    checks: dict[str, Any] = {}
    all_ok = True

    # Python
    checks["python"] = {"version": sys.version, "ok": True}

    # pywinauto
    try:
        import pywinauto
        checks["pywinauto"] = {"version": getattr(pywinauto, "__version__", "unknown"), "ok": True}
    except Exception as e:
        checks["pywinauto"] = {"ok": False, "error": str(e)}
        all_ok = False

    # pywin32
    try:
        import win32api
        checks["pywin32"] = {"ok": True}
    except Exception as e:
        checks["pywin32"] = {"ok": False, "error": str(e)}
        all_ok = False

    # comtypes
    try:
        import comtypes
        checks["comtypes"] = {"version": getattr(comtypes, "__version__", "unknown"), "ok": True}
    except Exception as e:
        checks["comtypes"] = {"ok": False, "error": str(e)}
        all_ok = False

    # fastmcp
    try:
        from fastmcp import FastMCP
        checks["fastmcp"] = {"ok": True}
    except Exception as e:
        checks["fastmcp"] = {"ok": False, "error": str(e)}
        all_ok = False

    # OS
    checks["platform"] = {"system": platform.system(), "ok": platform.system() == "Windows"}
    if platform.system() != "Windows":
        all_ok = False

    # Sessions
    with _session_lock:
        checks["sessions"] = {
            "active_apps": len(_app_sessions),
            "active_wrappers": len(_wrapper_sessions),
            "ok": True,
        }

    # Call stats
    with _session_lock:
        total = _call_stats["total_calls"]
        errors = _call_stats["errors"]
        error_rate = (errors / total * 100) if total > 0 else 0
        checks["call_stats"] = {
            "total_calls": total,
            "errors": errors,
            "error_rate_percent": round(error_rate, 2),
            "ok": error_rate < 50,
        }

    # Test basic pywinauto operation
    try:
        from pywinauto import sysinfo as pw_sysinfo
        checks["basic_operation"] = {
            "os_arch": pw_sysinfo.os_arch(),
            "is_x64_os": pw_sysinfo.is_x64_OS(),
            "ok": True,
        }
    except Exception as e:
        checks["basic_operation"] = {"ok": False, "error": str(e)}
        all_ok = False

    return {
        "status": "healthy" if all_ok else "degraded",
        "version": VERSION,
        "build_date": BUILD_DATE,
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
        "all_ok": all_ok,
    }


def get_capabilities() -> dict[str, Any]:
    """Return server capabilities and tool metadata.

    Returns:
        Dict with version, tool count, categories, and supported features.
    """
    from collections import Counter
    categories = Counter()
    tool_list = []
    for name in ALL_FUNCTIONS.keys():
        tool_list.append(name)
        # Infer category from prefix
        if name.startswith("app_"):
            categories["application"] += 1
        elif name.startswith("window_"):
            categories["window"] += 1
        elif name.startswith("control_"):
            categories["control"] += 1
        elif name.startswith("keyboard_"):
            categories["keyboard"] += 1
        elif name.startswith("mouse_"):
            categories["mouse"] += 1
        elif name.startswith("clipboard_"):
            categories["clipboard"] += 1
        elif name.startswith("timings_"):
            categories["timings"] += 1
        elif name.startswith("sysinfo_"):
            categories["system_info"] += 1
        elif name.startswith("find_") or name.startswith("enumerate_"):
            categories["element_finding"] += 1
        elif name.startswith("taskbar_"):
            categories["taskbar"] += 1
        elif name.startswith("desktop_"):
            categories["desktop"] += 1
        elif name.startswith("menu_"):
            categories["menu"] += 1
        elif name.startswith(("combobox_", "listbox_", "tab_", "tree_", "slider_", "progress_")):
            categories["specific_controls"] += 1
        elif name.startswith("workflow_"):
            categories["workflow"] += 1
        elif name.startswith(("safe_", "batch_", "inspect_", "snapshot_")):
            categories["enhanced"] += 1
        else:
            categories["other"] += 1

    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "total_tools": len(ALL_FUNCTIONS),
        "total_workflows": len(WORKFLOWS),
        "executable_workflows": sum(1 for w in WORKFLOWS.values() if w["executable"]),
        "categories": dict(categories),
        "features": [
            "application_lifecycle",
            "window_management",
            "control_interaction",
            "keyboard_mouse_simulation",
            "clipboard_operations",
            "element_discovery",
            "timing_control",
            "workflow_engine",
            "retry_mechanism",
            "input_validation",
            "thread_safe_sessions",
            "session_ttl_auto_cleanup",
            "call_statistics",
            "health_check",
            "safe_operations",
            "batch_execution",
            "state_snapshot",
            "element_inspection",
        ],
        "backends": ["uia", "win32"],
        "transports": ["stdio", "http"],
    }


def get_call_stats(reset: bool = False) -> dict[str, Any]:
    """Get tool call statistics.

    Args:
        reset: If True, reset statistics after reading

    Returns:
        Dict with total calls, errors, and per-tool breakdown
    """
    with _session_lock:
        stats = {
            "total_calls": _call_stats["total_calls"],
            "errors": _call_stats["errors"],
            "error_rate": round(_call_stats["errors"] / _call_stats["total_calls"] * 100, 2) if _call_stats["total_calls"] > 0 else 0,
            "by_tool": dict(_call_stats["by_tool"]),
        }
        if reset:
            _call_stats["total_calls"] = 0
            _call_stats["errors"] = 0
            _call_stats["by_tool"].clear()
    return stats


def safe_click(wrapper_id: str, button: str = "left", retries: int = 3,
               delay: float = 0.5, verify_visible: bool = True,
               verify_enabled: bool = True) -> dict[str, Any]:
    """Click a control with precondition verification and retry.

    Args:
        wrapper_id: Wrapper session ID
        button: Mouse button ('left', 'right', 'middle')
        retries: Number of retry attempts
        delay: Initial delay between retries
        verify_visible: Verify control is visible before clicking
        verify_enabled: Verify control is enabled before clicking

    Returns:
        Dict with click result and attempt count
    """
    _validate_mouse_button(button)

    def _do_click() -> dict[str, Any]:
        wrapper = _get_wrapper(wrapper_id)
        if verify_visible and not wrapper.is_visible():
            raise RuntimeError("Control is not visible")
        if verify_enabled and not wrapper.is_enabled():
            raise RuntimeError("Control is not enabled")
        wrapper.click(button=button)
        return {"clicked": True, "button": button}

    start = time.time()
    try:
        result = _with_retry(_do_click, retries=retries, delay=delay,
                              retry_on=(RuntimeError, ElementNotFoundError, ElementNotEnabled))
        result["attempts"] = retries + 1
        result["elapsed"] = round(time.time() - start, 3)
        return result
    except RetryExhaustedError as e:
        return {
            "clicked": False,
            "error": str(e),
            "attempts": e.attempts,
            "elapsed": round(time.time() - start, 3),
            "suggestions": _classify_error(e.last_error or e)["suggestions"],
        }


def safe_type_text(wrapper_id: str, text: str, clear_first: bool = True,
                   retries: int = 2, delay: float = 0.5,
                   use_clipboard: bool = True) -> dict[str, Any]:
    """Type text into a control with focus verification and retry.

    Args:
        wrapper_id: Wrapper session ID
        text: Text to type
        clear_first: Clear existing text before typing
        retries: Number of retry attempts
        delay: Delay between retries
        use_clipboard: Use clipboard paste for long text (faster, more reliable)

    Returns:
        Dict with typing result
    """
    _validate_nonempty(text, "text")

    def _do_type() -> dict[str, Any]:
        wrapper = _get_wrapper(wrapper_id)
        if not wrapper.is_visible():
            raise RuntimeError("Control is not visible")
        if not wrapper.is_enabled():
            raise RuntimeError("Control is not enabled")
        wrapper.set_focus()
        time.sleep(0.1)
        if clear_first:
            try:
                wrapper.type_keys("^a{DELETE}", with_spaces=True)
            except Exception:
                pass
        if use_clipboard and len(text) > 10:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            wrapper.type_keys("^v", with_spaces=True)
        else:
            wrapper.type_keys(text, with_spaces=True)
        return {"typed": True, "length": len(text), "method": "clipboard" if use_clipboard and len(text) > 10 else "type_keys"}

    start = time.time()
    try:
        result = _with_retry(_do_type, retries=retries, delay=delay,
                              retry_on=(RuntimeError,))
        result["elapsed"] = round(time.time() - start, 3)
        return result
    except RetryExhaustedError as e:
        return {"typed": False, "error": str(e), "attempts": e.attempts}


def inspect_element(wrapper_id: str, depth: int = 2) -> dict[str, Any]:
    """Deep inspect a control element, returning all properties and child structure.

    Args:
        wrapper_id: Wrapper session ID
        depth: Depth of child tree to include

    Returns:
        Comprehensive element info dict
    """
    wrapper = _get_wrapper(wrapper_id)
    info = _wrapper_info(wrapper)

    # Additional properties
    try:
        info["friendly_class_name"] = wrapper.friendly_class_name()
    except Exception:
        pass
    try:
        info["control_count"] = len(wrapper.children())
    except Exception:
        pass
    try:
        info["is_dialog"] = wrapper.is_dialog()
    except Exception:
        pass
    try:
        info["is_active"] = wrapper.is_active()
    except Exception:
        pass
    try:
        info["has_keyboard_focus"] = wrapper.has_keyboard_focus()
    except Exception:
        pass

    # Methods available
    try:
        methods = [m for m in dir(wrapper) if not m.startswith("_") and callable(getattr(wrapper, m))]
        info["available_methods"] = sorted(methods[:50])
        info["method_count"] = len(methods)
    except Exception:
        pass

    # Child tree (shallow)
    if depth > 0:
        try:
            children = []
            for child in wrapper.children()[:20]:
                child_info = _wrapper_info(child)
                children.append(child_info)
            info["children"] = children
        except Exception as e:
            info["children_error"] = str(e)

    return info


def batch_execute(operations: list[dict[str, Any]],
                  stop_on_error: bool = True,
                  continue_on_error: bool = False) -> dict[str, Any]:
    """Execute a batch of operations sequentially.

    Args:
        operations: List of operation dicts, each with 'tool' and 'params' keys
        stop_on_error: If True, stop execution on first error
        continue_on_error: If True, continue on error (overrides stop_on_error)

    Returns:
        Dict with results for each operation and overall status

    Example:
        batch_execute([
            {"tool": "app_start", "params": {"cmd_line": "notepad.exe"}},
            {"tool": "app_top_window", "params": {"app_id": "$prev.app_id$"}},
        ])
    """
    if not operations:
        return {"status": "success", "executed": 0, "results": []}

    results = []
    context: dict[str, Any] = {}
    start = time.time()
    errors = 0

    for i, op in enumerate(operations):
        tool_name = op.get("tool")
        params = op.get("params", {})

        if not tool_name:
            results.append({"index": i, "status": "error", "error": "Missing 'tool' key"})
            errors += 1
            if stop_on_error and not continue_on_error:
                break
            continue

        if tool_name not in ALL_FUNCTIONS:
            results.append({"index": i, "tool": tool_name, "status": "error",
                           "error": f"Unknown tool: {tool_name}"})
            errors += 1
            if stop_on_error and not continue_on_error:
                break
            continue

        # Resolve $prev.field$ references
        resolved_params = {}
        for key, val in params.items():
            if isinstance(val, str) and val.startswith("$prev."):
                field = val[6:]  # Remove "$prev."
                # Look through previous results for this field
                for prev in reversed(results):
                    if "data" in prev and field in prev["data"]:
                        resolved_params[key] = prev["data"][field]
                        break
                else:
                    resolved_params[key] = val
            elif isinstance(val, str) and val.startswith("$") and val.endswith("$"):
                var_name = val[1:-1]
                resolved_params[key] = context.get(var_name, val)
            else:
                resolved_params[key] = val

        try:
            func = ALL_FUNCTIONS[tool_name]
            sig_params = set(inspect.signature(func).parameters.keys())
            filtered = {k: v for k, v in resolved_params.items() if k in sig_params}
            result = func(**filtered)
            results.append({"index": i, "tool": tool_name, "status": "success", "data": result})
            # Store result fields in context
            if isinstance(result, dict):
                for k, v in result.items():
                    context[f"last_{k}"] = v
        except Exception as e:
            errors += 1
            classified = _classify_error(e)
            results.append({"index": i, "tool": tool_name, "status": "error",
                           "error": str(e), "error_type": classified["error_type"],
                           "category": classified["category"], "suggestions": classified["suggestions"]})
            if stop_on_error and not continue_on_error:
                break

    elapsed = round(time.time() - start, 3)
    return {
        "status": "success" if errors == 0 else "partial" if errors < len(operations) else "failed",
        "total": len(operations),
        "executed": len(results),
        "succeeded": len(results) - errors,
        "failed": errors,
        "elapsed_seconds": elapsed,
        "results": results,
    }


def snapshot_ui_state(wrapper_id: Optional[str] = None) -> dict[str, Any]:
    """Capture a snapshot of the current UI state for later comparison.

    Args:
        wrapper_id: If provided, snapshot this window/control; otherwise snapshot desktop

    Returns:
        Dict with snapshot data (control tree, text values, states)
    """
    snapshot = {"timestamp": datetime.now().isoformat(), "elements": []}

    def _capture(w, depth=0, max_depth=3):
        if depth > max_depth:
            return
        try:
            info = {
                "depth": depth,
                "class_name": w.class_name(),
                "text": w.window_text(),
                "control_id": w.control_id(),
                "is_visible": w.is_visible(),
                "is_enabled": w.is_enabled(),
                "rect": _rect_to_dict(w.rectangle()),
            }
            try:
                info["friendly_class"] = w.friendly_class_name()
            except Exception:
                pass
            try:
                if hasattr(w, "is_checked"):
                    info["is_checked"] = w.is_checked()
            except Exception:
                pass
            try:
                if hasattr(w, "selected_index"):
                    info["selected_index"] = w.selected_index()
            except Exception:
                pass
            snapshot["elements"].append(info)
        except Exception:
            pass
        try:
            for child in w.children():
                _capture(child, depth + 1, max_depth)
        except Exception:
            pass

    if wrapper_id:
        wrapper = _get_wrapper(wrapper_id)
        _capture(wrapper)
    else:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        for win in desktop.windows()[:10]:
            _capture(win)

    snapshot["element_count"] = len(snapshot["elements"])
    return snapshot


def cleanup_stale_sessions() -> dict[str, Any]:
    """Clean up sessions that have exceeded the TTL (2 hours).

    Returns:
        Dict with counts of removed sessions
    """
    result = _cleanup_expired_sessions()
    result["ttl_hours"] = _SESSION_TTL.total_seconds() / 3600
    return result


def classify_error(error_message: str) -> dict[str, Any]:
    """Classify an error message and provide recovery suggestions.

    Args:
        error_message: The error message string to classify

    Returns:
        Dict with category, likely cause, and suggestions
    """
    class FakeError(Exception):
        pass
    e = FakeError(error_message)
    return _classify_error(e)


# Add enhanced tools to ALL_FUNCTIONS
ALL_FUNCTIONS["health_check"] = health_check
ALL_FUNCTIONS["get_capabilities"] = get_capabilities
ALL_FUNCTIONS["get_call_stats"] = get_call_stats
ALL_FUNCTIONS["safe_click"] = safe_click
ALL_FUNCTIONS["safe_type_text"] = safe_type_text
ALL_FUNCTIONS["inspect_element"] = inspect_element
ALL_FUNCTIONS["batch_execute"] = batch_execute
ALL_FUNCTIONS["snapshot_ui_state"] = snapshot_ui_state
ALL_FUNCTIONS["cleanup_stale_sessions"] = cleanup_stale_sessions
ALL_FUNCTIONS["classify_error"] = classify_error


# ===========================================================================
# WORKFLOW ENGINE — 100 条桌面 GUI 常用工作流
# ===========================================================================

def _resolve_params(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Resolve $variable$ placeholders in params using context and input params."""
    resolved = {}
    for key, val in params.items():
        if isinstance(val, str) and val.startswith("$") and val.endswith("$"):
            var_name = val[1:-1]
            resolved[key] = context.get(var_name, val)
        elif isinstance(val, dict):
            resolved[key] = _resolve_params(val, context)
        elif isinstance(val, list):
            resolved[key] = [_resolve_params({"_": v}, context)["_"] if isinstance(v, str) and v.startswith("$") else v for v in val]
        else:
            resolved[key] = val
    return resolved


def _evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a simple condition expression against context.

    Supports:
      - $var$ == "value" / $var$ != "value"
      - $var$ > number / $var$ < number
      - $var$ (truthy check)
      - not $var$
      - Multiple conditions with 'and' / 'or'

    Args:
        condition: Condition string
        context: Context dict with variables

    Returns:
        Boolean result
    """
    if not condition:
        return True

    expr = condition.strip()

    # Handle 'or' (lower precedence)
    if " or " in expr:
        parts = expr.split(" or ", 1)
        return _evaluate_condition(parts[0], context) or _evaluate_condition(parts[1], context)

    # Handle 'and'
    if " and " in expr:
        parts = expr.split(" and ", 1)
        return _evaluate_condition(parts[0], context) and _evaluate_condition(parts[1], context)

    # Handle 'not'
    if expr.startswith("not "):
        return not _evaluate_condition(expr[4:], context)

    # Resolve $var$ references (supports dotted paths like $health.status$)
    def _resolve(match: re.Match) -> str:
        var_path = match.group(1)
        # Navigate dotted path in context
        val: Any = context
        for part in var_path.split("."):
            if isinstance(val, dict):
                val = val.get(part, "")
            else:
                val = getattr(val, part, "")
        if isinstance(val, bool):
            return str(val).lower()
        return str(val)

    _VAR_PATTERN = r"\$([\w.]+)\$"

    # Comparison operators
    for op in ["==", "!=", ">=", "<=", ">", "<"]:
        if op in expr:
            left, right = expr.split(op, 1)
            left = left.strip()
            right = right.strip()

            # Resolve variables
            left_val = re.sub(_VAR_PATTERN, _resolve, left)
            right_val = re.sub(_VAR_PATTERN, _resolve, right)

            # Strip quotes from string literals
            if (right_val.startswith('"') and right_val.endswith('"')) or \
               (right_val.startswith("'") and right_val.endswith("'")):
                right_val = right_val[1:-1]

            if op == "==":
                return str(left_val) == str(right_val)
            elif op == "!=":
                return str(left_val) != str(right_val)
            else:
                try:
                    l = float(left_val)
                    r = float(right_val)
                    if op == ">":
                        return l > r
                    elif op == "<":
                        return l < r
                    elif op == ">=":
                        return l >= r
                    elif op == "<=":
                        return l <= r
                except (ValueError, TypeError):
                    return False

    # Simple truthy check: $var$ (supports dotted paths)
    var_match = re.match(r"^\$([\w.]+)\$$", expr)
    if var_match:
        var_path = var_match.group(1)
        val: Any = context
        for part in var_path.split("."):
            if isinstance(val, dict):
                val = val.get(part, None)
            else:
                val = getattr(val, part, None)
            if val is None:
                return False
        return bool(val)

    # Literal boolean
    if expr.lower() == "true":
        return True
    if expr.lower() == "false":
        return False

    logger.warning("Could not evaluate condition: %s", expr)
    return False


def _execute_step(step: dict[str, Any], context: dict[str, Any],
                   step_index: int = 0) -> dict[str, Any]:
    """Execute a single workflow step with enhanced features.

    Enhanced step schema:
      {
        "tool": "function_name",
        "params": {...},
        "output_key": "var_name",
        "wait": 0.5,
        "condition": "$var$ == 'value'",  # skip if false
        "retries": 3,                       # retry on failure
        "retry_delay": 0.5,
        "timeout": 10.0,                    # step timeout in seconds
        "ignore_error": false,              # continue on error
        "description": "Step description"
      }

    Returns:
        Dict with status, result, and metadata
    """
    tool_name = step.get("tool")
    description = step.get("description", tool_name or "unknown")

    # Check condition
    condition = step.get("condition")
    if condition and not _evaluate_condition(condition, context):
        logger.debug("Step %d skipped (condition false): %s", step_index, condition)
        return {"status": "skipped", "reason": "condition_false", "tool": tool_name,
                "description": description}

    if not tool_name:
        raise ValueError(f"Step {step_index}: missing 'tool' key")

    if tool_name not in ALL_FUNCTIONS:
        raise ValueError(f"Step {step_index}: unknown tool '{tool_name}'")

    retries = step.get("retries", 0)
    retry_delay = step.get("retry_delay", 0.5)
    timeout = step.get("timeout")
    ignore_error = step.get("ignore_error", False)

    def _do_execute() -> Any:
        params = step.get("params", {})
        resolved = _resolve_params(params, context)

        func = ALL_FUNCTIONS[tool_name]
        sig_params = set(inspect.signature(func).parameters.keys())
        filtered = {k: v for k, v in resolved.items() if k in sig_params}

        if timeout:
            return _with_timeout(func, timeout, **filtered)
        return func(**filtered)

    start = time.time()
    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            result = _do_execute()

            # Store result in context
            output_key = step.get("output_key")
            if output_key:
                if isinstance(result, dict) and output_key in result:
                    context[output_key] = result[output_key]
                else:
                    context[output_key] = result

            # Wait after step
            wait_time = step.get("wait", 0)
            if wait_time > 0:
                time.sleep(wait_time)

            return {
                "status": "success",
                "tool": tool_name,
                "description": description,
                "result": result,
                "attempts": attempt + 1,
                "elapsed": round(time.time() - start, 3),
            }
        except Exception as e:
            last_error = e
            if attempt < retries:
                logger.debug("Step %d retry %d/%d: %s", step_index, attempt + 1, retries, e)
                time.sleep(retry_delay * (2 ** attempt))
            elif ignore_error:
                logger.warning("Step %d error ignored: %s", step_index, e)
                return {
                    "status": "error_ignored",
                    "tool": tool_name,
                    "description": description,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "attempts": retries + 1,
                    "elapsed": round(time.time() - start, 3),
                }

    # All retries exhausted
    classified = _classify_error(last_error) if last_error else {}
    return {
        "status": "error",
        "tool": tool_name,
        "description": description,
        "error": str(last_error) if last_error else "Unknown error",
        "error_type": type(last_error).__name__ if last_error else "Unknown",
        "category": classified.get("category", "unknown"),
        "suggestions": classified.get("suggestions", []),
        "attempts": retries + 1,
        "elapsed": round(time.time() - start, 3),
    }


# Workflow registry: workflow_id -> {name, description, category, steps, executable}
WORKFLOWS: dict[str, dict[str, Any]] = {}


def _register_workflow(wf_id: str, name: str, description: str, category: str,
                        steps: Optional[list[dict[str, Any]]] = None,
                        executable: bool = True) -> None:
    """Register a workflow in the registry."""
    WORKFLOWS[wf_id] = {
        "id": wf_id,
        "name": name,
        "description": description,
        "category": category,
        "steps": steps or [],
        "executable": executable and steps is not None and len(steps) > 0,
    }


# --- WF001: 启动应用并等待主窗口 ---
_register_workflow("WF001", "启动应用并等待主窗口",
    "启动应用程序，等待其主窗口出现并获取窗口句柄。",
    "应用生命周期",
    steps=[
        {"tool": "app_start", "params": {"cmd_line": "$cmd_line$", "backend": "$backend$", "timeout": "$timeout$"}, "output_key": "app_id", "wait": 1},
        {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "wrapper_id", "wait": 0.5},
    ])

# --- WF002: 连接到已运行应用 ---
_register_workflow("WF002", "连接到已运行应用",
    "连接到已经在运行的应用程序（按标题/进程/路径匹配）。",
    "应用生命周期",
    steps=[
        {"tool": "app_connect", "params": {"backend": "$backend$", "title": "$title$", "process": "$process$", "path": "$path$"}, "output_key": "app_id", "wait": 0.5},
        {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "wrapper_id"},
    ])

# --- WF003: 安全关闭应用 ---
_register_workflow("WF003", "安全关闭应用",
    "优雅地关闭应用（先尝试正常关闭，超时后强制终止）。",
    "应用生命周期",
    steps=[
        {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "wrapper_id"},
        {"tool": "control_close", "params": {"wrapper_id": "$wrapper_id$"}, "wait": 2},
        {"tool": "app_is_process_running", "params": {"app_id": "$app_id$"}, "output_key": "still_running"},
    ])

# --- WF006: 查找并聚焦窗口 ---
_register_workflow("WF006", "查找并聚焦窗口",
    "按标题查找窗口并将其置于前台。",
    "窗口管理",
    steps=[
        {"tool": "desktop_window", "params": {"backend": "$backend$", "title": "$title$", "title_re": "$title_re$"}, "output_key": "wrapper_id", "wait": 0.3},
        {"tool": "control_set_focus", "params": {"wrapper_id": "$wrapper_id$"}, "wait": 0.3},
    ])

# --- WF009: 窗口截图并保存 ---
_register_workflow("WF009", "窗口截图并保存",
    "截取指定窗口的完整内容并保存为图片文件。",
    "窗口管理",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$wrapper_id$"}, "wait": 0.3},
        {"tool": "control_capture_as_image", "params": {"wrapper_id": "$wrapper_id$", "save_path": "$save_path$"}, "output_key": "screenshot"},
    ])

# --- WF011: 安全输入文本到编辑框 ---
_register_workflow("WF011", "安全输入文本到编辑框",
    "定位编辑框，清空原有内容，输入新文本（支持特殊字符）。",
    "文本输入与编辑",
    steps=[
        {"tool": "control_child_window", "params": {"wrapper_id": "$wrapper_id$", "control_type": "Edit", "found_index": "$found_index$"}, "output_key": "edit_id", "wait": 0.2},
        {"tool": "control_set_focus", "params": {"wrapper_id": "$edit_id$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^a"}, "wait": 0.1},
        {"tool": "keyboard_send_keys", "params": {"keys": "{DELETE}"}, "wait": 0.1},
        {"tool": "clipboard_set_data", "params": {"text": "$text$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^v"}, "wait": 0.2},
    ])

# --- WF012: 追加文本到编辑框 ---
_register_workflow("WF012", "追加文本到编辑框",
    "在编辑框现有内容末尾追加文本。",
    "文本输入与编辑",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$edit_id$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^{END}"}, "wait": 0.1},
        {"tool": "clipboard_set_data", "params": {"text": "$text$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^v"}, "wait": 0.1},
    ])

# --- WF015: 撤销/重做/全选/复制/粘贴组合 ---
_register_workflow("WF015", "标准编辑操作序列",
    "对当前焦点控件执行标准编辑操作序列（全选/复制/剪切/粘贴/撤销/重做）。",
    "文本输入与编辑",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$edit_id$"}},
    ])

# --- WF016: 安全点击按钮 ---
_register_workflow("WF016", "安全点击按钮",
    "定位按钮，验证其可用且可见，然后点击（带重试）。",
    "按钮与控件交互",
    steps=[
        {"tool": "control_child_window", "params": {"wrapper_id": "$wrapper_id$", "control_type": "Button", "title": "$title$", "auto_id": "$auto_id$", "found_index": "$found_index$"}, "output_key": "btn_id", "wait": 0.2},
        {"tool": "control_is_enabled", "params": {"wrapper_id": "$btn_id$"}, "output_key": "enabled"},
        {"tool": "control_is_visible", "params": {"wrapper_id": "$btn_id$"}, "output_key": "visible"},
        {"tool": "control_click", "params": {"wrapper_id": "$btn_id$"}, "wait": 0.3},
    ])

# --- WF017: 切换复选框状态 ---
_register_workflow("WF017", "切换复选框状态",
    "将复选框设置为指定状态（勾选/取消勾选）。",
    "按钮与控件交互",
    steps=[
        {"tool": "control_is_checked", "params": {"wrapper_id": "$checkbox_id$"}, "output_key": "current_state"},
        {"tool": "control_click", "params": {"wrapper_id": "$checkbox_id$"}, "wait": 0.2},
    ])

# --- WF021: 通过菜单栏选择菜单项 ---
_register_workflow("WF021", "通过菜单栏选择菜单项",
    "通过窗口菜单栏选择指定路径的菜单项（如 File > Save As）。",
    "菜单与导航",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$wrapper_id$"}},
        {"tool": "control_menu_select", "params": {"wrapper_id": "$wrapper_id$", "path": "$menu_path$"}, "wait": 0.5},
    ])

# --- WF026: 从组合框选择项 ---
_register_workflow("WF026", "从组合框选择项",
    "展开组合框，从下拉列表中选择指定项。",
    "列表与组合框",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$combo_id$"}},
        {"tool": "combobox_get_items", "params": {"wrapper_id": "$combo_id$"}, "output_key": "items"},
        {"tool": "combobox_select", "params": {"wrapper_id": "$combo_id$", "item": "$item_text$"}, "wait": 0.3},
        {"tool": "control_selected_text", "params": {"wrapper_id": "$combo_id$"}, "output_key": "selected"},
    ])

# --- WF027: 获取列表框全部项 ---
_register_workflow("WF027", "获取列表框全部项",
    "提取列表框中所有项的文本，返回完整列表。",
    "列表与组合框",
    steps=[
        {"tool": "control_get_item_texts", "params": {"wrapper_id": "$list_id$"}, "output_key": "items"},
    ])

# --- WF036: 处理确认对话框（是/否） ---
_register_workflow("WF036", "处理确认对话框",
    "自动检测并响应 Yes/No 确认对话框。",
    "对话框处理",
    steps=[
        {"tool": "desktop_window", "params": {"control_type": "Window", "title_re": "$title_re$"}, "output_key": "dialog_id", "wait": 0.3},
        {"tool": "control_child_window", "params": {"wrapper_id": "$dialog_id$", "control_type": "Button", "title": "$button_title$"}, "output_key": "btn_id", "wait": 0.2},
        {"tool": "control_click", "params": {"wrapper_id": "$btn_id$"}, "wait": 0.5},
    ])

# --- WF037: 处理 OK 对话框 ---
_register_workflow("WF037", "处理 OK 对话框",
    "检测并点击消息框的确定/OK按钮。",
    "对话框处理",
    steps=[
        {"tool": "desktop_window", "params": {"title_re": "$title_re$"}, "output_key": "dialog_id", "wait": 0.3},
        {"tool": "control_child_window", "params": {"wrapper_id": "$dialog_id$", "control_type": "Button", "title": "确定"}, "output_key": "ok_btn_id", "wait": 0.2},
        {"tool": "control_click", "params": {"wrapper_id": "$ok_btn_id$"}, "wait": 0.3},
    ])

# --- WF041: 全局保存（Ctrl+S） ---
_register_workflow("WF041", "全局保存",
    "对当前活动窗口执行保存操作（Ctrl+S）。",
    "键盘快捷键",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$wrapper_id$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^s"}, "wait": 1},
    ])

# --- WF042: 全局复制粘贴文本 ---
_register_workflow("WF042", "复制粘贴文本",
    "从源控件复制文本，粘贴到目标控件。",
    "键盘快捷键",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$source_id$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^a"}, "wait": 0.1},
        {"tool": "keyboard_send_keys", "params": {"keys": "^c"}, "wait": 0.2},
        {"tool": "control_set_focus", "params": {"wrapper_id": "$target_id$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^a{DELETE}"}, "wait": 0.1},
        {"tool": "keyboard_send_keys", "params": {"keys": "^v"}, "wait": 0.2},
    ])

# --- WF046: 点击屏幕坐标 ---
_register_workflow("WF046", "点击屏幕坐标",
    "在屏幕指定坐标处执行点击。",
    "鼠标操作",
    steps=[
        {"tool": "mouse_move", "params": {"x": "$x$", "y": "$y$"}, "wait": 0.1},
        {"tool": "mouse_click", "params": {"button": "$button$", "x": "$x$", "y": "$y$", "double": "$double$"}},
    ])

# --- WF047: 拖拽文件/对象 ---
_register_workflow("WF047", "拖拽操作",
    "从源坐标拖拽到目标坐标。",
    "鼠标操作",
    steps=[
        {"tool": "mouse_move", "params": {"x": "$src_x$", "y": "$src_y$"}, "wait": 0.2},
        {"tool": "mouse_press", "params": {"button": "$button$", "x": "$src_x$", "y": "$src_y$"}},
        {"tool": "mouse_move", "params": {"x": "$dst_x$", "y": "$dst_y$"}, "wait": 0.3},
        {"tool": "mouse_release", "params": {"button": "$button$", "x": "$dst_x$", "y": "$dst_y$"}},
    ])

# --- WF049: 鼠标滚轮滚动 ---
_register_workflow("WF049", "鼠标滚轮滚动",
    "在指定位置滚动鼠标滚轮。",
    "鼠标操作",
    steps=[
        {"tool": "mouse_move", "params": {"x": "$x$", "y": "$y$"}},
        {"tool": "mouse_scroll", "params": {"direction": "$direction$", "amount": "$amount$"}},
    ])

# --- WF051: 提取窗口全部文本 ---
_register_workflow("WF051", "提取窗口全部文本",
    "递归提取窗口及其所有子控件的文本内容。",
    "数据提取",
    steps=[
        {"tool": "window_dump_tree", "params": {"wrapper_id": "$wrapper_id$", "depth": "$depth$"}, "output_key": "tree_dump"},
        {"tool": "control_descendants", "params": {"wrapper_id": "$wrapper_id$"}, "output_key": "descendants"},
    ])

# --- WF054: 提取控件属性快照 ---
_register_workflow("WF054", "提取控件属性快照",
    "获取控件的所有可用属性，用于调试和定位。",
    "数据提取",
    steps=[
        {"tool": "control_get_properties", "params": {"wrapper_id": "$wrapper_id$"}, "output_key": "properties"},
        {"tool": "control_get_rectangle", "params": {"wrapper_id": "$wrapper_id$"}, "output_key": "rectangle"},
        {"tool": "control_get_class_name", "params": {"wrapper_id": "$wrapper_id$"}, "output_key": "class_name"},
        {"tool": "control_is_visible", "params": {"wrapper_id": "$wrapper_id$"}, "output_key": "visible"},
        {"tool": "control_is_enabled", "params": {"wrapper_id": "$wrapper_id$"}, "output_key": "enabled"},
    ])

# --- WF055: 提取窗口列表及状态 ---
_register_workflow("WF055", "枚举所有顶层窗口",
    "枚举当前所有顶层窗口，返回标题、类名、进程、状态等信息。",
    "数据提取",
    steps=[
        {"tool": "enumerate_windows", "params": {"backend": "$backend$"}, "output_key": "windows"},
    ])

# --- WF056: 等待窗口出现并验证 ---
_register_workflow("WF056", "等待窗口出现",
    "等待指定标题的窗口出现，验证其可见且可用。",
    "验证与等待",
    steps=[
        {"tool": "desktop_window", "params": {"backend": "$backend$", "title": "$title$", "title_re": "$title_re$"}, "output_key": "wrapper_id", "wait": 0.5},
        {"tool": "window_wait", "params": {"wrapper_id": "$wrapper_id$", "wait_for": "ready", "timeout": "$timeout$"}},
    ])

# --- WF057: 验证控件文本 ---
_register_workflow("WF057", "验证控件文本",
    "检查控件的文本是否包含预期内容。",
    "验证与等待",
    steps=[
        {"tool": "control_get_text", "params": {"wrapper_id": "$wrapper_id$"}, "output_key": "actual_text"},
    ])

# --- WF061: 在浏览器地址栏输入 URL ---
_register_workflow("WF061", "浏览器导航到 URL",
    "聚焦浏览器窗口，在地址栏输入 URL 并导航。",
    "浏览器自动化",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$browser_id$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^l"}, "wait": 0.3},
        {"tool": "clipboard_set_data", "params": {"text": "$url$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^v"}, "wait": 0.2},
        {"tool": "keyboard_send_keys", "params": {"keys": "{ENTER}"}, "wait": 1},
    ])

# --- WF062: 浏览器标签页管理 ---
_register_workflow("WF062", "浏览器标签页操作",
    "新建、切换、关闭浏览器标签页。",
    "浏览器自动化",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$browser_id$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "$shortcut$"}, "wait": 0.5},
    ])

# --- WF066: 通过开始菜单启动应用 ---
_register_workflow("WF066", "通过开始菜单启动应用",
    "打开开始菜单，搜索并启动指定应用程序。",
    "系统操作",
    steps=[
        {"tool": "keyboard_send_keys", "params": {"keys": "{VK_LWIN}"}, "wait": 0.5},
        {"tool": "taskbar_get_search_edit", "params": {}, "output_key": "search_id"},
        {"tool": "control_set_focus", "params": {"wrapper_id": "$search_id$"}},
        {"tool": "clipboard_set_data", "params": {"text": "$app_name$"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "^v"}, "wait": 1},
        {"tool": "keyboard_send_keys", "params": {"keys": "{ENTER}"}, "wait": 2},
    ])

# --- WF068: 切换活动窗口 ---
_register_workflow("WF068", "切换活动窗口",
    "通过 Alt+Tab 在打开的窗口之间切换到指定应用。",
    "系统操作",
    steps=[
        {"tool": "desktop_active_window", "params": {}, "output_key": "current_window"},
        {"tool": "keyboard_key_press", "params": {"key": "VK_MENU"}},
        {"tool": "keyboard_send_keys", "params": {"keys": "{TAB}"}, "wait": 0.3},
        {"tool": "keyboard_key_release", "params": {"key": "VK_MENU"}},
    ])

# --- WF071: 截取指定窗口 ---
_register_workflow("WF071", "截取窗口截图",
    "截取指定窗口的完整内容并保存为图片。",
    "截图与捕获",
    steps=[
        {"tool": "control_set_focus", "params": {"wrapper_id": "$wrapper_id$"}, "wait": 0.3},
        {"tool": "control_capture_as_image", "params": {"wrapper_id": "$wrapper_id$", "save_path": "$save_path$"}, "output_key": "screenshot"},
    ])

# --- WF073: 截取控件元素 ---
_register_workflow("WF073", "截取控件截图",
    "截取窗口中特定控件的图像。",
    "截图与捕获",
    steps=[
        {"tool": "control_child_window", "params": {"wrapper_id": "$wrapper_id$", "control_type": "$control_type$", "title": "$title$", "auto_id": "$auto_id$"}, "output_key": "control_id", "wait": 0.2},
        {"tool": "control_capture_as_image", "params": {"wrapper_id": "$control_id$", "save_path": "$save_path$"}, "output_key": "screenshot"},
    ])

# --- WF076: 填写文本字段组 ---
_register_workflow("WF076", "填写文本字段组",
    "按顺序填写表单中的多个文本输入框（通过 Tab 键导航）。",
    "表单填写",
    steps=[
        {"tool": "control_child_window", "params": {"wrapper_id": "$form_id$", "control_type": "Edit", "found_index": 0}, "output_key": "first_id", "wait": 0.2},
        {"tool": "control_click", "params": {"wrapper_id": "$first_id"}},
    ])

# --- WF080: 提交表单并验证结果 ---
_register_workflow("WF080", "提交表单",
    "填写表单后点击提交按钮，等待结果。",
    "表单填写",
    steps=[
        {"tool": "control_child_window", "params": {"wrapper_id": "$form_id$", "control_type": "Button", "title": "$submit_title$", "auto_id": "$submit_auto_id$"}, "output_key": "submit_btn_id", "wait": 0.2},
        {"tool": "control_click", "params": {"wrapper_id": "$submit_btn_id$"}, "wait": 1},
    ])

# --- WF091: 切换到指定标签页 ---
_register_workflow("WF091", "切换标签页",
    "在 Tab 控件中切换到指定标题或索引的标签页。",
    "标签页操作",
    steps=[
        {"tool": "control_child_window", "params": {"wrapper_id": "$tab_id$", "control_type": "TabItem", "title": "$tab_title$", "found_index": "$tab_index$"}, "output_key": "tab_item_id", "wait": 0.2},
        {"tool": "control_click", "params": {"wrapper_id": "$tab_item_id$"}, "wait": 0.3},
    ])

# --- WF092: 获取所有标签页信息 ---
_register_workflow("WF092", "获取所有标签页",
    "提取 Tab 控件中所有标签页的标题、选中状态、索引。",
    "标签页操作",
    steps=[
        {"tool": "control_children", "params": {"wrapper_id": "$tab_id$"}, "output_key": "tabs"},
    ])

# --- Non-executable workflows (guide only, full steps in references/workflows.md) ---
_guide_workflows = [
    ("WF004", "重启应用", "关闭并重新启动应用程序。", "应用生命周期"),
    ("WF005", "批量启动多个应用", "依次启动多个应用程序。", "应用生命周期"),
    ("WF007", "窗口排列（平铺/层叠）", "将多个窗口按指定方式排列。", "窗口管理"),
    ("WF008", "最小化所有非活动窗口", "最小化除当前活动窗口外的所有顶层窗口。", "窗口管理"),
    ("WF010", "监控窗口出现/消失", "等待指定标题的窗口出现或消失。", "窗口管理"),
    ("WF013", "替换编辑框中的指定文本", "查找编辑框中的指定文本并替换为新文本。", "文本输入与编辑"),
    ("WF014", "多行文本批量输入", "向多行文本编辑器逐行输入文本。", "文本输入与编辑"),
    ("WF018", "选择单选按钮", "在一组单选按钮中选择指定的选项。", "按钮与控件交互"),
    ("WF019", "切换开关/Toggle 控件", "切换 UIA Toggle 控件到指定状态。", "按钮与控件交互"),
    ("WF020", "批量点击多个按钮", "按顺序点击多个按钮。", "按钮与控件交互"),
    ("WF022", "获取菜单全部项并选择", "先获取菜单的所有项，再根据文本选择指定项。", "菜单与导航"),
    ("WF023", "右键菜单操作", "在指定控件上右键点击，然后从上下文菜单中选择项。", "菜单与导航"),
    ("WF024", "键盘快捷键打开菜单", "使用 Alt 键激活菜单栏，然后用方向键导航。", "菜单与导航"),
    ("WF025", "最近打开文件列表选择", "从应用的最近打开文件菜单中选择指定文件。", "菜单与导航"),
    ("WF028", "列表多选（Ctrl+点击）", "在支持多选的列表中选择多个项。", "列表与组合框"),
    ("WF029", "列表项双击打开", "在列表/文件浏览器中双击指定项以打开。", "列表与组合框"),
    ("WF030", "动态添加项到列表", "通过应用的添加按钮/对话框向列表中添加新项。", "列表与组合框"),
    ("WF031", "在打开对话框中选择文件", "在标准 Windows 打开文件对话框中输入路径并打开文件。", "文件对话框操作"),
    ("WF032", "在另存为对话框中保存文件", "在标准另存为对话框中设置文件名和保存类型。", "文件对话框操作"),
    ("WF033", "浏览文件夹对话框导航", "在浏览文件夹对话框中导航到指定目录并确认。", "文件对话框操作"),
    ("WF034", "取消文件对话框", "安全地关闭打开/保存文件对话框。", "文件对话框操作"),
    ("WF035", "从文件对话框获取文件列表", "提取文件对话框中当前目录的所有文件和文件夹名称。", "文件对话框操作"),
    ("WF038", "处理错误/警告对话框", "检测错误或警告对话框，记录消息内容，然后关闭。", "对话框处理"),
    ("WF039", "处理进度对话框", "等待带进度条的对话框完成。", "对话框处理"),
    ("WF040", "批量处理弹出对话框", "在执行主操作过程中，自动处理可能出现的各种弹出对话框。", "对话框处理"),
    ("WF043", "应用快捷键序列", "对指定窗口依次执行多个键盘快捷键组合。", "键盘快捷键"),
    ("WF044", "功能键操作（F1-F12）", "发送功能键（F1 帮助、F2 重命名、F5 刷新等）。", "键盘快捷键"),
    ("WF045", "系统级快捷键", "发送 Windows 系统级快捷键（Win+D、Alt+Tab、Win+L 等）。", "键盘快捷键"),
    ("WF048", "鼠标悬停显示提示", "将鼠标悬停在控件上，等待工具提示出现并提取文本。", "鼠标操作"),
    ("WF050", "画框选择（拖拽选择区域）", "在画布/桌面/图像编辑器中拖拽画框选择区域。", "鼠标操作"),
    ("WF052", "提取表单所有字段值", "从表单对话框中提取所有输入字段的当前值。", "数据提取"),
    ("WF053", "提取表格/数据网格全部数据", "从 DataGrid/ListView 控件中提取所有行和列的数据。", "数据提取"),
    ("WF058", "等待控件状态变化", "等待控件的可见性/可用性/文本发生变化。", "验证与等待"),
    ("WF059", "验证按钮点击后状态变化", "点击按钮前后验证控件状态变化。", "验证与等待"),
    ("WF060", "轮询验证直到条件满足", "反复执行验证函数，直到条件满足或超时。", "验证与等待"),
    ("WF063", "浏览器表单填写", "在网页表单中填写文本字段（通过 Tab 键导航）。", "浏览器自动化"),
    ("WF064", "浏览器截图整页", "截取浏览器当前页面的完整截图。", "浏览器自动化"),
    ("WF065", "浏览器下载文件处理", "触发浏览器下载，等待下载完成，获取下载的文件路径。", "浏览器自动化"),
    ("WF067", "任务栏操作", "点击任务栏上的应用图标、系统托盘图标，或切换活动窗口。", "系统操作"),
    ("WF069", "系统托盘图标菜单操作", "右键点击系统托盘图标，从弹出菜单中选择指定项。", "系统操作"),
    ("WF070", "锁定/休眠/关机", "执行系统级操作（锁定工作站、休眠、关机、重启）。", "系统操作"),
    ("WF072", "截取屏幕区域", "截取屏幕指定矩形区域的内容。", "截图与捕获"),
    ("WF074", "定时连续截图", "按指定间隔连续截取屏幕/窗口。", "截图与捕获"),
    ("WF075", "对比截图检测变化", "截取当前窗口图像，与参考截图对比，检测 UI 变化。", "截图与捕获"),
    ("WF077", "填写带标签的表单", "通过标签文本定位对应的输入框，填写表单。", "表单填写"),
    ("WF078", "选择表单中的下拉选项", "为表单中的多个组合框/下拉列表选择指定选项。", "表单填写"),
    ("WF079", "设置表单复选框组", "批量设置表单中多个复选框的勾选状态。", "表单填写"),
    ("WF081", "选择表格行", "在 DataGrid/ListView 中选择指定行。", "表格/网格操作"),
    ("WF082", "获取表格单元格值", "获取 DataGrid/ListView 中指定行和列的单元格文本值。", "表格/网格操作"),
    ("WF083", "编辑表格单元格", "双击进入单元格编辑模式，输入新值，确认编辑。", "表格/网格操作"),
    ("WF084", "表格列排序", "点击表头列标题对表格数据进行排序。", "表格/网格操作"),
    ("WF085", "表格数据导出", "提取表格全部数据，导出为 CSV/JSON 格式文件。", "表格/网格操作"),
    ("WF086", "展开树节点路径", "按路径依次展开树控件中的节点。", "树控件操作"),
    ("WF087", "选择树节点", "按路径选择树控件中的指定节点。", "树控件操作"),
    ("WF088", "获取树节点子项", "获取指定树节点的所有直接子节点名称和状态。", "树控件操作"),
    ("WF089", "树节点重命名", "选中树节点，按 F2 进入重命名，输入新名称，确认。", "树控件操作"),
    ("WF090", "树节点拖拽排序", "将树节点从一个位置拖拽到另一个位置。", "树控件操作"),
    ("WF093", "关闭标签页", "关闭指定标签页（点击关闭按钮或使用快捷键）。", "标签页操作"),
    ("WF094", "新建标签页", "在 Tab 控件中新建标签页。", "标签页操作"),
    ("WF095", "遍历所有标签页提取内容", "依次切换到每个标签页，提取页面内容/文本，汇总返回。", "标签页操作"),
    ("WF096", "带重试的点击操作", "尝试点击控件，如果失败则等待后重试。", "错误恢复与重试"),
    ("WF097", "应用崩溃恢复", "检测应用是否崩溃，如果崩溃则重启并恢复状态。", "错误恢复与重试"),
    ("WF098", "对话框意外弹出处理", "在执行主操作时，监控并自动处理意外弹出的对话框。", "错误恢复与重试"),
    ("WF099", "超时回退策略", "尝试主要操作方法，如果超时则回退到备选方法。", "错误恢复与重试"),
    ("WF100", "完整自动化场景执行与验证", "按顺序执行一系列工作流步骤，每步验证后再继续，生成执行报告。", "错误恢复与重试"),
]

for wf_id, name, desc, category in _guide_workflows:
    _register_workflow(wf_id, name, desc, category, steps=None, executable=False)


def workflow_list(category: Optional[str] = None, executable_only: bool = False) -> dict[str, Any]:
    """List all available workflows.

    Args:
        category: Filter by category (optional)
        executable_only: If True, only return executable workflows

    Returns:
        Dict with workflow count and list
    """
    workflows = []
    for wf_id, wf in sorted(WORKFLOWS.items()):
        if category and wf["category"] != category:
            continue
        if executable_only and not wf["executable"]:
            continue
        workflows.append({
            "id": wf["id"],
            "name": wf["name"],
            "description": wf["description"],
            "category": wf["category"],
            "executable": wf["executable"],
            "step_count": len(wf["steps"]),
        })
    return {"count": len(workflows), "workflows": workflows}


def workflow_get(workflow_id: str) -> dict[str, Any]:
    """Get a workflow definition by ID.

    Args:
        workflow_id: Workflow ID (e.g. "WF001")

    Returns:
        Workflow definition with steps
    """
    if workflow_id not in WORKFLOWS:
        raise ValueError(f"Unknown workflow: {workflow_id}. "
                         f"Available: {list(WORKFLOWS.keys())[:10]}...")
    wf = WORKFLOWS[workflow_id]
    return {
        "id": wf["id"],
        "name": wf["name"],
        "description": wf["description"],
        "category": wf["category"],
        "executable": wf["executable"],
        "steps": wf["steps"],
        "step_count": len(wf["steps"]),
    }


def workflow_execute(workflow_id: str, params: Optional[dict[str, Any]] = None,
                      stop_on_error: bool = True) -> dict[str, Any]:
    """Execute a workflow by ID with the given parameters.

    Args:
        workflow_id: Workflow ID (e.g. "WF001")
        params: Input parameters for the workflow (available as $param_name$ in steps)
        stop_on_error: If True, stop on first error; if False, continue executing remaining steps

    Returns:
        Execution result with context, step results, and status
    """
    _validate_workflow_id(workflow_id)

    if workflow_id not in WORKFLOWS:
        raise ValueError(f"Unknown workflow: {workflow_id}. "
                         f"Use workflow_list() to see available workflows.")

    wf = WORKFLOWS[workflow_id]
    if not wf["executable"]:
        return {
            "status": "guide_only",
            "workflow_id": workflow_id,
            "name": wf["name"],
            "category": wf["category"],
            "message": f"Workflow '{workflow_id}' ({wf['name']}) is a guide-only workflow. "
                       f"See references/workflows.md for manual execution steps.",
            "steps": wf["steps"],
        }

    return _execute_workflow_steps(wf["steps"], workflow_id=workflow_id,
                                    workflow_name=wf["name"], category=wf["category"],
                                    params=params, stop_on_error=stop_on_error)


def workflow_execute_custom(steps: list[dict[str, Any]],
                             params: Optional[dict[str, Any]] = None,
                             name: str = "custom_workflow",
                             stop_on_error: bool = True) -> dict[str, Any]:
    """Execute a custom workflow defined by a list of steps.

    Args:
        steps: List of step definitions (same schema as registered workflows)
        params: Input parameters available as $param_name$ in steps
        name: Name for this custom workflow
        stop_on_error: If True, stop on first error

    Returns:
        Execution result

    Example:
        workflow_execute_custom([
            {"tool": "app_start", "params": {"cmd_line": "notepad.exe"}, "output_key": "app_id", "wait": 1},
            {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "wrapper_id"},
            {"tool": "control_type_keys", "params": {"wrapper_id": "$wrapper_id$", "keys": "Hello"}, "retries": 2},
        ])
    """
    if not steps:
        return {"status": "success", "name": name, "steps_completed": 0, "step_results": []}

    # Validate steps
    validation = workflow_validate_steps(steps)
    if not validation["valid"]:
        return {"status": "error", "name": name, "error": "Invalid workflow definition",
                "validation_errors": validation["errors"]}

    return _execute_workflow_steps(steps, workflow_id="custom", workflow_name=name,
                                    category="custom", params=params, stop_on_error=stop_on_error)


def workflow_validate_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate a list of workflow steps for correctness.

    Args:
        steps: List of step definitions

    Returns:
        Dict with valid flag and list of errors/warnings
    """
    errors = []
    warnings = []

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"Step {i}: must be a dict, got {type(step).__name__}")
            continue

        tool_name = step.get("tool")
        if not tool_name:
            errors.append(f"Step {i}: missing 'tool' key")
        elif tool_name not in ALL_FUNCTIONS:
            errors.append(f"Step {i}: unknown tool '{tool_name}'")
        else:
            # Validate params
            func = ALL_FUNCTIONS[tool_name]
            sig_params = set(inspect.signature(func).parameters.keys())
            params = step.get("params", {})
            for key in params:
                if key not in sig_params and not (isinstance(params[key], str) and params[key].startswith("$")):
                    warnings.append(f"Step {i}: param '{key}' not in {tool_name} signature")

        # Validate condition syntax
        condition = step.get("condition")
        if condition and not isinstance(condition, str):
            errors.append(f"Step {i}: 'condition' must be a string")

        # Validate numeric fields
        for field in ["retries", "wait", "timeout", "retry_delay"]:
            if field in step and not isinstance(step[field], (int, float)):
                errors.append(f"Step {i}: '{field}' must be numeric")

    return {
        "valid": len(errors) == 0,
        "step_count": len(steps),
        "errors": errors,
        "warnings": warnings,
    }


def _execute_workflow_steps(steps: list[dict[str, Any]], workflow_id: str,
                              workflow_name: str, category: str,
                              params: Optional[dict[str, Any]] = None,
                              stop_on_error: bool = True) -> dict[str, Any]:
    """Internal: execute a list of workflow steps."""
    context = dict(params or {})
    context["workflow_id"] = workflow_id
    context["workflow_name"] = workflow_name
    step_results = []
    start_time = time.time()
    errors = 0
    skipped = 0

    for i, step in enumerate(steps):
        tool_name = step.get("tool", "unknown")
        description = step.get("description", tool_name)
        logger.info("Workflow %s step %d/%d: %s", workflow_id, i + 1, len(steps), description)

        result = _execute_step(step, context, step_index=i + 1)
        step_results.append(result)

        if result["status"] == "skipped":
            skipped += 1
        elif result["status"] == "error":
            errors += 1
            if stop_on_error:
                logger.error("Workflow %s stopped at step %d due to error", workflow_id, i + 1)
                break
        elif result["status"] == "error_ignored":
            errors += 1

    elapsed = time.time() - start_time
    succeeded = len(step_results) - errors - skipped

    if errors > 0 and stop_on_error:
        status = "error"
    elif errors > 0:
        status = "partial"
    else:
        status = "success"

    logger.info("Workflow %s %s in %.2fs (%d steps, %d ok, %d err, %d skip)",
                workflow_id, status, elapsed, len(steps), succeeded, errors, skipped)

    return {
        "status": status,
        "workflow_id": workflow_id,
        "name": workflow_name,
        "category": category,
        "total_steps": len(steps),
        "steps_completed": len(step_results),
        "succeeded": succeeded,
        "errors": errors,
        "skipped": skipped,
        "step_results": step_results,
        "context": {k: v for k, v in context.items() if not k.startswith("_")},
        "elapsed_seconds": round(elapsed, 3),
    }


# Add workflow tools to ALL_FUNCTIONS
ALL_FUNCTIONS["workflow_list"] = workflow_list
ALL_FUNCTIONS["workflow_get"] = workflow_get
ALL_FUNCTIONS["workflow_execute"] = workflow_execute
ALL_FUNCTIONS["workflow_execute_custom"] = workflow_execute_custom
ALL_FUNCTIONS["workflow_validate_steps"] = workflow_validate_steps
