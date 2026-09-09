# PyWinAuto MCP — 使用指南

## 快速开始

### 1. 启动 MCP 服务器

```bash
# Stdio 模式（默认，用于 Claude Desktop、Cursor 等 MCP 客户端）
python scripts/mcp_server.py

# HTTP 模式
python scripts/mcp_server.py --http --port 10789

# 查看所有可用工具
python scripts/mcp_server.py --list-tools
```

### 2. MCP 客户端配置示例

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "pywinauto": {
      "command": "python",
      "args": ["C:/path/to/pywinauto-mcp/scripts/mcp_server.py"]
    }
  }
}
```

**Cursor / Continue**:
```json
{
  "mcpServers": {
    "pywinauto": {
      "command": "python",
      "args": ["C:/path/to/pywinauto-mcp/scripts/mcp_server.py"]
    }
  }
}
```

## 典型工作流

### 工作流 1：启动应用并操作

```
1. app_start(cmd_line="notepad.exe")
   → 返回 app_id="app_abc123"

2. app_top_window(app_id="app_abc123")
   → 返回 wrapper_id="ctrl_def456"，包含窗口信息

3. control_type_keys(wrapper_id="ctrl_def456", keys="Hello, World!")
   → 在记事本中输入文字

4. keyboard_send_keys(keys="^s")
   → Ctrl+S 保存

5. app_kill(app_id="app_abc123")
   → 关闭应用
```

### 工作流 2：连接到已运行的应用

```
1. app_connect(backend="uia", title_re=".*Notepad.*")
   → 返回 app_id

2. app_window(app_id=..., control_type="Edit", found_index=0)
   → 找到编辑框控件

3. control_get_text(wrapper_id=...)
   → 获取编辑框内容

4. control_set_text(wrapper_id=..., text="新内容")
   → 设置编辑框内容
```

### 工作流 3：操作计算器

```
1. app_start(cmd_line="calc.exe", backend="uia")

2. app_top_window(app_id=...)

3. window_dump_tree(wrapper_id=...)
   → 查看控件树，找到按钮的名称/automation_id

4. control_child_window(wrapper_id=..., control_type="Button", auto_id="num7Button")
   → 找到数字 7 按钮

5. control_click(wrapper_id=...)
   → 点击 7

6. control_child_window(..., auto_id="plusButton") → control_click
   → 点击 +

7. control_child_window(..., auto_id="num3Button") → control_click
   → 点击 3

8. control_child_window(..., auto_id="equalButton") → control_click
   → 点击 =

9. control_child_window(..., control_type="Text", found_index=0)
   → 找到结果显示

10. control_get_text(wrapper_id=...)
    → 获取结果 "10"
```

### 工作流 4：菜单操作

```
1. app_start(cmd_line="notepad.exe")

2. app_top_window(app_id=...)

3. control_type_keys(wrapper_id=..., keys="测试内容")

4. control_menu_select(wrapper_id=..., path="File->Save As...")
   → 打开另存为对话框

5. app_window(app_id=..., title_re=".*Save As.*")
   → 找到另存为对话框

6. control_child_window(wrapper_id=..., control_type="Edit", found_index=1)
   → 找到文件名输入框

7. control_set_text(wrapper_id=..., text="test.txt")

8. control_child_window(wrapper_id=..., control_type="Button", title="Save")
   → 找到保存按钮

9. control_click(wrapper_id=...)
```

### 工作流 5：全局鼠标键盘操作

```
1. mouse_move(x=500, y=300)
   → 移动鼠标到屏幕坐标

2. mouse_click(button="left", x=500, y=300)
   → 点击

3. mouse_drag(src_x=100, src_y=100, dst_x=500, dst_y=500)
   → 拖拽

4. mouse_scroll(direction="down", amount=3)
   → 向下滚动 3 格

5. keyboard_send_keys(keys="^c")
   → 复制

6. keyboard_send_keys(keys="^v")
   → 粘贴

7. clipboard_get_data()
   → 获取剪贴板内容
```

## 后端选择

### UIA 后端（推荐，默认）

- 支持现代 Windows 应用（WPF、UWP、WinForms、Qt 等）
- 可访问 `control_type`、`auto_id`、`name` 等 UIA 属性
- 支持 Invoke、Value、Toggle、ExpandCollapse、Selection 等模式
- 启动方式：`backend="uia"`

### Win32 后端

- 适用于传统 Win32 应用（MFC、VB6、旧版 Delphi 等）
- 基于窗口句柄和 Win32 API
- 启动方式：`backend="win32"`

**选择建议**：先尝试 UIA，如果无法识别控件再切换 Win32。

## 元素定位策略

### 优先级从高到低

1. **`auto_id`**（UIA）— 最稳定，开发者设置的唯一 ID
2. **`control_type` + `found_index`** — 按类型和索引定位
3. **`control_id`**（Win32）— 控件 ID
4. **`title` / `title_re`** — 文本匹配，可能因本地化变化
5. **`class_name`** — 类名，可能不唯一
6. **`handle`** — 窗口句柄，每次运行不同

### 模糊匹配

pywinauto 支持模糊匹配，`title="OK"` 可以匹配 "OK", "OK ", "&OK" 等。
使用 `title_re` 进行正则匹配：`title_re=".*Save.*"`

### 查看可用定位信息

```
1. window_dump_tree(wrapper_id=..., depth=3)
   → 打印控件树，包含每个控件的标题、类名、control_type、auto_id

2. control_get_properties(wrapper_id=...)
   → 获取控件的所有属性

3. control_children(wrapper_id=...)
   → 列出直接子控件
```

## 常见问题

### Q: 找不到控件怎么办？

1. 使用 `window_dump_tree` 查看实际的控件树结构
2. 确认使用了正确的后端（UIA vs Win32）
3. 尝试更宽松的匹配条件（`title_re` 代替 `title`）
4. 使用 `found_index` 处理多个匹配
5. 检查控件是否需要先展开/滚动才能访问

### Q: 点击没有反应？

1. 确认控件已启用：`control_is_enabled`
2. 确认控件可见：`control_is_visible`
3. 尝试 `control_click_input` 代替 `control_click`（更真实的点击）
4. 先设置焦点：`control_set_focus`
5. 检查是否有模态对话框阻挡

### Q: 输入文字不正确？

1. 使用 `control_set_text` / `control_set_edit_text` 代替 `control_type_keys`
2. 对于特殊字符，使用 `keyboard_send_keys` 配合剪贴板：
   - `clipboard_set_data(text="特殊文本")`
   - `keyboard_send_keys(keys="^v")`

### Q: 应用启动后窗口还没出现？

1. 使用 `app_top_window` 时会自动等待
2. 显式等待：`window_wait(wrapper_id=..., wait_for="visible", timeout=10)`
3. 增加 `app_start` 的 `timeout` 参数

### Q: 如何处理动态加载的内容？

1. 使用 `window_wait` 等待元素出现
2. 使用 `window_exists` 轮询检查
3. 调整 `timings_set` 增加超时时间

## 最佳实践

1. **始终使用会话管理**：通过 `app_id` 和 `wrapper_id` 复用连接，避免重复查找
2. **先探查再操作**：用 `window_dump_tree` 了解控件结构后再编写操作
3. **使用 UIA 后端**：除非应用明确不支持，否则优先使用 UIA
4. **合理设置等待**：对于慢响应应用，使用 `window_wait` 而不是固定 sleep
5. **清理会话**：任务完成后调用 `app_kill` 或 `close_session` 释放资源
6. **错误处理**：所有工具返回 `status` 字段，检查 `status=="success"` 后再继续
