---
name: pywinauto-mcp
description: Windows GUI 自动化 Skill（v3.0 生成级），基于 pywinauto 封装 153 个 API 工具并内置 100 条桌面 GUI 常用工作流 + 10 个场景模板，通过 MCP（Model Context Protocol）CLI 服务器暴露为工具。具备生成级能力：自然语言转工作流（NL2Workflow）、智能元素定位（smart_find 模糊匹配+语义排序）、自适应自愈执行（adaptive_execute 错误分析+策略调整+自动恢复）、UI 理解与分析（analyze_ui/describe_element）、场景模板库、脚本生成器（generate_script）。企业级加固：输入校验、重试机制、超时保护、线程安全会话、错误分类与恢复建议、健康检查、安全操作封装、批量执行、状态快照。当用户需要自动化 Windows 桌面应用、用自然语言描述自动化任务、智能查找控件、自适应执行、操作 GUI 控件、模拟键盘鼠标输入等场景时使用。支持 UIA 和 Win32 两种后端，可通过 stdio 或 HTTP 传输运行 MCP 服务器。触发关键词包括：pywinauto、windows 自动化、GUI 自动化、桌面自动化、UI 自动化、自然语言自动化、智能定位、自适应执行、NL2Workflow、生成工作流、脚本生成等。
---

# PyWinAuto MCP — Windows GUI 自动化 Skill (v3.0 生成级)

