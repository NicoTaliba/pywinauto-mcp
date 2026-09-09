# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- More scenario templates (Excel/Word/Outlook Office automation)
- Operation recording and playback (Record & Replay)
- Visual element locating (screenshot-based image matching)
- Multi-monitor support + DPI awareness
- Remote desktop automation

---

## [3.1.0] - 2026-09-09

### System Operations 📦

#### New System Tools (9 tools)
- **`system_download_file(url, save_path, timeout)`** — Download file from URL with progress tracking
- **`system_run_command(command, timeout, capture_output, work_dir)`** — Execute system command (CMD/PowerShell)
- **`system_process_running(process_name)`** — Check if a process is running, return PID list
- **`system_file_exists(path)`** — Check if file/directory exists, return file info
- **`system_get_installed_software()`** — Get list of installed software from Windows registry (HKLM + HKCU, 32/64-bit)
- **`system_find_software(name_pattern)`** — Search installed software by name (case-insensitive substring)
- **`system_uninstall_software(display_name, silent, timeout)`** — Uninstall software by display name, auto-detect silent flags
- **`system_install_package(installer_path, args, timeout, silent)`** — Install software package (EXE/MSI), auto-detect silent flags
- **`system_download_and_install(url, save_path, install_args, timeout, silent)`** — One-click download and install

#### New Workflows (WF101-WF105)
- **WF101**: Download installer and install (uninstall first if already installed)
- **WF102**: Batch check software installation status
- **WF103**: Silent uninstall specified software
- **WF104**: Download file to specified directory
- **WF105**: Execute command and wait for completion

### Documentation 📚
- **CREDITS.md** — Added attribution document listing all referenced open source projects, documentation, and resources
- **install_package_demo.py** — New example script demonstrating WF101 workflow and all system tools (dry-run mode by default)

### Enhanced
- MCP server: 162 tools (153 → 162, +9 system operations)
- Workflows: 105 (100 → 105, +5 software installation & management)
- Workflow categories: 21 (20 → 21, +1 "软件安装与管理")
- Test suite: 85 unit tests (72 → 85, +13 system operation tests)
- Workflow ID validation: now enforces upper bound WF001-WF105

### Fixed
- Workflow ID validation now properly enforces range (WF001-WF105), not just format

---

## [3.0.0] - 2026-09-09

### Generation-Level Features 🚀

#### NL2Workflow — Natural Language to Workflow
- **New tool**: `generate_workflow(description, context?, auto_execute?)`
- **New tool**: `generate_and_execute(description, context?)`
- 19 action template patterns (launch/connect/close/find/focus/screenshot/type/click/shortcut/menu/wait)
- Auto-completion: auto-get top window after app launch, auto-find target control before click
- Output: step list + reasoning process + confidence score + validation result
- Parameter extraction with regex + type conversion

#### SmartLocator — Intelligent Element Locator
- **New tool**: `smart_find(description, wrapper_id?, backend?, max_results?, search_depth?)`
- 16 control type auto-detection (Button/Edit/ComboBox/CheckBox/Tab/Tree/etc.)
- 4-level fuzzy matching: exact(1.0) > contains(0.8+) > acronym(0.6) > char similarity(0.5)
- Multi-dimensional scoring: control type + title fuzzy match + auto_id + visibility/enabled
- Best match auto-registered as wrapper session for direct subsequent operations

#### AdaptiveExec — Adaptive Self-Healing Executor
- **New tool**: `adaptive_execute(steps, max_retries_per_step?, auto_recover?, stop_on_error?, name?)`
- 6 error categories auto-detection: element_not_found / timeout / element_disabled / element_not_visible / permission_denied / session_expired
- 2-4 recovery strategies per category, applied in sequence
- Complete recovery log: error, category, applied strategy, result per step
- Exponential backoff retry with configurable max retries per step

#### UIAnalyzer — UI Understanding & Analysis
- **New tool**: `analyze_ui(wrapper_id?, depth?, include_properties?)`
- **New tool**: `describe_element(wrapper_id)`
- **New tool**: `find_interactive_elements(wrapper_id?, control_type?, only_visible?, only_enabled?)`
- UI structure analysis: element stats + type distribution + natural language description
- Control natural language description: type/text/class/state/position/supported operations
- Interactive element discovery: 17 interactive type filters

#### ScenarioLib — Scenario Template Library
- **New tool**: `list_scenarios(category?)`
- **New tool**: `apply_scenario(scenario_id, params?, auto_execute?)`
- 10 built-in scenarios: notepad_basic, calculator_math, browser_navigate, form_fill, dialog_confirm, screenshot_capture, menu_navigation, clipboard_operations, window_management, system_info
- Parameter schema per scenario (name/type/default/description)
- Auto parameter filling + step validation on apply

#### ScriptGen — Script Generator
- **New tool**: `generate_script(steps? / workflow_id? / scenario_id?, script_name?, include_comments?)`
- Generate standalone runnable pywinauto Python scripts
- 25+ tool code generation with automatic variable management
- Step comments + TODO markers for unsupported tools
- Source: workflow ID, scenario template, or custom steps

### Enhanced
- MCP server: 153 tools registered (143 base + 10 generation)
- Test suite: 72 unit tests (52 base + 20 generation)
- SKILL.md: comprehensive v3.0 generation-level documentation
- generation_engine.py: 58KB core generation engine module

### Fixed
- Confidence score calculation capped at 1.0
- generate_script respects script_name parameter when provided

---

## [2.0.0] - 2026-09-09

### Enterprise Hardening 🛡️

#### Input Validation
- 10 validators: backend, mouse_button, scroll_direction, nonempty, positive, timeout, workflow_id
- All critical parameters validated before execution

