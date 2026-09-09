# 常见问题 (FAQ)

## 目录

- [安装与环境](#安装与环境)
- [MCP 服务器](#mcp-服务器)
- [应用与窗口](#应用与窗口)
- [控件定位](#控件定位)
- [键盘与鼠标](#键盘与鼠标)
- [工作流与生成级](#工作流与生成级)
- [错误与调试](#错误与调试)
- [性能与优化](#性能与优化)
- [安全与权限](#安全与权限)

---

## 安装与环境

### Q: 支持哪些操作系统？

**A**: 仅支持 Windows 10/11。pywinauto 是 Windows 专用的 GUI 自动化库，不支持 macOS 或 Linux。

### Q: 支持哪些 Python 版本？

**A**: Python 3.10 及以上版本。推荐使用 Python 3.11+。

### Q: 如何验证安装是否成功？

**A**: 运行环境自检脚本：
```bash
python scripts/self_check.py
```
如果全部检查通过，则安装成功。

### Q: 安装 pywin32 后导入失败怎么办？

**A**: 运行 pywin32 的 post-install 脚本：
```bash
python Scripts/pywin32_postinstall.py -install
```
或者重新安装：
```bash
pip uninstall pywin32
pip install pywin32
```

### Q: 可以在虚拟环境中使用吗？

**A**: 可以。推荐使用虚拟环境隔离依赖：
```bash
python -m venv venv
venv\Scripts\activate
pip install pywinauto fastmcp pywin32 comtypes pydantic
```

---

## MCP 服务器

### Q: stdio 和 HTTP 模式有什么区别？

**A**:
- **stdio 模式**（默认）：通过标准输入输出通信，适合本地 MCP 客户端（如 Claude Desktop、Cursor），启动简单，无需配置端口
- **HTTP 模式**：通过 HTTP Streamable 协议通信，适合远程访问或需要多个客户端连接的场景，需要指定 host 和 port

### Q: 如何查看服务器注册了哪些工具？

**A**:
```bash
python scripts/mcp_server.py --list-tools
```
会列出全部 153 个工具的名称。

### Q: MCP 客户端连接不上服务器怎么办？

**A**:
1. 确认服务器正在运行且没有报错
2. stdio 模式：检查客户端配置中的命令路径和参数是否正确
3. HTTP 模式：检查端口是否被占用：`netstat -ano | findstr 10789`
4. 查看服务器日志（stderr 输出）获取详细错误信息
5. 尝试用 `--debug` 模式启动查看更多日志

### Q: 服务器启动后没有输出正常吗？

**A**: stdio 模式下，服务器启动后会等待客户端连接，不会在 stdout 输出内容（日志输出到 stderr）。这是正常的。可以用 `--list-tools` 验证服务器是否正常。

### Q: 如何优雅地停止服务器？

**A**: stdio 模式下，关闭 MCP 客户端或发送 Ctrl+C 即可。服务器会自动清理会话后退出。HTTP 模式下发送 SIGINT（Ctrl+C）。

---

## 应用与窗口

### Q: uia 和 win32 后端有什么区别？

**A**:
- **uia**（默认，推荐）：基于 UI Automation，支持现代应用（UWP、WPF、Electron、Chrome 等），控件信息更丰富
- **win32**：基于 Win32 API，适合传统 Win32 应用，速度更快但控件信息较少

选择建议：优先使用 uia，如果 uia 无法识别某些控件再尝试 win32。

### Q: 如何连接已经运行的应用？

**A**: 使用 `app_connect`，提供以下任一条件：
- `process`：进程 ID
- `handle`：窗口句柄
- `path`：可执行文件路径
- `title`：窗口标题（精确匹配）
- `title_re`：窗口标题（正则匹配）
- `class_name`：窗口类名

```python
app_connect(backend="uia", title="记事本")
```

### Q: 启动应用后找不到窗口怎么办？

**A**:
1. 增加等待时间：`app_start(cmd_line, timeout=10)`
2. 等待 CPU 空闲：`app_wait_cpu_usage_lower(app_id, threshold=5)`
3. 使用 `window_wait` 显式等待窗口出现
4. 检查应用是否真的启动了（任务管理器）
5. 确认使用了正确的后端

### Q: 如何获取应用的所有窗口？

**A**: 使用 `app_windows(app_id)`，返回顶层窗口列表。

### Q: 如何关闭应用？

**A**:
- 优雅关闭：`control_close(wrapper_id)`（发送 WM_CLOSE）
- 强制终止：`app_kill(app_id)`（终止进程）

---

## 控件定位

### Q: 如何查看应用的控件树？

**A**: 使用 `window_dump_tree(wrapper_id)`，会输出控件树的标识符列表。也可以使用 `analyze_ui(wrapper_id)` 获取更详细的结构分析。

### Q: 找不到控件怎么办？

**A**:
1. 先用 `window_dump_tree` 查看控件树，确认控件存在
2. 检查定位条件是否正确（title/control_type/auto_id/class_name）
3. 使用 `smart_find(description)` 智能定位
4. 增加搜索深度：`control_descendants(wrapper_id)`
5. 确认控件可见（有些控件需要滚动或展开才可见）
6. 尝试切换后端（uia ↔ win32）

### Q: auto_id 和 control_id 有什么区别？

**A**:
- `auto_id`：UIA 自动化 ID，是 UIA 特有的属性，通常更稳定
- `control_id`：Win32 控件 ID，是传统 Win32 控件的标识符

优先使用 `auto_id`（uia 后端），如果是传统 Win32 应用则使用 `control_id`。

### Q: 多个控件匹配时如何选择？

**A**: 使用 `found_index` 参数指定第几个匹配（从 0 开始）：
```python
control_child_window(wrapper_id, control_type="Button", found_index=0)
```
或者使用 `smart_find` 获取按相关性排序的候选列表。

### Q: 如何定位动态变化的控件？

**A**:
1. 使用 `auto_id`（最稳定）
2. 使用 `class_name` + `control_type` 组合
3. 使用 `title_re` 正则匹配
4. 使用 `smart_find` 模糊匹配
5. 使用 `adaptive_execute` 自适应执行（失败时自动调整）

---

## 键盘与鼠标

### Q: 如何发送特殊按键？

**A**: 使用 pywinauto 按键语法：
- `^a` = Ctrl+A
- `%{F4}` = Alt+F4
- `+{INS}` = Shift+Ins
- `{ENTER}` = 回车
- `{TAB}` = Tab
- `{ESC}` = Esc
- `{F1}`..`{F24}` = 功能键
- `{VK_SHIFT down}`...`{VK_SHIFT up}` = 按住/释放

### Q: 中文输入乱码怎么办？

**A**:
1. 使用 `safe_type_text()` 代替 `control_type_keys()`（自动使用剪贴板粘贴）
2. 确保 Python 文件编码为 UTF-8
3. 确认系统区域设置支持中文
4. 对于长文本，优先使用剪贴板方式

### Q: 如何模拟真实的鼠标点击？

**A**: 使用 `control_click_input()` 代替 `control_click()`：
- `control_click()`：发送 WM_LBUTTONDOWN/WM_LBUTTONUP 消息（更快，但不激活窗口）
- `control_click_input()`：移动鼠标到控件位置并真实点击（更真实，会激活窗口）

### Q: 如何拖拽操作？

**A**:
- 控件内拖拽：`control_drag_mouse(wrapper_id, dst_x, dst_y, src_x, src_y)`
- 屏幕坐标拖拽：`mouse_drag(src_x, src_y, dst_x, dst_y)`
- 复杂拖拽：`mouse_press()` → `mouse_move()` → `mouse_release()`

---

## 工作流与生成级

### Q: 100 条工作流中有多少可以直接执行？

**A**: 35 条可一键执行，65 条为指南型（需要根据具体应用调整参数）。可执行工作流主要是系统级操作（记事本、计算器、系统信息等）。

### Q: 如何创建自定义工作流？

**A**: 使用 `workflow_execute_custom(steps)`，步骤格式：
```json
[
  {"tool": "app_start", "params": {"cmd_line": "notepad.exe"}, "output_key": "app_id"},
  {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "wrapper_id"},
  {"tool": "safe_type_text", "params": {"wrapper_id": "$wrapper_id$", "text": "Hello"}}
]
```
支持条件分支、步骤重试、步骤超时、忽略错误等高级特性。

### Q: 自然语言生成工作流的准确率如何？

**A**: 对于常见操作（启动应用、输入文本、点击按钮、快捷键等），准确率较高（置信度通常 >0.8）。对于复杂或模糊的描述，置信度会降低，建议查看 `reasoning` 字段确认每步的推理依据，必要时手动调整。

### Q: 生成的脚本可以独立运行吗？

**A**: 可以。`generate_script()` 生成的是标准的 pywinauto Python 脚本，不依赖 MCP 服务器，可以直接运行：
```bash
python generated_script.py
```

### Q: 场景模板可以自定义吗？

**A**: 当前版本的场景模板是内置的（10 个）。如需自定义场景，可以：
1. 使用 `workflow_execute_custom` 定义自定义工作流
2. 直接修改 `generation_engine.py` 中的 `SCENARIOS` 字典
3. 未来版本将支持外部场景模板文件

---

## 错误与调试

### Q: 如何查看详细的错误信息？

**A**:
1. 工具返回的 `error` 字段包含错误消息
2. `error_type` 字段包含异常类型
3. 使用 `classify_error(error_message)` 获取错误分类和恢复建议
4. 服务器日志（stderr）包含完整的 traceback
5. 使用 `--debug` 模式启动服务器获取更多日志

### Q: "ElementNotFound" 错误怎么办？

**A**: 这是最常见的错误。排查步骤：
1. 确认控件存在（`window_dump_tree`）
2. 检查定位条件
3. 增加超时（`window_wait`）
4. 使用 `smart_find` 智能定位
5. 确认控件可见（滚动/展开）
6. 尝试切换后端

### Q: "Timeout" 错误怎么办？

**A**:
1. 增加超时时间：`timings_set(window_find_timeout=30)`
2. 降低操作速度：`timings_slow()`
3. 检查应用是否响应（CPU 使用率）
4. 使用 `adaptive_execute` 自适应执行（自动增加超时）
5. 检查是否有模态对话框阻塞

### Q: 如何调试工作流？

**A**:
1. 逐步执行，每步后检查返回值
2. 使用 `snapshot_ui_state` 捕获 UI 状态
3. 使用 `inspect_element` 深度探查控件
4. 在步骤间添加 `wait` 延迟
5. 使用 `get_call_stats` 查看调用统计

### Q: 会话过期了怎么办？

**A**: 会话 2 小时无访问会自动过期。过期后需要：
1. 重新启动或连接应用（`app_start` / `app_connect`）
2. 重新获取窗口和控件（`app_top_window` / `control_child_window`）
3. 使用 `cleanup_stale_sessions` 清理过期会话

---

## 性能与优化

### Q: 工具调用的延迟是多少？

**A**:
- 纯内存操作（会话管理、校验）：<10ms
- 元素查找：50-500ms（取决于控件树大小）
- 控件操作（点击、输入）：100-500ms
- 智能定位（smart_find）：200ms-3s（取决于搜索深度）

### Q: 如何加快自动化速度？

**A**:
1. 使用 `timings_fast()` 加快操作速度
2. 使用 `auto_id` 定位（比 title 匹配快）
3. 限定搜索范围（在父控件内搜索而非整个桌面）
4. 减少不必要的 `window_dump_tree` 调用
5. 使用 `batch_execute` 批量执行
6. 对于长文本使用剪贴板粘贴而非逐键输入

### Q: 控件树很大时如何优化？

**A**:
1. 限定搜索深度（`smart_find(search_depth=3)`）
2. 在最近的父控件内搜索
3. 使用 `control_type` 过滤
4. 使用 `auto_id` 直接定位
5. 避免频繁遍历整个控件树

---

## 安全与权限

### Q: 操作需要管理员权限的应用时怎么办？

**A**: MCP 服务器也需要以管理员身份运行：
1. 右键点击命令提示符
2. 选择"以管理员身份运行"
3. 重新启动 MCP 服务器

### Q: 自动化操作会被检测为恶意软件吗？

**A**: pywinauto 是合法的 UI 自动化库，不会被检测为恶意软件。但某些安全软件可能会对模拟键盘鼠标输入的行为进行告警。建议：
1. 将 Python 解释器加入安全软件白名单
2. 避免在敏感应用（银行、支付）中使用自动化
3. 仅在自己的电脑上使用

### Q: 会话 ID 会泄露敏感信息吗？

**A**: 不会。会话 ID（app_id/wrapper_id）是随机生成的标识符，仅在当前进程内有效，不包含任何敏感信息。服务器重启后全部失效。

### Q: 工具会发送数据到外部服务器吗？

**A**: 不会。所有操作都是纯本地的，不发送任何数据到外部服务器。MCP 服务器仅通过 stdio 或本地 HTTP 与客户端通信。

---

## 更多资源

- [快速开始指南](getting_started.md)
- [架构设计文档](architecture.md)
- [API 参考](../references/api_reference.md)
- [100 条工作流](../references/workflows.md)
- [元素定位策略](../references/element_locators.md)
- [使用指南](../references/usage_guide.md)
- [示例代码](examples/)
- [贡献指南](../CONTRIBUTING.md)
- [变更日志](../CHANGELOG.md)

如果以上 FAQ 没有解决你的问题，请在 [GitHub Issues](https://github.com/your-org/pywinauto-mcp/issues) 中提问。