基于 [pywinauto](https://github.com/pywinauto/pywinauto) 的完整 Windows GUI 自动化工具集，通过 MCP 服务器暴露 **153 个封装 API 工具**，内置 **100 条桌面 GUI 常用工作流**（35 条可一键执行）和 **10 个场景模板**，支持从自然语言描述自动生成可执行工作流、智能元素定位、自适应自愈执行、UI 理解分析、脚本生成等生成级能力。

**v3.0 生成级增强**：
- **NL2Workflow**：自然语言描述 → 可执行工作流（带推理过程和置信度）
- **SmartLocator**：智能元素定位（模糊匹配+语义排序+自动遍历控件树）
- **AdaptiveExec**：自适应自愈执行（6类错误自动识别+恢复策略库+指数退避重试）
- **UIAnalyzer**：UI 理解与分析（界面结构描述+可交互元素发现+控件自然语言描述）
- **ScenarioLib**：10 个场景模板（记事本/计算器/浏览器/表单/对话框/截图/菜单/剪贴板/窗口/系统信息）
- **ScriptGen**：工作流 → 独立可运行 pywinauto Python 脚本生成

**v2.0 加固增强**：输入校验、重试机制（指数退避）、超时保护、线程安全会话（2小时TTL自动清理）、错误分类与恢复建议、健康检查、安全操作封装（safe_click/safe_type_text）、批量执行、状态快照、元素深度探查、自定义工作流（条件分支/步骤重试/超时/忽略错误）、72项单元测试、环境自检脚本。

## 架构概览

```
pywinauto-mcp/
├── SKILL.md                          # 本文件
├── scripts/
│   ├── mcp_server.py                 # MCP CLI 服务器（stdio/HTTP，162 工具，优雅关闭）
│   ├── pywinauto_wrapper.py          # 143 API 封装层 + 100 工作流引擎 + 重试/校验/超时/线程安全
│   ├── generation_engine.py          # v3.0 生成级引擎（NL2Workflow/SmartLocator/AdaptiveExec/UIAnalyzer/ScriptGen）
│   └── self_check.py                 # 环境自检脚本（7大类检查）
├── tests/
│   └── test_wrapper.py               # 85 项单元测试
└── references/
    ├── api_reference.md              # 全部 162 工具 API 参考（按 23 类分组）
    ├── usage_guide.md                # 使用指南与典型工作流示例
    ├── element_locators.md           # 元素定位策略与 40+ UIA 控件类型
    └── workflows.md                  # 100 条桌面 GUI 常用工作流（20 类 × 5 条）
```

## 快速开始

### 1. 环境要求

- Windows 10/11
- Python 3.10+
- 已安装依赖：`pywinauto`, `fastmcp`, `pywin32`, `comtypes`, `pydantic`

安装依赖：
```bash
pip install pywinauto fastmcp pywin32 comtypes pydantic
```

### 2. 启动 MCP 服务器

```bash
# Stdio 模式（默认，用于 Claude Desktop、Cursor、Continue 等 MCP 客户端）
python scripts/mcp_server.py

# HTTP 模式
python scripts/mcp_server.py --http --host 127.0.0.1 --port 10789

# 列出全部 128 个工具
python scripts/mcp_server.py --list-tools

# 调试模式（输出详细日志）
python scripts/mcp_server.py --debug
```

### 3. MCP 客户端配置

**Claude Desktop** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "pywinauto": {
      "command": "python",
      "args": ["<skill目录>/scripts/mcp_server.py"]
    }
  }
}
```

**Cursor / Continue**: 在 MCP 配置中添加相同的 command + args。

## 核心概念

### 会话管理

MCP 服务器维护两类会话 ID，在服务器运行期间持久化：

- **`app_id`**（格式 `app_xxxxxxxxxxxx`）：应用程序会话，由 `app_start` / `app_connect` 返回
- **`wrapper_id`**（格式 `ctrl_xxxxxxxxxxxx`）：窗口/控件包装器会话，由查找类工具返回

所有操作类工具都需要传入对应的 `app_id` 或 `wrapper_id`。使用 `list_sessions` 查看当前会话，`close_session` / `window_release` 释放资源。

### 后端选择

| 后端 | 适用场景 | 特点 |
|------|----------|------|
| `uia`（默认，推荐） | WPF、UWP、WinForms、Qt、现代应用 | 支持 control_type、auto_id、UIA 模式 |
| `win32` | 传统 Win32、MFC、VB6、旧版 Delphi | 基于窗口句柄和 Win32 API |

### 统一返回格式

所有工具返回：
```json
{
  "status": "success",
  "data": { ... }
}
```
错误时：
```json
{
  "status": "error",
  "error": "错误信息",
  "error_type": "异常类名",
  "category": "element_not_found",
  "suggestions": ["检查定位条件是否正确", "..."]
}
```

### v2.0 健壮性特性

| 特性 | 说明 |
|------|------|
| **输入校验** | 所有关键参数（backend、button、timeout、workflow_id等）在执行前校验，非法输入立即返回明确错误 |
| **重试机制** | `_with_retry` 指数退避重试，safe_click/safe_type_text 内置重试 |
| **超时保护** | `_with_timeout` 线程级超时，工作流步骤支持 `timeout` 参数 |
| **线程安全** | 会话管理使用 `RLock`，支持多线程并发调用 |
| **会话TTL** | 会话2小时无访问自动过期，`cleanup_stale_sessions` 手动清理 |
| **错误分类** | 自动识别 element_not_found/timeout/element_disabled/permission_denied 等6类错误，附带恢复建议 |
| **调用统计** | 记录每次工具调用的次数、错误率、耗时，`get_call_stats` 查询 |
| **健康检查** | `health_check` 一键检测9项依赖和运行状态 |

## v2.0 增强工具

### 健康与诊断

| 工具 | 说明 |
|------|------|
| `health_check()` | 全面健康检查（Python/pywinauto/pywin32/comtypes/fastmcp/平台/会话/统计/基础操作） |
| `get_capabilities()` | 返回服务器能力清单（版本、工具数、工作流数、支持的特性列表） |
| `get_call_stats(reset?)` | 获取工具调用统计（总调用数、错误数、错误率、每工具明细） |
| `classify_error(error_message)` | 对错误消息进行分类并给出恢复建议 |
| `cleanup_stale_sessions()` | 清理超过2小时未使用的过期会话 |

### 安全操作

| 工具 | 说明 |
|------|------|
| `safe_click(wrapper_id, button?, retries?, delay?, verify_visible?, verify_enabled?)` | 点击前验证可见/可用，失败自动重试（指数退避） |
| `safe_type_text(wrapper_id, text, clear_first?, retries?, delay?, use_clipboard?)` | 输入前验证焦点，长文本自动用剪贴板粘贴，失败重试 |

### 探查与快照

| 工具 | 说明 |
|------|------|
| `inspect_element(wrapper_id, depth?)` | 深度探查控件：全部属性、可用方法列表、子控件树、焦点/激活状态 |
| `snapshot_ui_state(wrapper_id?)` | 捕获UI状态快照（控件树、文本值、勾选状态、选中项），用于前后对比 |

### 批量与自定义工作流

| 工具 | 说明 |
|------|------|
| `batch_execute(operations_json, stop_on_error?, continue_on_error?)` | 顺序执行一批操作，支持 `$prev.field$` 引用上一步结果 |
| `workflow_execute_custom(steps_json, params_json?, name?, stop_on_error?)` | 执行自定义工作流，步骤支持条件分支、重试、超时、忽略错误 |
| `workflow_validate_steps(steps_json)` | 验证自定义工作流步骤定义的正确性 |

### 自定义工作流步骤 Schema

```json
{
  "tool": "function_name",
  "params": {"key": "$variable$"},
  "output_key": "result_var",
  "description": "步骤说明",
  "wait": 0.5,
  "condition": "$status$ == 'ready'",
  "retries": 3,
  "retry_delay": 0.5,
  "timeout": 10.0,
  "ignore_error": false
}
```

**条件表达式**支持：`$var$ == "value"`、`$var$ != "value"`、`$var$ > number`、`$var$ < number`、`$var$`（真值判断）、`not $var$`、`... and ...`、`... or ...`，支持点号路径如 `$health.status$`。

## v3.0 生成级能力

从"工具封装"提升到"智能生成与自适应编排"，核心是让用户用自然语言描述任务，系统自动生成、定位、执行、恢复。

### 1. NL2Workflow — 自然语言转工作流

| 工具 | 说明 |
|------|------|
| `generate_workflow(description, context_json?, auto_execute?)` | 根据自然语言描述生成可执行工作流步骤，附带推理过程和置信度 |
| `generate_and_execute(description, context_json?)` | 生成后立即执行 |

**工作原理**：分句解析 → 动作模板匹配（20+ 动作模式）→ 参数提取（正则+类型转换）→ 控件类型检测 → 自动补全（启动应用后自动获取主窗口，点击前自动查找目标控件）→ 步骤验证 → 置信度计算。

**示例**：
```
输入："启动记事本，输入Hello World，然后保存"
输出：4 步工作流
  1. app_start(cmd_line="notepad.exe") → app_id
  2. app_top_window(app_id) → wrapper_id  (自动补全)
  3. safe_type_text(wrapper_id, text="Hello World")
  4. keyboard_send_keys(keys="^s")
