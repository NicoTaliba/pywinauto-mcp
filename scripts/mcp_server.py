"""
PyWinAuto MCP Server — Windows UI automation via Model Context Protocol.

Exposes 128+ pywinauto API operations as MCP tools over stdio or HTTP.

Usage:
    # Stdio mode (default, for MCP clients)
    python mcp_server.py

    # HTTP mode
    python mcp_server.py --http --host 127.0.0.1 --port 10789

    # List all tools
    python mcp_server.py --list-tools

Environment variables:
    MCP_TRANSPORT  - "stdio" (default) or "http"
    MCP_HOST       - bind address for HTTP (default: 127.0.0.1)
    MCP_PORT       - port for HTTP (default: 10789)
    MCP_PATH       - HTTP endpoint path (default: /mcp)
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import inspect
import logging
import os
import sys
import traceback
from typing import Any, Callable, Optional

# Ensure the script directory is on the path for wrapper import
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import pywinauto_wrapper as pw  # noqa: E402

# Import generation engine to auto-register generation-level tools
import generation_engine  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("pywinauto_mcp")


# ---------------------------------------------------------------------------
# Error-handling decorator that preserves the original function signature
# ---------------------------------------------------------------------------

def _tool_error_handler(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorate a function to catch exceptions and return standardized error dict.

    Uses functools.wraps so inspect.signature() follows __wrapped__ and
    FastMCP can generate proper JSON schemas.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            result = func(*args, **kwargs)
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error("Tool '%s' failed: %s", func.__name__, e)
            logger.debug(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }
    return wrapper


# ---------------------------------------------------------------------------
# Explicit-parameter versions of functions that originally used **kwargs
# ---------------------------------------------------------------------------

def app_connect_explicit(backend: str = "uia", process: Optional[int] = None,
                          handle: Optional[int] = None, path: Optional[str] = None,
                          title: Optional[str] = None, title_re: Optional[str] = None,
                          class_name: Optional[str] = None,
                          class_name_re: Optional[str] = None) -> dict[str, Any]:
    """Connect to an already running application.

    Provide exactly one criterion: process, handle, path, title, title_re,
    class_name, or class_name_re.

    Args:
        backend: 'uia' or 'win32'
        process: Process ID
        handle: Window handle
        path: Executable path
        title: Exact window title
        title_re: Regex pattern for window title
        class_name: Window class name
        class_name_re: Regex pattern for class name
    """
    kwargs: dict[str, Any] = {}
    for key, val in [("process", process), ("handle", handle), ("path", path),
                      ("title", title), ("title_re", title_re),
                      ("class_name", class_name), ("class_name_re", class_name_re)]:
        if val is not None:
            kwargs[key] = val
    return pw.app_connect(backend=backend, **kwargs)


def app_windows_explicit(app_id: str) -> dict[str, Any]:
    """Return list of top-level windows of the application."""
    return pw.app_windows(app_id)


def app_window_explicit(app_id: str, title: Optional[str] = None,
                         title_re: Optional[str] = None,
                         class_name: Optional[str] = None,
                         class_name_re: Optional[str] = None,
                         control_type: Optional[str] = None,
                         auto_id: Optional[str] = None,
                         control_id: Optional[int] = None,
                         handle: Optional[int] = None,
                         found_index: Optional[int] = None) -> dict[str, Any]:
    """Find a window within the application by criteria.

    Args:
        app_id: Application session ID
        title: Exact title match
        title_re: Regex title match
        class_name: Exact class name match
        class_name_re: Regex class name match
        control_type: UIA control type (e.g. 'Button', 'Edit')
        auto_id: UIA automation ID
        control_id: Win32 control ID
        handle: Window handle
        found_index: Zero-based index among matches
    """
    kwargs: dict[str, Any] = {}
    for key, val in [("title", title), ("title_re", title_re),
                      ("class_name", class_name), ("class_name_re", class_name_re),
                      ("control_type", control_type), ("auto_id", auto_id),
                      ("control_id", control_id), ("handle", handle),
                      ("found_index", found_index)]:
        if val is not None:
            kwargs[key] = val
    return pw.app_window(app_id, **kwargs)


def window_find_explicit(app_id: Optional[str] = None, backend: str = "uia",
                          title: Optional[str] = None, title_re: Optional[str] = None,
                          class_name: Optional[str] = None,
                          class_name_re: Optional[str] = None,
                          control_type: Optional[str] = None,
                          auto_id: Optional[str] = None,
                          control_id: Optional[int] = None,
                          handle: Optional[int] = None,
                          found_index: Optional[int] = None) -> dict[str, Any]:
    """Find a window/control on the desktop or within an app.

    If app_id is provided, searches within that application.
    Otherwise searches the whole desktop.

    Args:
        app_id: Application session ID (optional)
        backend: 'uia' or 'win32'
        title: Exact title match
        title_re: Regex title match
        class_name: Exact class name match
        class_name_re: Regex class name match
        control_type: UIA control type
        auto_id: UIA automation ID
        control_id: Win32 control ID
        handle: Window handle
        found_index: Zero-based index among matches
    """
    kwargs: dict[str, Any] = {"backend": backend}
    for key, val in [("title", title), ("title_re", title_re),
                      ("class_name", class_name), ("class_name_re", class_name_re),
                      ("control_type", control_type), ("auto_id", auto_id),
                      ("control_id", control_id), ("handle", handle),
                      ("found_index", found_index)]:
        if val is not None:
            kwargs[key] = val
    return pw.window_find(app_id=app_id, **kwargs)


def control_child_window_explicit(wrapper_id: str, title: Optional[str] = None,
                                    title_re: Optional[str] = None,
                                    class_name: Optional[str] = None,
                                    class_name_re: Optional[str] = None,
                                    control_type: Optional[str] = None,
                                    auto_id: Optional[str] = None,
                                    control_id: Optional[int] = None,
                                    found_index: Optional[int] = None) -> dict[str, Any]:
    """Find a child control by criteria.

    Args:
        wrapper_id: Parent wrapper session ID
        title: Exact title match
        title_re: Regex title match
        class_name: Exact class name match
        class_name_re: Regex class name match
        control_type: UIA control type
        auto_id: UIA automation ID
        control_id: Win32 control ID
        found_index: Zero-based index among matches
    """
    kwargs: dict[str, Any] = {}
    for key, val in [("title", title), ("title_re", title_re),
                      ("class_name", class_name), ("class_name_re", class_name_re),
                      ("control_type", control_type), ("auto_id", auto_id),
                      ("control_id", control_id), ("found_index", found_index)]:
        if val is not None:
            kwargs[key] = val
    return pw.control_child_window(wrapper_id, **kwargs)


def control_children_explicit(wrapper_id: str) -> dict[str, Any]:
    """Get immediate children of the control."""
    return pw.control_children(wrapper_id)


def control_descendants_explicit(wrapper_id: str) -> dict[str, Any]:
    """Get all descendants of the control."""
    return pw.control_descendants(wrapper_id)


def timings_set_explicit(window_find_timeout: Optional[float] = None,
                           window_find_retry: Optional[float] = None,
                           exists_timeout: Optional[float] = None,
                           exists_retry: Optional[float] = None,
                           after_click_wait: Optional[float] = None,
                           after_clickinput_wait: Optional[float] = None,
                           after_menu_wait: Optional[float] = None,
                           after_sendkeys_key_wait: Optional[float] = None,
                           after_setcursorpos_wait: Optional[float] = None,
                           after_tabselect_wait: Optional[float] = None,
                           drag_n_drop_move_mouse_wait: Optional[float] = None,
                           before_drag_wait: Optional[float] = None,
                           before_drop_wait: Optional[float] = None,
                           after_drag_n_drop_wait: Optional[float] = None,
                           scroll_step_wait: Optional[float] = None) -> dict[str, Any]:
    """Set timing configuration values.

    Only provided (non-None) values are updated.
    Use timings_get() to see the full list of available timing keys.
    """
    kwargs: dict[str, Any] = {}
    for key, val in [("window_find_timeout", window_find_timeout),
                      ("window_find_retry", window_find_retry),
                      ("exists_timeout", exists_timeout),
                      ("exists_retry", exists_retry),
                      ("after_click_wait", after_click_wait),
                      ("after_clickinput_wait", after_clickinput_wait),
                      ("after_menu_wait", after_menu_wait),
                      ("after_sendkeys_key_wait", after_sendkeys_key_wait),
                      ("after_setcursorpos_wait", after_setcursorpos_wait),
                      ("after_tabselect_wait", after_tabselect_wait),
                      ("drag_n_drop_move_mouse_wait", drag_n_drop_move_mouse_wait),
                      ("before_drag_wait", before_drag_wait),
                      ("before_drop_wait", before_drop_wait),
                      ("after_drag_n_drop_wait", after_drag_n_drop_wait),
                      ("scroll_step_wait", scroll_step_wait)]:
        if val is not None:
            kwargs[key] = val
    return pw.timings_set(**kwargs)


def find_windows_explicit(backend: str = "uia", title: Optional[str] = None,
                            title_re: Optional[str] = None,
                            class_name: Optional[str] = None,
                            class_name_re: Optional[str] = None,
                            process: Optional[int] = None,
                            handle: Optional[int] = None,
                            enabled_only: bool = False,
                            visible_only: bool = True,
                            top_level_only: bool = True) -> dict[str, Any]:
    """Find windows matching criteria. Returns list of window handles.

    Args:
        backend: 'uia' or 'win32'
        title: Exact title match
        title_re: Regex title match
        class_name: Exact class name match
        class_name_re: Regex class name match
        process: Process ID filter
        handle: Window handle filter
        enabled_only: Only return enabled windows
        visible_only: Only return visible windows
        top_level_only: Only return top-level windows
    """
    kwargs: dict[str, Any] = {}
    for key, val in [("title", title), ("title_re", title_re),
                      ("class_name", class_name), ("class_name_re", class_name_re),
                      ("process", process), ("handle", handle),
                      ("enabled_only", enabled_only), ("visible_only", visible_only),
                      ("top_level_only", top_level_only)]:
        if val is not None and val is not False:
            kwargs[key] = val
        elif key in ("enabled_only", "visible_only", "top_level_only") and val:
            kwargs[key] = val
    return pw.find_windows(backend=backend, **kwargs)


def find_elements_explicit(backend: str = "uia", title: Optional[str] = None,
                             title_re: Optional[str] = None,
                             class_name: Optional[str] = None,
                             control_type: Optional[str] = None,
                             auto_id: Optional[str] = None,
                             process: Optional[int] = None,
                             depth: Optional[int] = None) -> dict[str, Any]:
    """Find UIA elements matching criteria. Returns element info list.

    Args:
        backend: 'uia' (recommended)
        title: Exact name/title match
        title_re: Regex name match
        class_name: Class name filter
        control_type: UIA control type filter
        auto_id: UIA automation ID filter
        process: Process ID filter
        depth: Search depth
    """
    kwargs: dict[str, Any] = {}
    for key, val in [("title", title), ("title_re", title_re),
                      ("class_name", class_name), ("control_type", control_type),
                      ("auto_id", auto_id), ("process", process), ("depth", depth)]:
        if val is not None:
            kwargs[key] = val
    return pw.find_elements(backend=backend, **kwargs)


def desktop_window_explicit(backend: str = "uia", title: Optional[str] = None,
                              title_re: Optional[str] = None,
                              class_name: Optional[str] = None,
                              control_type: Optional[str] = None,
                              auto_id: Optional[str] = None,
                              handle: Optional[int] = None,
                              found_index: Optional[int] = None) -> dict[str, Any]:
    """Find a desktop window by criteria."""
    kwargs: dict[str, Any] = {}
    for key, val in [("title", title), ("title_re", title_re),
                      ("class_name", class_name), ("control_type", control_type),
                      ("auto_id", auto_id), ("handle", handle),
                      ("found_index", found_index)]:
        if val is not None:
            kwargs[key] = val
    return pw.desktop_window(backend=backend, **kwargs)


def control_call_method_explicit(wrapper_id: str, method: str,
                                   arg1: Optional[str] = None,
                                   arg2: Optional[str] = None,
                                   arg3: Optional[str] = None) -> dict[str, Any]:
    """Call any method on a wrapper object (escape hatch).

    Args:
        wrapper_id: Wrapper session ID
        method: Method name to call
        arg1: First positional argument (string, will be auto-converted)
        arg2: Second positional argument
        arg3: Third positional argument
    """
    args: list[Any] = []
    for arg in (arg1, arg2, arg3):
        if arg is not None:
            # Try to convert to int/float/bool
            if arg.lower() in ("true", "false"):
                args.append(arg.lower() == "true")
            else:
                try:
                    args.append(int(arg))
                except ValueError:
                    try:
                        args.append(float(arg))
                    except ValueError:
                        args.append(arg)
    return pw.control_call_method(wrapper_id, method, *args)


def control_click_explicit(wrapper_id: str, button: str = "left",
                             x: Optional[int] = None, y: Optional[int] = None,
                             double: bool = False) -> dict[str, Any]:
    """Click on the control.

    Args:
        wrapper_id: Wrapper session ID
        button: 'left', 'right', or 'middle'
        x: X coordinate relative to control (None = center)
        y: Y coordinate relative to control (None = center)
        double: If True, double-click
    """
    coords = (x, y) if x is not None and y is not None else None
    return pw.control_click(wrapper_id, button=button, coords=coords, double=double)


def control_double_click_explicit(wrapper_id: str, button: str = "left",
                                    x: Optional[int] = None,
                                    y: Optional[int] = None) -> dict[str, Any]:
    """Double-click the control."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.control_double_click(wrapper_id, button=button, coords=coords)