#### Retry Mechanism
- `_with_retry()` helper with exponential backoff
- `safe_click()`: precondition verification (visible/enabled) + retry
- `safe_type_text()`: focus verification + clipboard optimization + retry

#### Timeout Protection
- `_with_timeout()` thread-level timeout
- Workflow steps support `timeout` parameter
- `OperationTimeoutError` custom exception

#### Thread Safety
- `RLock` protecting all session operations
- Thread-safe session registry

#### Session TTL
- 2-hour auto-expiry for idle sessions
- `cleanup_stale_sessions()` manual cleanup
- Session metadata: created, last_used, age, idle time

#### Error Classification
- 6 error categories: element_not_found, timeout, element_disabled, element_not_visible, permission_denied, session_expired, unknown
- Auto-recovery suggestions per category
- `classify_error()` tool for arbitrary error messages

#### Health & Diagnostics
- `health_check()`: 9 checks (Python/pywinauto/pywin32/comtypes/fastmcp/platform/sessions/call_stats/basic_operation)
- `get_capabilities()`: version, tool count, workflow count, feature list
- `get_call_stats()`: total calls, errors, error rate, per-tool breakdown
- Call statistics recording infrastructure

#### Safe Operations
- `safe_click()`: verify visible + enabled before click, retry on failure
- `safe_type_text()`: verify focus, clear first, clipboard paste for long text, retry

#### Batch & Snapshot
- `batch_execute()`: sequential execution with `$prev.field$` result references
- `snapshot_ui_state()`: capture UI state (control tree, text values, check states)
- `inspect_element()`: deep element inspection (all properties, methods, children)

### Enhanced
- MCP server: 143 tools (128 → 143)
- Test suite: 55 unit tests
- Graceful server shutdown with session cleanup
- Startup health check logging
- SKILL.md: comprehensive v2.0 documentation

### Fixed
- sysinfo function names (is_x64_Python / is_x64_OS, case-sensitive)
- timings _timings dictionary access pattern
- clipboard SetClipboardData (use win32clipboard directly)
- Session management thread safety

---

## [1.0.0] - 2026-09-09

### Initial Release 🎉

#### Core API Wrapper (128 functions)
- Application management: app_start, app_connect, app_kill, app_window, app_top_window, app_windows, app_cpu_usage, app_wait_cpu_usage_lower, app_wait_for_process_exit, app_is_process_running
- Window find & wait: window_find, window_exists, window_wait, window_dump_tree
- Control mouse operations: control_click, control_double_click, control_right_click, control_click_input, control_drag_mouse, control_press_mouse, control_release_mouse, control_move_mouse
- Control keyboard & text: control_type_keys, control_set_text, control_set_edit_text, control_get_text, control_selected_text
- Control state & selection: control_select, control_check, control_uncheck, control_expand, control_collapse, control_invoke, control_set_value, control_verify_action
- Window management: control_close, control_maximize, control_minimize, control_move_window, control_set_focus
- Menu & scroll: control_menu_select, control_scroll, control_scroll_at_point
- Control properties: control_get_properties, control_get_rectangle, control_get_class_name, control_is_visible, control_is_enabled, control_is_checked, control_capture_as_image, control_get_legacy_iaccessible_property
- Control tree navigation: control_child_window, control_children, control_descendants
- Specific controls: combobox_select, combobox_get_items, listbox_select, listbox_get_selected, tab_select, tab_get_selected, tree_select, tree_expand, tree_collapse, tree_get_selected, slider_get_position, slider_set_position, progress_get_position
- Global keyboard: keyboard_send_keys, keyboard_key_press, keyboard_key_release
- Global mouse: mouse_click, mouse_double_click, mouse_right_click, mouse_move, mouse_press, mouse_release, mouse_scroll, mouse_drag, mouse_get_position
- Clipboard: clipboard_get_data, clipboard_set_data, clipboard_empty, clipboard_get_formats
- Timings: timings_get, timings_set, timings_defaults, timings_slow, timings_fast
- System info: sysinfo_is_x64_python, sysinfo_is_x64_os, sysinfo_os_arch, sysinfo_python_bitness
- Element finding: find_windows, find_elements, enumerate_windows
- Taskbar: taskbar_click_on_button, taskbar_get_button, taskbar_get_start_button, taskbar_get_search_edit, taskbar_get_system_tray
- Desktop: desktop_windows, desktop_active_window, desktop_window
- Menu: menu_get_items, menu_click_item
- Generic escape hatch: control_call_method, control_get_attribute
- Session management: list_sessions, close_session, close_all_sessions

#### MCP Server
- FastMCP 4.x based server
- stdio transport (default)
- HTTP Streamable transport
- `--list-tools` command
- 128 tools all registered successfully

#### 100 Pre-built Workflows
- 20 categories × 5 workflows each
- 35 executable workflows
- Categories: app lifecycle, window management, text input, button interaction, menu navigation, list & combobox, file dialogs, dialog handling, keyboard shortcuts, mouse operations, data extraction, validation & wait, browser automation, system operations, screenshot capture, form filling, table/grid, tree control, tab control, error recovery

#### Reference Documentation
- api_reference.md: 128 tools API reference
- usage_guide.md: usage guide with examples
- element_locators.md: element locating strategies
- workflows.md: 100 workflows detailed reference

---

[Unreleased]: https://github.com/your-org/pywinauto-mcp/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/your-org/pywinauto-mcp/releases/tag/v3.0.0
[2.0.0]: https://github.com/your-org/pywinauto-mcp/releases/tag/v2.0.0
[1.0.0]: https://github.com/your-org/pywinauto-mcp/releases/tag/v1.0.0