置信度：0.9，验证：通过
```

支持的动作类型：启动/连接/关闭应用、查找/聚焦/最大化/最小化窗口、截图、输入/清空文本、点击/双击/右键、快捷键（保存/复制/粘贴/全选）、菜单选择、等待等。

### 2. SmartLocator — 智能元素定位

| 工具 | 说明 |
|------|------|
| `smart_find(description, wrapper_id?, backend?, max_results?, search_depth?)` | 根据自然语言描述智能查找控件，按相关性排序返回 |

**定位策略**：
1. **控件类型检测**：从描述中识别 17 种控件类型（Button/Edit/ComboBox/CheckBox/Tab/Tree 等）
2. **关键词提取**：去掉控件类型词后提取搜索关键词
3. **自动遍历**：遍历控件树（深度可配），收集候选元素
4. **多维度评分**：控件类型匹配(0.4) + 标题模糊匹配(0.3×N) + auto_id 匹配(0.4) + 可见/可用加分(0.1)
5. **模糊匹配算法**：精确匹配(1.0) > 包含匹配(0.8+) > 首字母缩写(0.6) > 字符相似度(0.5)
6. **最佳匹配自动注册**：得分最高的元素自动注册为 wrapper 会话，可直接用于后续操作

**示例**：
```
smart_find("确定按钮", wrapper_id="ctrl_xxx")
→ 扫描 500+ 元素，返回 3 个匹配：
  1. 确定 (Button, score=0.85, 已注册为 ctrl_xxx)
  2. 确定并关闭 (Button, score=0.62)
  3. 取消 (Button, score=0.15)
