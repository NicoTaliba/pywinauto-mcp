<div align="center">

# PyWinAuto MCP

**Windows GUI 自动化 · 生成级智能 · MCP 协议**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-3.0.0-orange.svg)](#)
[![Tools](https://img.shields.io/badge/MCP%20Tools-153-brightgreen.svg)](#)
[![Workflows](https://img.shields.io/badge/Workflows-100-blueviolet.svg)](#)
[![Tests](https://img.shields.io/badge/Tests-72-success.svg)](#)

基于 [pywinauto](https://github.com/pywinauto/pywinauto) 的 Windows GUI 自动化工具集，通过 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 暴露 153 个工具，内置 100 条工作流和 10 个场景模板，具备自然语言转工作流、智能元素定位、自适应自愈执行等生成级能力。

[快速开始](#快速开始) · [文档](#文档) · [示例](#示例) · [贡献](#贡献) · [许可证](#许可证)

</div>

---

## 特性

### 核心能力

- **162 个 MCP 工具** — 覆盖应用管理、窗口操作、控件交互、键盘鼠标、剪贴板、元素查找、时序控制、任务栏、桌面、菜单、特定控件等 23 个分类
- **105 条预置工作流** — 20 个类别 × 5 条，35 条可一键执行，覆盖应用生命周期、窗口管理、文本输入、按钮交互、菜单导航、列表组合框、文件对话框、对话框处理、键盘快捷键、鼠标操作、数据提取、验证等待、浏览器自动化、系统操作、截图捕获、表单填写、表格操作、树控件、标签页、错误恢复
- **10 个场景模板** — 记事本、计算器、浏览器、表单、对话框、截图、菜单、剪贴板、窗口管理、系统信息

### v3.0 生成级能力

- **NL2Workflow** — 自然语言描述 → 可执行工作流，附带推理过程和置信度
  ```
  输入："启动记事本，输入Hello World，然后保存"
  输出：4 步工作流（app_start → app_top_window → safe_type_text → keyboard_send_keys）
  ```
- **SmartLocator** — 智能元素定位，16 种控件类型自动检测，4 级模糊匹配，多维度语义排序
- **AdaptiveExec** — 自适应自愈执行，6 类错误自动识别，每类 2-4 种恢复策略，指数退避重试
- **UIAnalyzer** — UI 理解与分析，界面结构描述、可交互元素发现、控件自然语言描述
- **ScenarioLib** — 场景模板库，参数化模板一键生成工作流
- **ScriptGen** — 工作流 → 独立可运行 pywinauto Python 脚本生成

### v2.0 企业级加固

- **输入校验** — 10 类校验器（backend/button/timeout/workflow_id 等）
- **重试机制** — 指数退避重试，safe_click/safe_type_text 内置重试
- **超时保护** — 线程级超时，工作流步骤支持 timeout 参数
- **线程安全** — RLock 保护全部会话操作
- **会话 TTL** — 2 小时无访问自动过期，cleanup_stale_sessions 手动清理
- **错误分类** — 6 类错误自动识别 + 恢复建议
- **健康检查** — health_check 9 项依赖和运行状态检测
- **安全操作** — safe_click（验证可见/可用+重试）、safe_type_text（焦点验证+剪贴板优化）
- **批量执行** — batch_execute 支持 $prev.field$ 引用
- **状态快照** — snapshot_ui_state + inspect_element 深度探查

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / Windows 11 |
| Python | 3.10+ |
| 依赖 | pywinauto, fastmcp>=4.0, pywin32, comtypes, pydantic |
| 后端 | UIA（默认，推荐）/ Win32 |

## 快速开始

### 1. 安装依赖

```bash
pip install pywinauto fastmcp pywin32 comtypes pydantic
```

### 2. 环境自检

```bash
python scripts/self_check.py
```

### 3. 运行 MCP 服务器

```bash
# stdio 模式（默认，用于 MCP 客户端连接）
python scripts/mcp_server.py

# HTTP 模式
python scripts/mcp_server.py --http --host 127.0.0.1 --port 10789

# 列出全部工具
python scripts/mcp_server.py --list-tools
```

### 4. 运行测试

```bash
python tests/test_wrapper.py
```

### 5. 自然语言自动化（生成级）

```python
from scripts.generation_engine import generate_and_execute

# 用自然语言描述任务，自动生成工作流并执行
result = generate_and_execute("启动记事本，输入Hello World，然后保存")
print(result["status"])  # success
```

## 文档

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目入口（本文件） |
| [docs/getting_started.md](docs/getting_started.md) | 快速开始指南 |
| [docs/architecture.md](docs/architecture.md) | 架构设计文档 |
| [docs/faq.md](docs/faq.md) | 常见问题 |
| [references/api_reference.md](references/api_reference.md) | 153 工具完整 API 参考 |
| [references/workflows.md](references/workflows.md) | 100 条工作流详解 |
| [references/element_locators.md](references/element_locators.md) | 元素定位策略 |
| [references/usage_guide.md](references/usage_guide.md) | 使用指南与最佳实践 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更日志 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | 行为准则 |

## 示例

### 示例 1：基础自动化

```python
from scripts.pywinauto_wrapper import (
    app_start, app_top_window, control_type_keys, keyboard_send_keys
)

# 启动记事本
app = app_start("notepad.exe", backend="uia")
win = app_top_window(app["app_id"])

# 输入文本
control_type_keys(win["wrapper_id"], "Hello, PyWinAuto MCP!")

# 保存
keyboard_send_keys("^s")
```

### 示例 2：自然语言生成工作流

```python
from scripts.generation_engine import generate_workflow

# 自然语言描述 → 工作流步骤
result = generate_workflow("启动计算器，输入123+456，按等号")

print(f"生成 {result['step_count']} 步，置信度 {result['confidence']}")
for step in result["steps"]:
    print(f"  - {step['tool']}: {step.get('description', '')}")
```

### 示例 3：智能元素定位

```python
from scripts.generation_engine import smart_find

# 自然语言描述查找控件
result = smart_find("确定按钮", wrapper_id="ctrl_xxx")

print(f"找到 {result['matches_found']} 个匹配")
for match in result["matches"][:3]:
    print(f"  - {match['text']} ({match['control_type']}) score={match['score']}")

# 最佳匹配已自动注册为 wrapper 会话
print(f"最佳匹配 wrapper_id: {result['best_match_wrapper_id']}")
```

### 示例 4：自适应自愈执行

```python
import json
from scripts.generation_engine import adaptive_execute

steps = json.dumps([
    {"tool": "app_start", "params": {"cmd_line": "notepad.exe"}, "output_key": "app_id"},
    {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "wrapper_id"},
    {"tool": "safe_type_text", "params": {"wrapper_id": "$wrapper_id$", "text": "Hello"}},
])

# 自动处理元素未找到、超时等错误
result = adaptive_execute(steps, auto_recover=True, max_retries_per_step=3)
print(f"状态: {result['status']}, 恢复次数: {result['total_recoveries']}")
```

### 示例 5：场景模板

```python
from scripts.generation_engine import apply_scenario

# 应用预置场景模板
result = apply_scenario("notepad_basic", params={"text": "Hello from scenario"})
print(f"场景: {result['scenario_name']}, 步骤: {result['step_count']}")
```

更多示例见 [docs/examples/](docs/examples/)。

## 工具分类

| 分类 | 数量 | 代表工具 |
|------|------|----------|
| 应用管理 | 13 | `app_start`, `app_connect`, `app_kill`, `app_top_window` |
| 控件操作 | 55+ | `control_click`, `control_set_focus`, `control_get_text`, `safe_click` |
| 键盘鼠标 | 12 | `keyboard_send_keys`, `mouse_click`, `mouse_drag`, `mouse_scroll` |
| 窗口查找 | 7 | `window_find`, `window_exists`, `window_wait`, `window_dump_tree` |
| 剪贴板 | 4 | `clipboard_get_data`, `clipboard_set_data`, `clipboard_empty` |
| 时序控制 | 5 | `timings_get`, `timings_set`, `timings_slow`, `timings_fast` |
| 系统信息 | 4 | `sysinfo_is_x64_python`, `sysinfo_os_arch` |
| 元素查找 | 3 | `find_windows`, `find_elements`, `enumerate_windows` |
| 任务栏/桌面 | 8 | `taskbar_click_on_button`, `desktop_windows`, `desktop_active_window` |
| 特定控件 | 14 | `combobox_select`, `tab_select`, `tree_select`, `slider_set_position` |
| 健康诊断 | 5 | `health_check`, `get_capabilities`, `get_call_stats`, `classify_error` |
| 生成级 | 10 | `generate_workflow`, `smart_find`, `adaptive_execute`, `generate_script` |
| 工作流 | 5 | `workflow_list`, `workflow_execute`, `workflow_execute_custom` |
| **总计** | **153** | |

## 项目结构

```
pywinauto-mcp/
├── README.md                    # 项目入口文档
├── CHANGELOG.md                 # 变更日志
├── CONTRIBUTING.md              # 贡献指南
├── CODE_OF_CONDUCT.md           # 行为准则
├── LICENSE                      # MIT 许可证
├── SKILL.md                     # MCP Skill 定义文档
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md       # Bug 报告模板
│   │   └── feature_request.md  # 功能请求模板
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── architecture.md          # 架构设计文档
│   ├── getting_started.md       # 快速开始指南
│   ├── faq.md                   # 常见问题
│   └── examples/
│       ├── basic_automation.py
│       ├── nl2workflow_demo.py
│       ├── smart_locator_demo.py
│       ├── adaptive_exec_demo.py
│       └── scenario_template_demo.py
├── scripts/
│   ├── mcp_server.py            # MCP CLI 服务器（stdio/HTTP）
│   ├── pywinauto_wrapper.py     # 143 API 封装 + 100 工作流引擎
│   ├── generation_engine.py     # v3.0 生成级引擎
│   └── self_check.py            # 环境自检脚本
├── tests/
│   └── test_wrapper.py          # 85 项单元测试
└── references/
    ├── api_reference.md         # 153 工具 API 参考
    ├── workflows.md             # 100 条工作流详解
    ├── element_locators.md      # 元素定位策略
    └── usage_guide.md           # 使用指南
```

## 路线图

- [x] v1.0 — 128 API 封装 + MCP 服务器
- [x] v2.0 — 企业级加固（校验/重试/超时/线程安全/健康检查）
- [x] v3.0 — 生成级能力（NL2Workflow/SmartLocator/AdaptiveExec/UIAnalyzer/ScriptGen）
- [ ] v3.1 — 更多场景模板（Excel/Word/Outlook 等 Office 自动化）
- [ ] v3.2 — 操作录制与回放（Record & Replay）
- [ ] v4.0 — 视觉定位（基于截图的图像匹配定位）
- [ ] v4.1 — 多显示器支持 + DPI 感知
- [ ] v4.2 — 远程桌面自动化

## 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献流程。

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/your-org/pywinauto-mcp.git
cd pywinauto-mcp

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
python tests/test_wrapper.py

# 运行自检
python scripts/self_check.py
```

### 提交规范

本项目使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具链相关

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 致谢

- [pywinauto](https://github.com/pywinauto/pywinauto) — Windows GUI 自动化基础库
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP 服务器框架
- [pywinauto-mcp (参考项目)](https://github.com/wenyubo2008/pywinauto-mcp) — 架构参考

---

<div align="center">

如果这个项目对你有帮助，请给个 ⭐ Star

**Made with ❤️ for Windows Automation**

</div>