def control_right_click_explicit(wrapper_id: str, x: Optional[int] = None,
                                   y: Optional[int] = None) -> dict[str, Any]:
    """Right-click the control."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.control_right_click(wrapper_id, coords=coords)


def control_click_input_explicit(wrapper_id: str, button: str = "left",
                                   x: Optional[int] = None,
                                   y: Optional[int] = None,
                                   double: bool = False) -> dict[str, Any]:
    """Click using send_message (more realistic, activates window first)."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.control_click_input(wrapper_id, button=button, coords=coords, double=double)


def control_drag_mouse_explicit(wrapper_id: str, dst_x: int, dst_y: int,
                                  src_x: Optional[int] = None,
                                  src_y: Optional[int] = None,
                                  button: str = "left") -> dict[str, Any]:
    """Drag the mouse from src to dst on the control.

    Args:
        wrapper_id: Wrapper session ID
        dst_x: Destination X relative to control
        dst_y: Destination Y relative to control
        src_x: Source X relative to control (None = center)
        src_y: Source Y relative to control (None = center)
        button: 'left', 'right', or 'middle'
    """
    dst = (dst_x, dst_y)
    src = (src_x, src_y) if src_x is not None and src_y is not None else None
    return pw.control_drag_mouse(wrapper_id, dst=dst, src=src, button=button)