```

### 3. AdaptiveExec — 自适应自愈执行

| 工具 | 说明 |
|------|------|
| `adaptive_execute(steps_json, max_retries_per_step?, auto_recover?, stop_on_error?, name?)` | 带自愈能力的工作流执行器，失败时自动分析错误并应用恢复策略 |

**6 类错误自动识别与恢复策略**：

| 错误类别 | 识别关键词 | 恢复策略 |
|----------|-----------|----------|
| `element_not_found` | not found / could not find | 扩大搜索范围 → 增加等待 → 切换后端 → 用 smart_find |
| `timeout` | timed out / timeout | 增加超时(×2) → 降低操作速度 → 检查 CPU |
| `element_disabled` | not enabled / disabled | 等待前置条件 → 检查依赖字段 |
| `element_not_visible` | not visible | 滚动到可见 → 展开父容器 → 切换标签页 |
| `permission_denied` | permission / access denied | 提示需要管理员权限 |
| `session_expired` | session not found | 重新连接 → 重新启动 |

**执行流程**：每步最多重试 N 次 → 失败时分类错误 → 按序应用恢复策略 → 策略应用后重试 → 全部失败则记录并停止（或继续）。返回完整的恢复日志，包含每步的错误、分类、应用的策略和结果。

### 4. UIAnalyzer — UI 理解与分析

| 工具 | 说明 |
|------|------|
| `analyze_ui(wrapper_id?, depth?, include_properties?)` | 分析界面结构，生成统计摘要和自然语言描述 |
| `describe_element(wrapper_id)` | 生成控件的自然语言描述（类型/文本/类名/状态/位置/支持操作） |
| `find_interactive_elements(wrapper_id?, control_type?, only_visible?, only_enabled?)` | 查找界面中所有可交互元素（17 种可交互类型过滤） |

**analyze_ui 输出**：
- 统计摘要：总元素数、可见数、可用数、可交互数、控件类型分布
- 可交互元素列表（前 50 个）：文本、类型、类名、auto_id、状态、位置、深度
- 自然语言描述：自动生成界面结构描述

**describe_element 输出**：
- 完整属性（15+ 字段）
- 自然语言描述："这是一个 Button 控件，显示文本为'确定'，窗口类名为 Button，当前状态：可见、可用，位置: (100, 200) 大小: 80x30，支持操作: click、double_click、right_click..."

### 5. ScenarioLib — 场景模板库

| 工具 | 说明 |
|------|------|
| `list_scenarios(category?)` | 列出所有可用场景模板 |
| `apply_scenario(scenario_id, params_json?, auto_execute?)` | 应用场景模板，参数填充后生成工作流步骤 |

**内置 10 个场景模板**：

| ID | 名称 | 类别 | 步骤数 |
|----|------|------|--------|
| `notepad_basic` | 记事本基础操作 | 文本编辑 | 4 |
| `calculator_math` | 计算器数学运算 | 系统工具 | 4 |
| `browser_navigate` | 浏览器导航 | 浏览器 | 6 |
| `form_fill` | 表单填写 | 表单操作 | 1+ |
| `dialog_confirm` | 对话框确认 | 对话框处理 | 3 |
| `screenshot_capture` | 窗口截图 | 截图捕获 | 3 |
| `menu_navigation` | 菜单导航 | 菜单操作 | 2 |
| `clipboard_operations` | 剪贴板操作 | 剪贴板 | 3 |
| `window_management` | 窗口管理 | 窗口管理 | 1+ |
| `system_info` | 系统信息收集 | 系统操作 | 4 |

每个场景定义了参数 schema（名称/类型/默认值/描述），应用时自动填充参数占位符并验证步骤。

### 6. ScriptGen — 脚本生成器

| 工具 | 说明 |
|------|------|
| `generate_script(steps_json?, workflow_id?, scenario_id?, script_name?, include_comments?)` | 将工作流步骤生成为独立可运行的 pywinauto Python 脚本 |

**生成的脚本特性**：
- 标准 Python 脚本结构（import + 函数 + main 入口）
- 每步附带注释（步骤序号+描述）
- 自动变量管理（app_id/wrapper_id 等会话变量自动传递）
- 支持 25+ 种工具的代码生成（app_start/connect/click/type_keys/menu_select/keyboard 等）
- 未支持的工具标记为 TODO 注释

**生成示例**（WF001 启动应用）：
```python
"""
Auto-generated pywinauto automation script
Generated by pywinauto-mcp generation engine v3.0
Script: wf001
Steps: 2
"""

