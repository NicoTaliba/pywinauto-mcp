# PyWinAuto MCP — API 参考文档

本文件列出 MCP 服务器暴露的全部 128 个工具，按功能分类。

## 目录

1. [会话管理](#1-会话管理)
2. [应用程序管理](#2-应用程序管理)
3. [窗口/控件查找与等待](#3-窗口控件查找与等待)
4. [控件操作 — 鼠标](#4-控件操作--鼠标)
5. [控件操作 — 键盘与文本](#5-控件操作--键盘与文本)
6. [控件操作 — 状态与选择](#6-控件操作--状态与选择)
7. [控件操作 — 窗口管理](#7-控件操作--窗口管理)
8. [控件操作 — 菜单与拖拽滚动](#8-控件操作--菜单与拖拽滚动)
9. [控件属性与检查](#9-控件属性与检查)
10. [控件树导航](#10-控件树导航)
11. [特定控件类型](#11-特定控件类型)
12. [全局键盘](#12-全局键盘)
13. [全局鼠标](#13-全局鼠标)
14. [剪贴板](#14-剪贴板)
15. [时序配置](#15-时序配置)
16. [系统信息](#16-系统信息)
17. [窗口/元素查找](#17-窗口元素查找)
18. [任务栏](#18-任务栏)
19. [桌面](#19-桌面)
20. [菜单](#20-菜单)
21. [通用调用接口](#21-通用调用接口)

---

## 1. 会话管理

| 工具名 | 说明 |
|--------|------|
| `list_sessions` | 列出所有活跃的应用和控件会话 |
| `close_session` | 关闭一个应用会话并释放关联控件 |
| `close_all_sessions` | 关闭所有会话 |

## 2. 应用程序管理

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `app_start` | `cmd_line`, `backend="uia"`, `timeout`, `work_dir`, `wait_for_idle=True` | 启动应用程序 |
| `app_connect` | `backend="uia"`, `process`, `handle`, `path`, `title`, `title_re`, `class_name`, `class_name_re` | 连接到已运行的应用 |
| `app_kill` | `app_id`, `soft=False` | 终止应用 |
| `app_windows` | `app_id` | 列出应用的所有顶层窗口 |
| `app_top_window` | `app_id` | 获取当前顶层窗口 |
| `app_active_window` | `app_id` | 获取活动窗口 |
| `app_window` | `app_id`, `title`, `title_re`, `class_name`, `class_name_re`, `control_type`, `auto_id`, `control_id`, `handle`, `found_index` | 按条件查找窗口 |
| `app_cpu_usage` | `app_id`, `interval` | 获取 CPU 使用率 |
| `app_is64bit` | `app_id` | 检查进程是否 64 位 |
| `app_is_process_running` | `app_id` | 检查进程是否运行中 |
| `app_wait_cpu_usage_lower` | `app_id`, `threshold=2.5`, `timeout`, `usage_interval` | 等待 CPU 使用率低于阈值 |
| `app_wait_for_process_exit` | `app_id`, `timeout`, `retry_interval` | 等待进程退出 |

## 3. 窗口/控件查找与等待

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `window_find` | `app_id`, `backend="uia"`, `title`, `title_re`, `class_name`, `class_name_re`, `control_type`, `auto_id`, `control_id`, `handle`, `found_index` | 查找窗口/控件 |
| `window_exists` | `wrapper_id`, `timeout`, `retry_interval` | 检查窗口是否存在 |
| `window_wait` | `wrapper_id`, `wait_for="visible"`, `timeout`, `retry_interval` | 等待窗口进入指定状态 |
| `window_dump_tree` | `wrapper_id`, `depth` | 打印控件树标识符 |
| `window_print_control_identifiers` | `wrapper_id`, `depth` | 同 dump_tree |
| `window_get_wrapper` | `wrapper_id` | 获取控件会话的完整信息 |
| `window_release` | `wrapper_id` | 释放控件会话 |

**wait_for 状态值**: `exists`, `visible`, `enabled`, `ready`(=visible+enabled)，可用空格组合。

## 4. 控件操作 — 鼠标

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `control_click` | `wrapper_id`, `button="left"`, `x`, `y`, `double=False` | 单击控件 |
| `control_double_click` | `wrapper_id`, `button="left"`, `x`, `y` | 双击控件 |
| `control_right_click` | `wrapper_id`, `x`, `y` | 右键单击 |
| `control_click_input` | `wrapper_id`, `button="left"`, `x`, `y`, `double=False` | 使用 send_message 点击（更真实，先激活窗口） |
| `control_press_mouse` | `wrapper_id`, `button="left"`, `x`, `y` | 按下鼠标键 |
| `control_release_mouse` | `wrapper_id`, `button="left"`, `x`, `y` | 释放鼠标键 |
| `control_move_mouse` | `wrapper_id`, `x`, `y` | 移动鼠标到控件上方 |

## 5. 控件操作 — 键盘与文本

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `control_type_keys` | `wrapper_id`, `keys`, `with_spaces`, `with_tabs`, `with_newlines`, `turn_off_numlock=True`, `set_foreground=True`, `pause` | 向控件发送按键（支持 pywinauto 语法） |
| `control_set_text` | `wrapper_id`, `text` | 设置编辑框文本（SetText） |
| `control_set_edit_text` | `wrapper_id`, `text` | 设置编辑框文本（UIA Value 模式，更可靠） |
| `control_get_text` | `wrapper_id` | 获取窗口/控件文本 |

**按键语法**: `^a`=Ctrl+A, `%{F4}`=Alt+F4, `+{INS}`=Shift+Ins, `{ENTER}`, `{TAB}`, `{ESC}`, `{F1}`..`{F24}`

## 6. 控件操作 — 状态与选择

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `control_select` | `wrapper_id`, `item`, `index` | 选择列表/组合框项 |
| `control_check` | `wrapper_id` | 勾选复选框 |
| `control_uncheck` | `wrapper_id` | 取消勾选 |
| `control_is_checked` | `wrapper_id` | 获取勾选状态 |
| `control_expand` | `wrapper_id` | 展开可折叠元素 |
| `control_collapse` | `wrapper_id` | 折叠元素 |
| `control_get_expand_state` | `wrapper_id` | 获取展开状态 |
| `control_set_focus` | `wrapper_id` | 设置键盘焦点 |
| `control_invoke` | `wrapper_id` | 调用默认操作（UIA Invoke） |
| `control_get_value` | `wrapper_id` | 获取 Value 模式值 |
| `control_set_value` | `wrapper_id`, `value` | 设置 Value 模式值 |
| `control_get_range_value` | `wrapper_id` | 获取范围值（滑块/进度条） |
| `control_get_item_texts` | `wrapper_id` | 获取列表/组合框所有项文本 |
| `control_selected_index` | `wrapper_id` | 获取选中索引 |
| `control_selected_text` | `wrapper_id` | 获取选中文本 |

## 7. 控件操作 — 窗口管理

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `control_close` | `wrapper_id` | 关闭窗口 |
| `control_minimize` | `wrapper_id` | 最小化 |
| `control_maximize` | `wrapper_id` | 最大化 |
| `control_restore` | `wrapper_id` | 还原 |
| `control_get_show_state` | `wrapper_id` | 获取窗口显示状态 |
| `control_move_window` | `wrapper_id`, `x`, `y`, `width`, `height` | 移动并可选调整大小 |
| `control_resize` | `wrapper_id`, `width`, `height` | 调整大小 |

## 8. 控件操作 — 菜单与拖拽滚动

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `control_menu_select` | `wrapper_id`, `path` | 按路径选择菜单项（如 `File->Save`） |
| `control_drag_mouse` | `wrapper_id`, `dst_x`, `dst_y`, `src_x`, `src_y`, `button="left"` | 在控件上拖拽 |
| `control_scroll` | `wrapper_id`, `direction="down"`, `amount=1`, `count=1` | 滚动控件 |
| `control_scroll_at_point` | `wrapper_id`, `direction`, `amount`, `count`, `x`, `y` | 在指定点滚动 |

## 9. 控件属性与检查

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `control_get_properties` | `wrapper_id` | 获取所有可用属性 |
| `control_get_rectangle` | `wrapper_id` | 获取边界矩形 |
| `control_get_class_name` | `wrapper_id` | 获取类名 |
| `control_get_backend` | `wrapper_id` | 获取后端名称 |
| `control_get_handle` | `wrapper_id` | 获取窗口句柄 |
| `control_is_active` | `wrapper_id` | 检查是否活动 |
| `control_is_visible` | `wrapper_id` | 检查是否可见 |
| `control_is_enabled` | `wrapper_id` | 检查是否启用 |
| `control_capture_as_image` | `wrapper_id`, `save_path` | 截图（返回路径或 base64） |
| `control_get_tool_tip` | `wrapper_id` | 获取工具提示文本 |
| `control_verify_action` | `wrapper_id`, `action="click"` | 验证操作是否可执行 |
| `control_get_boundary_rect` | `wrapper_id` | 获取 UIA 边界矩形 |
| `control_get_legacy_iaccessible_property` | `wrapper_id`, `property_name` | 获取遗留 IAccessible 属性 |

## 10. 控件树导航

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `control_child_window` | `wrapper_id`, `title`, `title_re`, `class_name`, `class_name_re`, `control_type`, `auto_id`, `control_id`, `found_index` | 按条件查找子控件 |
| `control_children` | `wrapper_id` | 获取直接子控件 |
| `control_descendants` | `wrapper_id` | 获取所有后代控件 |

## 11. 特定控件类型

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `combobox_select` | `wrapper_id`, `item` | 选择组合框项 |
| `combobox_get_items` | `wrapper_id` | 获取组合框所有项 |
| `listbox_select` | `wrapper_id`, `item` | 选择列表框项 |
| `listbox_get_selected` | `wrapper_id` | 获取列表框选中项 |
| `tab_select` | `wrapper_id`, `tab` | 选择标签页 |
| `tab_get_selected` | `wrapper_id` | 获取选中标签页 |
| `tree_select` | `wrapper_id`, `path` | 选择树节点（路径如 `Root\Child`） |
| `tree_expand` | `wrapper_id`, `path` | 展开树节点 |
| `tree_collapse` | `wrapper_id`, `path` | 折叠树节点 |
| `tree_get_selected` | `wrapper_id` | 获取选中树节点 |
| `slider_get_position` | `wrapper_id` | 获取滑块位置 |
| `slider_set_position` | `wrapper_id`, `value` | 设置滑块位置 |
| `progress_get_position` | `wrapper_id` | 获取进度条位置 |

## 12. 全局键盘

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `keyboard_send_keys` | `keys`, `with_spaces`, `with_tabs`, `with_newlines`, `turn_off_numlock=True`, `pause` | 向活动窗口发送按键 |
| `keyboard_key_press` | `key` | 按下并保持按键 |
| `keyboard_key_release` | `key` | 释放按键 |

## 13. 全局鼠标

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `mouse_click` | `button="left"`, `x`, `y`, `double=False` | 在屏幕坐标点击 |
| `mouse_double_click` | `button="left"`, `x`, `y` | 双击 |
| `mouse_right_click` | `x`, `y` | 右键点击 |
| `mouse_move` | `x`, `y` | 移动鼠标 |
| `mouse_press` | `button="left"`, `x`, `y` | 按下鼠标键 |
| `mouse_release` | `button="left"`, `x`, `y` | 释放鼠标键 |
| `mouse_scroll` | `direction="up"`, `amount=1`, `x`, `y` | 滚动滚轮 |
| `mouse_drag` | `src_x`, `src_y`, `dst_x`, `dst_y`, `button="left"` | 拖拽 |
| `mouse_get_position` | — | 获取当前鼠标位置 |

## 14. 剪贴板

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `clipboard_get_data` | — | 获取剪贴板文本 |
| `clipboard_set_data` | `text` | 设置剪贴板文本 |
| `clipboard_empty` | — | 清空剪贴板 |
| `clipboard_get_formats` | — | 获取可用剪贴板格式 |

## 15. 时序配置

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `timings_get` | — | 获取当前时序配置 |
| `timings_set` | `window_find_timeout`, `window_find_retry_interval`, `exists_timeout`, `exists_retry_interval`, `after_click_wait`, `after_menu_wait`, `slow_motion_delay`, ... | 设置时序值 |
| `timings_defaults` | — | 恢复默认时序 |
| `timings_slow` | — | 设置慢速模式（调试用） |
| `timings_fast` | — | 设置快速模式 |

## 16. 系统信息

| 工具名 | 说明 |
|--------|------|
| `sysinfo_is_x64_python` | Python 是否 64 位 |
| `sysinfo_is_x64_os` | 操作系统是否 64 位 |
| `sysinfo_os_arch` | 操作系统架构 |
| `sysinfo_python_bitness` | Python 位数 |

## 17. 窗口/元素查找

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `find_windows` | `backend="uia"`, `title`, `title_re`, `class_name`, `class_name_re`, `process`, `handle`, `enabled_only`, `visible_only`, `top_level_only` | 查找窗口句柄列表 |
| `find_elements` | `backend="uia"`, `title`, `title_re`, `class_name`, `control_type`, `auto_id`, `process`, `depth` | 查找 UIA 元素 |
| `enumerate_windows` | `backend="uia"` | 枚举所有顶层窗口 |

## 18. 任务栏

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `taskbar_click_on_button` | `text`, `by="title"` | 点击任务栏按钮 |
| `taskbar_get_button` | `text` | 获取任务栏按钮 |
| `taskbar_get_start_button` | — | 获取开始按钮 |
| `taskbar_get_search_edit` | — | 获取搜索框 |
| `taskbar_get_system_tray` | — | 获取系统托盘 |

## 19. 桌面

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `desktop_windows` | `backend="uia"` | 获取所有顶层桌面窗口 |
| `desktop_active_window` | `backend="uia"` | 获取当前活动窗口 |
| `desktop_window` | `backend="uia"`, `title`, `title_re`, `class_name`, `control_type`, `auto_id`, `handle`, `found_index` | 按条件查找桌面窗口 |

## 20. 菜单

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `menu_get_items` | `wrapper_id`, `path` | 获取菜单项列表 |
| `menu_click_item` | `wrapper_id`, `path` | 按路径点击菜单项 |

## 21. 通用调用接口

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `control_call_method` | `wrapper_id`, `method`, `arg1`, `arg2`, `arg3` | 调用控件对象的任意方法（逃逸舱） |
| `control_get_attribute` | `wrapper_id`, `attribute` | 获取控件对象的任意属性 |

---

## 返回值格式

所有工具统一返回：

```json
{
  "status": "success | error",
  "data": { ... }  // 成功时的结果
}
```

错误时：

```json
{
  "status": "error",
  "error": "错误信息",
  "error_type": "异常类名"
}
```

## 会话 ID 说明

- `app_id`: 格式 `app_xxxxxxxxxxxx`，由 `app_start` / `app_connect` 返回
- `wrapper_id`: 格式 `ctrl_xxxxxxxxxxxx`，由窗口/控件查找工具返回
- 会话在 MCP 服务器运行期间持久化，可跨多次工具调用复用
- 使用 `list_sessions` 查看当前会话，`close_session` / `window_release` 释放