def control_scroll_at_point_explicit(wrapper_id: str, direction: str = "down",
                                       amount: int = 1, count: int = 1,
                                       x: Optional[int] = None,
                                       y: Optional[int] = None) -> dict[str, Any]:
    """Scroll at a specific point on the control."""
    kwargs: dict[str, Any] = {}
    if x is not None and y is not None:
        kwargs["x"] = x
        kwargs["y"] = y
    return pw.control_scroll_at_point(wrapper_id, direction=direction, amount=amount,
                                        count=count, **kwargs)


def control_capture_as_image_explicit(wrapper_id: str, save_path: Optional[str] = None) -> dict[str, Any]:
    """Capture the control as an image. Returns path or base64."""
    return pw.control_capture_as_image(wrapper_id, save_path=save_path)


def control_press_mouse_explicit(wrapper_id: str, button: str = "left",
                                   x: Optional[int] = None,
                                   y: Optional[int] = None) -> dict[str, Any]:
    """Press a mouse button on the control."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.control_press_mouse(wrapper_id, button=button, coords=coords)


def control_release_mouse_explicit(wrapper_id: str, button: str = "left",
                                     x: Optional[int] = None,
                                     y: Optional[int] = None) -> dict[str, Any]:
    """Release a mouse button on the control."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.control_release_mouse(wrapper_id, button=button, coords=coords)