import time
from pywinauto import Application, Desktop
from pywinauto.keyboard import send_keys


def wf001():
    """Execute the automation workflow."""
    # Step 1: 启动应用并等待主窗口
    app_id = Application(backend="uia").start("notepad.exe")
    time.sleep(1)

    # Step 2: 获取应用主窗口
    wrapper_id = app.top_window()
    time.sleep(0.5)

    print('Automation completed successfully')


if __name__ == "__main__":
    wf001()
```

## 标准工作流

### 工作流 A：启动应用 → 操作 → 关闭

```
1. app_start(cmd_line="notepad.exe", backend="uia")
   → { "status": "success", "data": { "app_id": "app_abc123", ... } }

2. app_top_window(app_id="app_abc123")
   → { "data": { "wrapper_id": "ctrl_def456", "text": "无标题 - 记事本", ... } }

3. control_type_keys(wrapper_id="ctrl_def456", keys="Hello, World!")

4. keyboard_send_keys(keys="^s")

5. app_kill(app_id="app_abc123")
```

### 工作流 B：连接已运行应用 → 查找控件 → 读取/操作

```
1. app_connect(backend="uia", title_re=".*Notepad.*")
   → { "data": { "app_id": "app_xyz789" } }

2. app_window(app_id="app_xyz789", control_type="Edit", found_index=0)
   → { "data": { "wrapper_id": "ctrl_aaa111" } }

3. control_get_text(wrapper_id="ctrl_aaa111")
   → { "data": { "text": "当前记事本内容" } }

4. control_set_text(wrapper_id="ctrl_aaa111", text="新的内容")
```

### 工作流 C：探查控件树 → 精确定位 → 操作

```
1. app_start(cmd_line="calc.exe")
2. app_top_window(app_id=...) → wrapper_id
3. window_dump_tree(wrapper_id=..., depth=3)
   → 输出控件树，查看按钮的 auto_id 和 control_type

4. control_child_window(wrapper_id=..., control_type="Button", auto_id="num7Button")
   → { "data": { "wrapper_id": "ctrl_bbb222" } }

5. control_click(wrapper_id="ctrl_bbb222")
```

## 105 条预置工作流

内置 100 条桌面 GUI 常用工作流，覆盖 20 个类别（每类 5 条），其中 35 条可通过 `workflow_execute` 一键执行，其余 65 条提供详细手动执行步骤指南。

### 工作流工具

| 工具 | 说明 |
|------|------|
| `workflow_list(category?, executable_only?)` | 列出全部工作流，可按类别筛选 |
| `workflow_get(workflow_id)` | 获取指定工作流的完整定义和步骤 |
| `workflow_execute(workflow_id, params?)` | 执行指定工作流，params 为输入参数字典 |

### 可执行工作流示例

```python
# 启动记事本并等待主窗口
workflow_execute("WF001", {"cmd_line": "notepad.exe", "backend": "uia", "timeout": 10})

# 安全输入文本到编辑框
workflow_execute("WF011", {"wrapper_id": "ctrl_xxx", "text": "Hello World", "found_index": 0})

# 安全点击按钮
workflow_execute("WF016", {"wrapper_id": "ctrl_xxx", "title": "确定", "found_index": 0})

# 浏览器导航到 URL
workflow_execute("WF061", {"browser_id": "ctrl_xxx", "url": "https://example.com"})

# 截取窗口截图
workflow_execute("WF071", {"wrapper_id": "ctrl_xxx", "save_path": "C:/screenshot.png"})
```

### 工作流类别（20 类 × 5 条 = 100 条）

| 类别 | 编号范围 | 可执行 |
|------|----------|--------|
| 应用生命周期 | WF001-WF005 | WF001, WF002, WF003 |
| 窗口管理 | WF006-WF010 | WF006, WF009 |
| 文本输入与编辑 | WF011-WF015 | WF011, WF012, WF015 |
| 按钮与控件交互 | WF016-WF020 | WF016, WF017 |
| 菜单与导航 | WF021-WF025 | WF021 |
| 列表与组合框 | WF026-WF030 | WF026, WF027 |
| 文件对话框操作 | WF031-WF035 | — |
| 对话框处理 | WF036-WF040 | WF036, WF037 |
| 键盘快捷键 | WF041-WF045 | WF041, WF042 |
| 鼠标操作 | WF046-WF050 | WF046, WF047, WF049 |
| 数据提取 | WF051-WF055 | WF051, WF054, WF055 |
| 验证与等待 | WF056-WF060 | WF056, WF057 |
| 浏览器自动化 | WF061-WF065 | WF061, WF062 |
| 系统操作 | WF066-WF070 | WF066, WF068 |
| 截图与捕获 | WF071-WF075 | WF071, WF073 |
| 表单填写 | WF076-WF080 | WF076, WF080 |
| 表格/网格操作 | WF081-WF085 | — |
| 树控件操作 | WF086-WF090 | — |
| 标签页操作 | WF091-WF095 | WF091, WF092 |
| 错误恢复与重试 | WF096-WF100 | — |

**完整工作流定义**：见 `references/workflows.md`（每条含用途、参数、详细执行步骤）

## 工具分类速查

| 分类 | 工具数量 | 代表工具 |
|------|----------|----------|
| 会话管理 | 3 | `list_sessions`, `close_session`, `close_all_sessions` |
| 应用管理 | 13 | `app_start`, `app_connect`, `app_kill`, `app_window`, `app_top_window` |
| 窗口查找与等待 | 7 | `window_find`, `window_exists`, `window_wait`, `window_dump_tree` |
| 控件鼠标操作 | 8 | `control_click`, `control_double_click`, `control_right_click`, `control_drag_mouse` |
| 控件键盘文本 | 5 | `control_type_keys`, `control_set_text`, `control_set_edit_text`, `control_get_text` |
| 控件状态选择 | 14 | `control_select`, `control_check`, `control_expand`, `control_invoke`, `control_set_value` |
| 窗口管理 | 7 | `control_close`, `control_maximize`, `control_minimize`, `control_move_window` |
| 菜单拖拽滚动 | 4 | `control_menu_select`, `control_drag_mouse`, `control_scroll`, `control_scroll_at_point` |
| 控件属性检查 | 15 | `control_get_properties`, `control_get_rectangle`, `control_is_visible`, `control_capture_as_image` |
| 控件树导航 | 3 | `control_child_window`, `control_children`, `control_descendants` |
| 特定控件 | 14 | `combobox_select`, `tab_select`, `tree_select`, `slider_set_position`, `progress_get_position` |
| 全局键盘 | 3 | `keyboard_send_keys`, `keyboard_key_press`, `keyboard_key_release` |
| 全局鼠标 | 9 | `mouse_click`, `mouse_move`, `mouse_drag`, `mouse_scroll`, `mouse_get_position` |
| 剪贴板 | 4 | `clipboard_get_data`, `clipboard_set_data`, `clipboard_empty`, `clipboard_get_formats` |
| 时序配置 | 5 | `timings_get`, `timings_set`, `timings_defaults`, `timings_slow`, `timings_fast` |
| 系统信息 | 4 | `sysinfo_is_x64_python`, `sysinfo_is_x64_os`, `sysinfo_os_arch`, `sysinfo_python_bitness` |
| 窗口元素查找 | 3 | `find_windows`, `find_elements`, `enumerate_windows` |
| 任务栏 | 5 | `taskbar_click_on_button`, `taskbar_get_start_button`, `taskbar_get_search_edit` |
| 桌面 | 3 | `desktop_windows`, `desktop_active_window`, `desktop_window` |
| 菜单 | 2 | `menu_get_items`, `menu_click_item` |
| 通用调用 | 2 | `control_call_method`, `control_get_attribute` |
| 健康与诊断 | 5 | `health_check`, `get_capabilities`, `get_call_stats`, `classify_error`, `cleanup_stale_sessions` |
| 安全操作 | 2 | `safe_click`, `safe_type_text`（内置重试+前置验证） |
| 探查与快照 | 2 | `inspect_element`, `snapshot_ui_state` |
| 批量执行 | 1 | `batch_execute`（支持 $prev.field$ 引用） |
| 工作流引擎 | 5 | `workflow_list`, `workflow_get`, `workflow_execute`, `workflow_execute_custom`, `workflow_validate_steps`（100 条预置 + 自定义） |
| NL2Workflow | 2 | `generate_workflow`, `generate_and_execute`（自然语言→工作流） |
| SmartLocator | 1 | `smart_find`（智能元素定位+模糊匹配+语义排序） |
| AdaptiveExec | 1 | `adaptive_execute`（自适应自愈执行+6类错误恢复） |
| UIAnalyzer | 3 | `analyze_ui`, `describe_element`, `find_interactive_elements`（UI理解与分析） |
| ScenarioLib | 2 | `list_scenarios`, `apply_scenario`（10个场景模板） |
| ScriptGen | 1 | `generate_script`（工作流→独立Python脚本） |

**总计：162 个工具**（143 基础+加固 + 10 生成级 + 9 系统操作）

**完整 API 参考**：见 `references/api_reference.md`

## 按键语法

`keyboard_send_keys` 和 `control_type_keys` 支持 pywinauto 按键语法：

| 语法 | 含义 | 示例 |
|------|------|------|
| `^` | Ctrl | `^a` = Ctrl+A, `^c` = Ctrl+C |
| `%` | Alt | `%{F4}` = Alt+F4, `%{TAB}` = Alt+Tab |
| `+` | Shift | `+{INS}` = Shift+Ins |
| `{KEY}` | 特殊键 | `{ENTER}`, `{TAB}`, `{ESC}`, `{F1}`..`{F24}`, `{LEFT}`, `{RIGHT}`, `{UP}`, `{DOWN}` |
| `{KEY down}` / `{KEY up}` | 按住/释放 | `{VK_SHIFT down}PYWINAUTO{VK_SHIFT up}` |
| `{^}` | 字面 `^` | `{^}a{^}c` 输入 "^a^c" |
| `{{}` / `{}}` | 字面 `{` / `}` | `{{}ENTER{}}` 输入 "{ENTER}" |

## 元素定位

支持的定位条件：`title`, `title_re`, `class_name`, `class_name_re`, `control_type`(UIA), `auto_id`(UIA), `control_id`(Win32), `handle`, `found_index`, `process`。

**定位优先级**：`auto_id` > `control_type`+`found_index` > `control_id` > `title`/`title_re` > `class_name` > `handle`

**详细定位指南**：见 `references/element_locators.md`

## 测试与自检

### 环境自检

运行自检脚本验证所有依赖和运行环境：

```bash
python scripts/self_check.py
```

自检覆盖 7 大类：Python 版本、平台、6 项依赖、Wrapper 模块、MCP 服务器、健康检查、基础操作（sysinfo/timings/clipboard/find_windows/workflows）。通过后生成 `self_check_report.json`。

### 单元测试

```bash
python tests/test_wrapper.py
```

85 项测试覆盖：版本与能力（3）、输入校验（10）、错误分类（6）、会话管理（4）、重试与超时（5）、工作流注册表（7）、条件评估（12）、工作流验证（4）、自定义工作流执行（5）、调用统计（2）、全函数注册（2）、生成级引擎（20：NL2Workflow 5 + SmartLocator 1 + 场景模板 4 + 脚本生成 3 + UIAnalyzer 2 + 模糊匹配 1 + 控件检测 1 + 恢复策略 1 + 工具注册 1 + 总数校验 1）。

## 使用参考文件

执行任务时按需读取以下参考文件：

### 项目文档
- **`README.md`** — 项目入口，特性概览，快速开始，工具分类，路线图
- **`CHANGELOG.md`** — 版本变更日志（v1.0 → v2.0 → v3.0 详细变更）
- **`CONTRIBUTING.md`** — 贡献指南，代码规范，测试要求，发布流程
- **`CODE_OF_CONDUCT.md`** — 行为准则
- **`LICENSE`** — MIT 开源许可证

### 详细文档 (docs/)
- **`docs/architecture.md`** — 架构设计文档（三层架构、数据流、会话状态机、扩展性设计、性能考量、安全设计）
- **`docs/getting_started.md`** — 快速开始指南（环境准备、安装、自检、MCP连接、第一个任务、生成级体验）
- **`docs/faq.md`** — 常见问题（安装、MCP服务器、应用窗口、控件定位、键盘鼠标、工作流、错误调试、性能优化、安全权限）

### 示例代码 (docs/examples/)
- **`docs/examples/basic_automation.py`** — 基础自动化示例（记事本/计算器/会话管理）
- **`docs/examples/nl2workflow_demo.py`** — 自然语言转工作流演示
- **`docs/examples/smart_locator_demo.py`** — 智能元素定位演示
- **`docs/examples/adaptive_exec_demo.py`** — 自适应自愈执行演示
- **`docs/examples/scenario_template_demo.py`** — 场景模板与脚本生成演示

### API 参考 (references/)
- **`references/api_reference.md`** — 需要查询某个工具的完整参数列表时
- **`references/usage_guide.md`** — 需要参考典型工作流、解决常见问题、了解最佳实践时
- **`references/element_locators.md`** — 需要定位控件、选择定位策略、查看控件类型时
- **`references/workflows.md`** — 需要查看 105 条预置工作流的详细步骤和参数时

### 源码与测试
- **`scripts/generation_engine.py`** — 需要查看生成级引擎实现（NL2Workflow/SmartLocator/AdaptiveExec/UIAnalyzer/ScriptGen）时
- **`scripts/self_check.py`** — 需要验证运行环境和依赖时
- **`tests/test_wrapper.py`** — 需要运行单元测试验证功能时
- **`scripts/pywinauto_wrapper.py`** — 需要查看底层实现或扩展功能时

## 注意事项

1. **仅支持 Windows**：pywinauto 是 Windows 专用库，无法在 Linux/macOS 上运行
2. **UAC 权限**：操作需要管理员权限的应用时，MCP 服务器也需要以管理员身份运行
3. **会话隔离**：`app_id` 和 `wrapper_id` 仅在当前 MCP 服务器进程内有效，服务器重启后失效；会话2小时无访问自动过期
4. **时序调整**：操作慢响应应用时，使用 `timings_set` 增加超时，或用 `window_wait` 显式等待；对不稳定操作使用 `safe_click`/`safe_type_text` 内置重试
5. **通用逃逸舱**：未显式封装的 API 可通过 `control_call_method(wrapper_id, method, arg1, arg2, arg3)` 调用
6. **安全提示**：本工具可模拟真实用户输入，操作前确认目标应用和控件正确，避免误操作
7. **错误恢复**：操作失败时，查看返回的 `category` 和 `suggestions` 字段获取自动分类和恢复建议；使用 `classify_error` 对任意错误消息进行诊断
8. **自定义工作流**：复杂场景优先使用 `workflow_execute_custom` 定义步骤序列，支持条件分支、重试、超时，比逐个调用工具更可靠
9. **自然语言自动化**：用 `generate_workflow` 从自然语言描述生成工作流，查看 `reasoning` 字段了解每步的推理依据和 `confidence` 置信度；低置信度时建议手动调整后再执行
10. **智能定位**：不确定控件精确属性时用 `smart_find` 自然语言描述查找，返回按相关性排序的候选列表，最佳匹配自动注册为 wrapper 会话
11. **自适应执行**：对不稳定的自动化场景用 `adaptive_execute`，内置 6 类错误的自动识别和恢复策略，比普通 `workflow_execute_custom` 更健壮
12. **脚本导出**：需要独立运行或分享自动化脚本时用 `generate_script` 导出为标准 pywinauto Python 脚本，支持从工作流ID、场景模板或自定义步骤生成
13. **场景模板**：常见操作优先用 `apply_scenario` 应用预置场景模板（记事本/计算器/浏览器/对话框等），参数化后直接生成可执行步骤