def control_move_mouse_explicit(wrapper_id: str, x: Optional[int] = None,
                                  y: Optional[int] = None) -> dict[str, Any]:
    """Move the mouse over the control."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.control_move_mouse(wrapper_id, coords=coords)


def mouse_click_explicit(button: str = "left", x: Optional[int] = None,
                           y: Optional[int] = None, double: bool = False) -> dict[str, Any]:
    """Click at screen coordinates (or current position if x/y not provided)."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.mouse_click(button=button, coords=coords, double=double)


def mouse_double_click_explicit(button: str = "left", x: Optional[int] = None,
                                  y: Optional[int] = None) -> dict[str, Any]:
    """Double-click at screen coordinates."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.mouse_double_click(button=button, coords=coords)


def mouse_right_click_explicit(x: Optional[int] = None, y: Optional[int] = None) -> dict[str, Any]:
    """Right-click at screen coordinates."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.mouse_right_click(coords=coords)


def mouse_move_explicit(x: int, y: int) -> dict[str, Any]:
    """Move the mouse to screen coordinates."""
    return pw.mouse_move(coords=(x, y))


def mouse_press_explicit(button: str = "left", x: Optional[int] = None,
                          y: Optional[int] = None) -> dict[str, Any]:
    """Press a mouse button at screen coordinates."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.mouse_press(button=button, coords=coords)


def mouse_release_explicit(button: str = "left", x: Optional[int] = None,
                            y: Optional[int] = None) -> dict[str, Any]:
    """Release a mouse button at screen coordinates."""
    coords = (x, y) if x is not None and y is not None else None
    return pw.mouse_release(button=button, coords=coords)


def mouse_scroll_explicit(direction: str = "up", amount: int = 1,
                            x: Optional[int] = None, y: Optional[int] = None) -> dict[str, Any]:
    """Scroll the mouse wheel.

    Args:
        direction: 'up' or 'down'
        amount: Number of scroll steps
        x: X coordinate to scroll at (None = current)
        y: Y coordinate to scroll at (None = current)
    """
    coords = (x, y) if x is not None and y is not None else None
    return pw.mouse_scroll(direction=direction, amount=amount, coords=coords)


def mouse_drag_explicit(src_x: int, src_y: int, dst_x: int, dst_y: int,
                         button: str = "left") -> dict[str, Any]:
    """Drag from src to dst at screen coordinates."""
    return pw.mouse_drag(src=(src_x, src_y), dst=(dst_x, dst_y), button=button)


def control_select_explicit(wrapper_id: str, item: Optional[str] = None,
                              index: Optional[int] = None) -> dict[str, Any]:
    """Select an item in a list/combo box. Provide item or index."""
    return pw.control_select(wrapper_id, item=item, index=index)


def window_wait_explicit(wrapper_id: str, wait_for: str = "visible",
                          timeout: Optional[float] = None,
                          retry_interval: Optional[float] = None) -> dict[str, Any]:
    """Wait for the window to be in a particular state.

    States: 'exists', 'visible', 'enabled', 'ready' (visible + enabled).
    Combine with space: 'visible enabled'.
    """
    return pw.window_wait(wrapper_id, wait_for=wait_for, timeout=timeout,
                           retry_interval=retry_interval)


def window_exists_explicit(wrapper_id: str, timeout: Optional[float] = None,
                             retry_interval: Optional[float] = None) -> dict[str, Any]:
    """Check if a window/control exists."""
    return pw.window_exists(wrapper_id, timeout=timeout, retry_interval=retry_interval)


def window_dump_tree_explicit(wrapper_id: str, depth: Optional[int] = None) -> dict[str, Any]:
    """Dump the control tree identifiers."""
    return pw.window_dump_tree(wrapper_id, depth=depth)


def app_start_explicit(cmd_line: str, backend: str = "uia",
                        timeout: Optional[float] = None,
                        work_dir: Optional[str] = None,
                        wait_for_idle: bool = True) -> dict[str, Any]:
    """Start an application.

    Args:
        cmd_line: Command line to start (e.g. 'notepad.exe')
        backend: 'uia' or 'win32'
        timeout: Timeout for start
        work_dir: Working directory
        wait_for_idle: Whether to wait for idle after start
    """
    return pw.app_start(cmd_line, backend=backend, timeout=timeout,
                         work_dir=work_dir, wait_for_idle=wait_for_idle)


def app_cpu_usage_explicit(app_id: str, interval: Optional[float] = None) -> dict[str, Any]:
    """Return CPU usage percent."""
    return pw.app_cpu_usage(app_id, interval=interval)


def app_wait_cpu_usage_lower_explicit(app_id: str, threshold: float = 2.5,
                                         timeout: Optional[float] = None,
                                         usage_interval: Optional[float] = None) -> dict[str, Any]:
    """Wait until CPU usage is below threshold."""
    return pw.app_wait_cpu_usage_lower(app_id, threshold=threshold, timeout=timeout,
                                         usage_interval=usage_interval)


def app_wait_for_process_exit_explicit(app_id: str, timeout: Optional[float] = None,
                                          retry_interval: Optional[float] = None) -> dict[str, Any]:
    """Wait for the process to exit."""
    return pw.app_wait_for_process_exit(app_id, timeout=timeout, retry_interval=retry_interval)


def keyboard_send_keys_explicit(keys: str, with_spaces: bool = False,
                                  with_tabs: bool = False,
                                  with_newlines: bool = False,
                                  turn_off_numlock: bool = True,
                                  pause: Optional[float] = None) -> dict[str, Any]:
    """Send keys to the active window.

    Supports pywinauto key syntax:
      - '^a' = Ctrl+A, '%{F4}' = Alt+F4, '+{INS}' = Shift+Ins
      - '{ENTER}', '{TAB}', '{ESC}', '{F1}'..'{F24}'
      - '{VK_SHIFT down}' ... '{VK_SHIFT up}' for hold/release
    """
    return pw.keyboard_send_keys(keys, with_spaces=with_spaces, with_tabs=with_tabs,
                                   with_newlines=with_newlines, turn_off_numlock=turn_off_numlock,
                                   pause=pause)


def control_type_keys_explicit(wrapper_id: str, keys: str, with_spaces: bool = False,
                                 with_tabs: bool = False, with_newlines: bool = False,
                                 turn_off_numlock: bool = True,
                                 set_foreground: bool = True,
                                 pause: Optional[float] = None) -> dict[str, Any]:
    """Type keys into the control (supports pywinauto key syntax)."""
    return pw.control_type_keys(wrapper_id, keys, with_spaces=with_spaces,
                                  with_tabs=with_tabs, with_newlines=with_newlines,
                                  turn_off_numlock=turn_off_numlock,
                                  set_foreground=set_foreground, pause=pause)


def control_move_window_explicit(wrapper_id: str, x: int, y: int,
                                   width: Optional[int] = None,
                                   height: Optional[int] = None) -> dict[str, Any]:
    """Move and optionally resize the window."""
    return pw.control_move_window(wrapper_id, x, y, width=width, height=height)


def menu_get_items_explicit(wrapper_id: str, path: Optional[str] = None) -> dict[str, Any]:
    """Get menu items from a menu wrapper or window."""
    return pw.menu_get_items(wrapper_id, path=path)


def taskbar_click_on_button_explicit(text: str, by: str = "title") -> dict[str, Any]:
    """Click a button on the taskbar.

    Args:
        text: Button text or index (as string)
        by: 'title' or 'index'
    """
    return pw.taskbar_click_on_button(text, by=by)


def control_get_legacy_iaccessible_property_explicit(wrapper_id: str,
                                                        property_name: str) -> dict[str, Any]:
    """Get a legacy IAccessible property (UIA only)."""
    return pw.control_get_legacy_iaccessible_property(wrapper_id, property_name)


def control_verify_action_explicit(wrapper_id: str, action: str = "click") -> dict[str, Any]:
    """Verify that an action can be performed."""
    return pw.control_verify_action(wrapper_id, action=action)


# ---------------------------------------------------------------------------
# Explicit versions for enhanced v2.0 tools
# ---------------------------------------------------------------------------

def safe_click_explicit(wrapper_id: str, button: str = "left", retries: int = 3,
                         delay: float = 0.5, verify_visible: bool = True,
                         verify_enabled: bool = True) -> dict[str, Any]:
    """Click a control with precondition verification and retry."""
    return pw.safe_click(wrapper_id, button=button, retries=retries, delay=delay,
                          verify_visible=verify_visible, verify_enabled=verify_enabled)


def safe_type_text_explicit(wrapper_id: str, text: str, clear_first: bool = True,
                              retries: int = 2, delay: float = 0.5,
                              use_clipboard: bool = True) -> dict[str, Any]:
    """Type text into a control with focus verification and retry."""
    return pw.safe_type_text(wrapper_id, text, clear_first=clear_first, retries=retries,
                               delay=delay, use_clipboard=use_clipboard)


def inspect_element_explicit(wrapper_id: str, depth: int = 2) -> dict[str, Any]:
    """Deep inspect a control element, returning all properties and child structure."""
    return pw.inspect_element(wrapper_id, depth=depth)


def batch_execute_explicit(operations_json: str, stop_on_error: bool = True,
                            continue_on_error: bool = False) -> dict[str, Any]:
    """Execute a batch of operations sequentially.

    Args:
        operations_json: JSON string of operations list, each with 'tool' and 'params'
        stop_on_error: If True, stop on first error
        continue_on_error: If True, continue on error (overrides stop_on_error)
    """
    import json as _json
    operations = _json.loads(operations_json)
    return pw.batch_execute(operations, stop_on_error=stop_on_error,
                             continue_on_error=continue_on_error)


def snapshot_ui_state_explicit(wrapper_id: Optional[str] = None) -> dict[str, Any]:
    """Capture a snapshot of the current UI state for later comparison."""
    return pw.snapshot_ui_state(wrapper_id=wrapper_id)


def workflow_execute_custom_explicit(steps_json: str, params_json: Optional[str] = None,
                                       name: str = "custom_workflow",
                                       stop_on_error: bool = True) -> dict[str, Any]:
    """Execute a custom workflow defined by a list of steps.

    Args:
        steps_json: JSON string of step definitions
        params_json: JSON string of input parameters
        name: Name for this custom workflow
        stop_on_error: If True, stop on first error
    """
    import json as _json
    steps = _json.loads(steps_json)
    params = _json.loads(params_json) if params_json else None
    return pw.workflow_execute_custom(steps, params=params, name=name,
                                        stop_on_error=stop_on_error)


def workflow_validate_steps_explicit(steps_json: str) -> dict[str, Any]:
    """Validate a list of workflow steps for correctness.

    Args:
        steps_json: JSON string of step definitions
    """
    import json as _json
    steps = _json.loads(steps_json)
    return pw.workflow_validate_steps(steps)


def classify_error_explicit(error_message: str) -> dict[str, Any]:
    """Classify an error message and provide recovery suggestions."""
    return pw.classify_error(error_message)


# ---------------------------------------------------------------------------
# Explicit versions for generation-level (v3.0) tools
# ---------------------------------------------------------------------------

def generate_workflow_explicit(description: str, context_json: Optional[str] = None,
                                auto_execute: bool = False) -> dict[str, Any]:
    """Generate an executable workflow from natural language description.

    Args:
        description: Natural language task description
        context_json: JSON string of existing context (app_id, wrapper_id, etc.)
        auto_execute: If True, execute the workflow immediately after generation
    """
    import json as _json
    context = _json.loads(context_json) if context_json else None
    return generation_engine.generate_workflow(description, context=context, auto_execute=auto_execute)


def generate_and_execute_explicit(description: str, context_json: Optional[str] = None) -> dict[str, Any]:
    """Generate workflow from natural language and execute immediately."""
    import json as _json
    context = _json.loads(context_json) if context_json else None
    return generation_engine.generate_and_execute(description, context=context)


def smart_find_explicit(description: str, wrapper_id: Optional[str] = None,
                         backend: str = "uia", max_results: int = 10,
                         search_depth: int = 3) -> dict[str, Any]:
    """Smart element locator: find controls by natural language description.

    Args:
        description: Element description (e.g. '确定按钮', '用户名输入框')
        wrapper_id: Parent container wrapper_id (None = whole desktop)
        backend: 'uia' or 'win32'
        max_results: Maximum number of results to return
        search_depth: Control tree search depth
    """
    return generation_engine.smart_find(description, wrapper_id=wrapper_id,
                                          backend=backend, max_results=max_results,
                                          search_depth=search_depth)


def adaptive_execute_explicit(steps_json: str, max_retries_per_step: int = 3,
                                auto_recover: bool = True, stop_on_error: bool = True,
                                name: str = "adaptive_workflow") -> dict[str, Any]:
    """Adaptive self-healing workflow executor with automatic error recovery.

    Args:
        steps_json: JSON string of workflow steps
        max_retries_per_step: Max retries per step
        auto_recover: Enable automatic recovery strategies
        stop_on_error: Stop after recovery fails
        name: Workflow name
    """
    import json as _json
    steps = _json.loads(steps_json)
    return generation_engine.adaptive_execute(steps, max_retries_per_step=max_retries_per_step,
                                                auto_recover=auto_recover, stop_on_error=stop_on_error,
                                                name=name)


def analyze_ui_explicit(wrapper_id: Optional[str] = None, depth: int = 3,
                         include_properties: bool = True) -> dict[str, Any]:
    """Analyze UI structure and generate structured description."""
    return generation_engine.analyze_ui(wrapper_id, depth=depth, include_properties=include_properties)


def describe_element_explicit(wrapper_id: str) -> dict[str, Any]:
    """Generate natural language description of a control element."""
    return generation_engine.describe_element(wrapper_id)


def find_interactive_elements_explicit(wrapper_id: Optional[str] = None,
                                         control_type: Optional[str] = None,
                                         only_visible: bool = True,
                                         only_enabled: bool = True) -> dict[str, Any]:
    """Find all interactive elements in the UI."""
    return generation_engine.find_interactive_elements(wrapper_id, control_type=control_type,
                                                          only_visible=only_visible, only_enabled=only_enabled)


def list_scenarios_explicit(category: Optional[str] = None) -> dict[str, Any]:
    """List all available scenario templates."""
    return generation_engine.list_scenarios(category)


def apply_scenario_explicit(scenario_id: str, params_json: Optional[str] = None,
                             auto_execute: bool = False) -> dict[str, Any]:
    """Apply a scenario template to generate workflow steps.

    Args:
        scenario_id: Scenario ID (e.g. 'notepad_basic')
        params_json: JSON string of scenario parameters
        auto_execute: Execute immediately
    """
    import json as _json
    params = _json.loads(params_json) if params_json else None
    return generation_engine.apply_scenario(scenario_id, params=params, auto_execute=auto_execute)


def generate_script_explicit(steps_json: Optional[str] = None,
                               workflow_id: Optional[str] = None,
                               scenario_id: Optional[str] = None,
                               script_name: str = "generated_automation",
                               include_comments: bool = True) -> dict[str, Any]:
    """Generate standalone pywinauto Python script from workflow steps.

    Args:
        steps_json: JSON string of workflow steps
        workflow_id: Pre-built workflow ID (alternative to steps_json)
        scenario_id: Scenario template ID (alternative)
        script_name: Name for the generated script
        include_comments: Include step comments
    """
    import json as _json
    steps = _json.loads(steps_json) if steps_json else None
    return generation_engine.generate_script(steps=steps, workflow_id=workflow_id,
                                              scenario_id=scenario_id, script_name=script_name,
                                              include_comments=include_comments)


# ---------------------------------------------------------------------------
# Build the complete tool registry: name -> function
# ---------------------------------------------------------------------------

def _build_tool_registry() -> dict[str, Callable[..., Any]]:
    """Build the complete tool registry, using explicit versions where needed."""
    registry: dict[str, Callable[..., Any]] = {}

    # Functions that need explicit versions (had **kwargs, *args, or tuple params)
    explicit_overrides = {
        "app_start": app_start_explicit,
        "app_connect": app_connect_explicit,
        "app_windows": app_windows_explicit,
        "app_window": app_window_explicit,
        "app_cpu_usage": app_cpu_usage_explicit,
        "app_wait_cpu_usage_lower": app_wait_cpu_usage_lower_explicit,
        "app_wait_for_process_exit": app_wait_for_process_exit_explicit,
        "window_find": window_find_explicit,
        "window_exists": window_exists_explicit,
        "window_wait": window_wait_explicit,
        "window_dump_tree": window_dump_tree_explicit,
        "window_print_control_identifiers": window_dump_tree_explicit,
        "control_click": control_click_explicit,
        "control_double_click": control_double_click_explicit,
        "control_right_click": control_right_click_explicit,
        "control_click_input": control_click_input_explicit,
        "control_type_keys": control_type_keys_explicit,
        "control_select": control_select_explicit,
        "control_drag_mouse": control_drag_mouse_explicit,
        "control_scroll_at_point": control_scroll_at_point_explicit,
        "control_press_mouse": control_press_mouse_explicit,
        "control_release_mouse": control_release_mouse_explicit,
        "control_move_mouse": control_move_mouse_explicit,
        "control_capture_as_image": control_capture_as_image_explicit,
        "control_child_window": control_child_window_explicit,
        "control_children": control_children_explicit,
        "control_descendants": control_descendants_explicit,
        "control_call_method": control_call_method_explicit,
        "control_move_window": control_move_window_explicit,
        "keyboard_send_keys": keyboard_send_keys_explicit,
        "mouse_click": mouse_click_explicit,
        "mouse_double_click": mouse_double_click_explicit,
        "mouse_right_click": mouse_right_click_explicit,
        "mouse_move": mouse_move_explicit,
        "mouse_press": mouse_press_explicit,
        "mouse_release": mouse_release_explicit,
        "mouse_scroll": mouse_scroll_explicit,
        "mouse_drag": mouse_drag_explicit,
        "timings_set": timings_set_explicit,
        "find_windows": find_windows_explicit,
        "find_elements": find_elements_explicit,
        "desktop_window": desktop_window_explicit,
        "menu_get_items": menu_get_items_explicit,
        "taskbar_click_on_button": taskbar_click_on_button_explicit,
        "control_get_legacy_iaccessible_property": control_get_legacy_iaccessible_property_explicit,
        "control_verify_action": control_verify_action_explicit,
        # Enhanced v2.0 tools
        "safe_click": safe_click_explicit,
        "safe_type_text": safe_type_text_explicit,
        "inspect_element": inspect_element_explicit,
        "batch_execute": batch_execute_explicit,
        "snapshot_ui_state": snapshot_ui_state_explicit,
        "workflow_execute_custom": workflow_execute_custom_explicit,
        "workflow_validate_steps": workflow_validate_steps_explicit,
        "classify_error": classify_error_explicit,
        # Generation-level (v3.0) tools
        "generate_workflow": generate_workflow_explicit,
        "generate_and_execute": generate_and_execute_explicit,
        "smart_find": smart_find_explicit,
        "adaptive_execute": adaptive_execute_explicit,
        "analyze_ui": analyze_ui_explicit,
        "describe_element": describe_element_explicit,
        "find_interactive_elements": find_interactive_elements_explicit,
        "list_scenarios": list_scenarios_explicit,
        "apply_scenario": apply_scenario_explicit,
        "generate_script": generate_script_explicit,
    }

    for name, func in pw.ALL_FUNCTIONS.items():
        if name in explicit_overrides:
            registry[name] = explicit_overrides[name]
        else:
            registry[name] = func

    return registry


TOOL_REGISTRY = _build_tool_registry()


# ---------------------------------------------------------------------------
# Tool registration with FastMCP
# ---------------------------------------------------------------------------

def register_tools(mcp: Any) -> int:
    """Register all tools with the FastMCP server.

    Returns the number of tools registered.
    """
    count = 0
    failed = []
    for name, func in TOOL_REGISTRY.items():
        try:
            decorated = _tool_error_handler(func)
            decorated.__name__ = name
            mcp.add_tool(decorated)
            count += 1
        except Exception as e:
            failed.append((name, str(e)))
            logger.warning("Failed to register tool '%s': %s", name, e)

    if failed:
        logger.warning("Failed to register %d tools: %s", len(failed),
                        [f[0] for f in failed])
    logger.info("Registered %d/%d tools", count, len(TOOL_REGISTRY))
    return count


# ---------------------------------------------------------------------------
# Server creation
# ---------------------------------------------------------------------------

def create_server() -> Any:
    """Create and configure the FastMCP server with all tools registered."""
    from fastmcp import FastMCP

    mcp = FastMCP(
        name="pywinauto-mcp",
        version="2.0.0",
        instructions=(
            "PyWinAuto MCP server for Windows UI automation (v2.0). "
            "143 tools covering application management, window/control interaction, "
            "keyboard/mouse input, clipboard, timings, system info, element "
            "discovery, taskbar, desktop, menus, specific control types, "
            "100 pre-built workflows, safe operations, batch execution, "
            "health checks, and state snapshots. "
            "Use app_start/app_connect to begin, then window_find/control_* "
            "to interact. Use workflow_execute for pre-built workflows. "
            "Use health_check to verify server status. "
            "Sessions (app_id, wrapper_id) persist across calls."
        ),
    )

    register_tools(mcp)
    return mcp


def _graceful_shutdown() -> None:
    """Clean up resources on server shutdown."""
    logger.info("Shutting down pywinauto-mcp server...")
    try:
        result = pw.close_all_sessions()
        logger.info("Cleaned up %d app sessions and %d wrapper sessions",
                    result["app_count"], result["wrapper_count"])
    except Exception as e:
        logger.warning("Error during session cleanup: %s", e)
    logger.info("Server shutdown complete")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PyWinAuto MCP Server — Windows UI automation via MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Stdio mode (default)
  python mcp_server.py

  # HTTP mode
  python mcp_server.py --http --port 10789

  # List all available tools
  python mcp_server.py --list-tools

Environment:
  MCP_TRANSPORT  stdio (default) or http
  MCP_HOST       bind address (default: 127.0.0.1)
  MCP_PORT       port (default: 10789)
  MCP_PATH       HTTP path (default: /mcp)
""",
    )
    transport_group = parser.add_mutually_exclusive_group()
    transport_group.add_argument("--stdio", action="store_true", help="Run in stdio mode (default)")
    transport_group.add_argument("--http", action="store_true", help="Run in HTTP Streamable mode")

    parser.add_argument("--host", default=None, help="HTTP bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="HTTP port (default: 10789)")
    parser.add_argument("--path", default=None, help="HTTP endpoint path (default: /mcp)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--list-tools", action="store_true", help="List all registered tools and exit")

    return parser.parse_args()


def resolve_transport(args: argparse.Namespace) -> str:
    if args.http:
        return "http"
    if args.stdio:
        return "stdio"
    return os.getenv("MCP_TRANSPORT", "stdio").lower()


async def run_async() -> None:
    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    mcp = create_server()

    if args.list_tools:
        for name in sorted(TOOL_REGISTRY.keys()):
            print(f"  - {name}")
        print(f"\nTotal: {len(TOOL_REGISTRY)} tools")
        return

    transport = resolve_transport(args)
    host = args.host or os.getenv("MCP_HOST", "127.0.0.1")
    port = args.port or int(os.getenv("MCP_PORT", "10789"))
    path = args.path or os.getenv("MCP_PATH", "/mcp")

    logger.info("=" * 60)
    logger.info("PyWinAuto MCP Server v2.0.0")
    logger.info("Transport: %s", transport.upper())
    logger.info("Tools: %d", len(TOOL_REGISTRY))
    logger.info("Workflows: %d (35 executable)", len(pw.WORKFLOWS))
    logger.info("=" * 60)

    # Startup health check
    try:
        health = pw.health_check()
        logger.info("Health check: %s (all_ok=%s)", health["status"], health["all_ok"])
    except Exception as e:
        logger.warning("Startup health check failed: %s", e)

    try:
        if transport == "stdio":
            logger.info("Running in stdio mode — waiting for MCP client...")
            await mcp.run_stdio_async()
        elif transport == "http":
            endpoint = f"http://{host}:{port}{path}"
            logger.info("Running in HTTP mode: %s", endpoint)
            await mcp.run_http_async(host=host, port=port, path=path)
        else:
            logger.error("Unknown transport: %s", transport)
            sys.exit(1)
    except asyncio.CancelledError:
        logger.info("Server cancelled")
    except Exception as e:
        logger.critical("Server error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        _graceful_shutdown()


def main() -> None:
    """CLI entry point."""
    asyncio.run(run_async())


if __name__ == "__main__":
    main()
