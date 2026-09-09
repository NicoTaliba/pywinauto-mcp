# 快速开始指南

本指南将帮助你在 5 分钟内开始使用 PyWinAuto MCP。

## 目录

- [1. 环境准备](#1-环境准备)
- [2. 安装依赖](#2-安装依赖)
- [3. 环境自检](#3-环境自检)
- [4. 运行 MCP 服务器](#4-运行-mcp-服务器)
- [5. 连接 MCP 客户端](#5-连接-mcp-客户端)
- [6. 第一个自动化任务](#6-第一个自动化任务)
- [7. 生成级能力体验](#7-生成级能力体验)
- [8. 运行测试](#8-运行测试)
- [9. 常见问题排查](#9-常见问题排查)

---

## 1. 环境准备

### 系统要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10 | Windows 11 |
| Python | 3.10 | 3.11+ |
| 内存 | 2GB | 4GB+ |
| 磁盘 | 100MB | 500MB+ |

### 检查 Python 版本

```bash
python --version
# Python 3.11.9
```

如果 Python 版本低于 3.10，请先升级 Python。

---

## 2. 安装依赖

### 方式一：pip 安装（推荐）

```bash
pip install pywinauto fastmcp pywin32 comtypes pydantic
```

### 方式二：requirements 文件

```bash
pip install -r requirements.txt
```

### 验证安装

```bash
python -c "import pywinauto; import fastmcp; print('All dependencies installed')"
# All dependencies installed
```

---

## 3. 环境自检

运行自检脚本，验证所有依赖和运行环境：

```bash
python scripts/self_check.py
```

预期输出：

```
======================================================================
  PyWinAuto MCP — Environment Self-Check
======================================================================

[1/7] Python Version
  Version: 3.11.9 (required: >= 3.10)
  Status: OK

[2/7] Platform
  System: Windows 10 (AMD64)
  Status: OK

[3/7] Dependencies
  pywinauto       OK       v0.6.9
  fastmcp         OK       v4.0.3
  pywin32         OK
  comtypes        OK       v1.4.16
  pydantic        OK       v2.13.4
  six             OK       v1.17.0

[4/7] Wrapper Module
  Version: 2.0.0
  Functions: 143
  Workflows: 100 (35 executable)
  Status: OK

[5/7] MCP Server Module
  Tool registry: 153 tools
  Status: OK

[6/7] Health Check
  Overall: healthy
  All OK: True

[7/7] Basic Operations
  sysinfo              OK
  timings              OK
  clipboard            OK
  find_windows         OK
  workflows            OK

======================================================================
  RESULT: ALL CHECKS PASSED
======================================================================
```

如果有任何检查失败，请根据提示修复后再继续。

---

## 4. 运行 MCP 服务器

### 方式一：stdio 模式（默认，推荐用于本地 MCP 客户端）

```bash
python scripts/mcp_server.py
```

服务器启动后会等待 MCP 客户端通过标准输入输出连接。

### 方式二：HTTP 模式（用于远程访问或调试）

```bash
python scripts/mcp_server.py --http --host 127.0.0.1 --port 10789
```

服务器将在 `http://127.0.0.1:10789/mcp` 提供 HTTP Streamable MCP 服务。

### 列出全部工具

```bash
python scripts/mcp_server.py --list-tools
```

预期输出：

```
Registered 153/153 tools
  - app_start
  - app_connect
  - app_kill
  - ...
  - generate_workflow
  - smart_find
  - adaptive_execute
  - generate_script

Total: 153 tools
```

### 调试模式

```bash
python scripts/mcp_server.py --debug
```

---

## 5. 连接 MCP 客户端

### Claude Desktop

编辑 `%APPDATA%\Claude\claude_desktop_config.json`：

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

重启 Claude Desktop 后即可使用。

### Cursor

在 Cursor 设置中添加 MCP 服务器：

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

### 其他 MCP 客户端

任何支持 MCP 协议的客户端都可以通过 stdio 或 HTTP 连接本服务器。

---

## 6. 第一个自动化任务

### 任务：启动记事本，输入文本，保存

#### 方式一：使用 MCP 工具（通过 AI 客户端）

告诉 AI 客户端：

> "帮我启动记事本，输入 'Hello, PyWinAuto MCP!'，然后保存文件"

AI 客户端会自动调用以下工具序列：

1. `app_start(cmd_line="notepad.exe", backend="uia")` → 获取 app_id
2. `app_top_window(app_id=...)` → 获取 wrapper_id
3. `control_child_window(wrapper_id=..., control_type="Document")` → 获取编辑区
4. `control_type_keys(wrapper_id=..., keys="Hello, PyWinAuto MCP!")` → 输入文本
5. `keyboard_send_keys(keys="^s")` → 保存

#### 方式二：使用 Python API（直接调用）

创建 `first_task.py`：

```python
import sys
sys.path.insert(0, "scripts")
from pywinauto_wrapper import (
    app_start, app_top_window, control_child_window,
    control_type_keys, keyboard_send_keys
)

# 1. 启动记事本
app = app_start("notepad.exe", backend="uia")
print(f"启动成功: app_id={app['app_id']}")

# 2. 获取主窗口
win = app_top_window(app["app_id"])
print(f"窗口: {win.get('text', 'unknown')}")

# 3. 定位编辑区
edit = control_child_window(win["wrapper_id"], control_type="Document")
print(f"编辑区: wrapper_id={edit['wrapper_id']}")

# 4. 输入文本
control_type_keys(edit["wrapper_id"], "Hello, PyWinAuto MCP!")
print("文本输入完成")

# 5. 保存（Ctrl+S）
keyboard_send_keys("^s")
print("保存对话框已打开")

print("任务完成！")
```

运行：

```bash
python first_task.py
```

---

## 7. 生成级能力体验

### 7.1 自然语言转工作流

```python
import sys
sys.path.insert(0, "scripts")
from generation_engine import generate_workflow

# 用自然语言描述任务
result = generate_workflow("启动计算器，输入123+456，按等号")

print(f"生成 {result['step_count']} 步工作流")
print(f"置信度: {result['confidence']}")
print(f"验证通过: {result['validation']['valid']}")
print()
print("推理过程:")
for r in result["reasoning"]:
    print(f"  - {r.get('sentence', '')}: {r.get('action', '')} -> {r.get('tool', '-')}")
print()
print("工作流步骤:")
for i, step in enumerate(result["steps"], 1):
    print(f"  {i}. {step['tool']}: {step.get('description', '')}")
```

### 7.2 智能元素定位

```python
from generation_engine import smart_find

# 自然语言描述查找控件
result = smart_find("确定按钮", wrapper_id="ctrl_xxx")

print(f"找到 {result['matches_found']} 个匹配")
for match in result["matches"][:3]:
    print(f"  - {match['text']} ({match['control_type']}) score={match['score']}")

# 最佳匹配已自动注册为 wrapper 会话
print(f"最佳匹配 wrapper_id: {result['best_match_wrapper_id']}")
```

### 7.3 自适应自愈执行

```python
import json
from generation_engine import adaptive_execute

steps = json.dumps([
    {"tool": "app_start", "params": {"cmd_line": "notepad.exe"}, "output_key": "app_id"},
    {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "wrapper_id"},
    {"tool": "safe_type_text", "params": {"wrapper_id": "$wrapper_id$", "text": "Hello"}},
])

# 自动处理元素未找到、超时等错误
result = adaptive_execute(steps, auto_recover=True, max_retries_per_step=3)

print(f"状态: {result['status']}")
print(f"成功: {result['succeeded']}, 失败: {result['errors']}")
print(f"自动恢复次数: {result['total_recoveries']}")
if result["recovery_log"]:
    print("恢复日志:")
    for log in result["recovery_log"]:
        print(f"  - 步骤{log['step']}: {log['error_category']} -> {log['strategy']}")
```

### 7.4 场景模板

```python
from generation_engine import apply_scenario, list_scenarios

# 列出所有场景
scenarios = list_scenarios()
print(f"可用场景: {scenarios['count']} 个")
for s in scenarios["scenarios"]:
    print(f"  - {s['id']}: {s['name']} ({s['step_count']} 步)")

# 应用场景
result = apply_scenario("notepad_basic", params={"text": "Hello from scenario"})
print(f"场景: {result['scenario_name']}")
print(f"步骤: {result['step_count']}")
print(f"验证: {result['validation']['valid']}")
```

### 7.5 脚本生成

```python
from generation_engine import generate_script

# 从工作流生成独立脚本
result = generate_script(workflow_id="WF001", script_name="start_notepad")

print(f"生成 {result['lines_of_code']} 行代码")
print()
print(result["script"])

# 保存到文件
with open("start_notepad.py", "w", encoding="utf-8") as f:
    f.write(result["script"])
print("\n脚本已保存到 start_notepad.py")
```

---

## 8. 运行测试

### 运行全部测试

```bash
python tests/test_wrapper.py
```

### 运行特定测试类

```bash
python -m pytest tests/test_wrapper.py::TestGenerationEngine -v
```

### 运行特定测试方法

```bash
python -m pytest tests/test_wrapper.py::TestGenerationEngine::test_generate_workflow_basic -v
```

预期输出：

```
Ran 72 tests in 3.099s
OK
```

---

## 9. 常见问题排查

### Q: 提示 "No module named 'pywinauto'"

**A**: 安装依赖：
```bash
pip install pywinauto
```

### Q: 提示 "No module named 'fastmcp'"

**A**: 安装 FastMCP：
```bash
pip install fastmcp
```

### Q: 操作需要管理员权限的应用时失败

**A**: 以管理员身份运行 MCP 服务器：
1. 右键点击命令提示符
2. 选择"以管理员身份运行"
3. 重新运行 `python scripts/mcp_server.py`

### Q: 找不到控件 / 元素未找到

**A**:
1. 使用 `window_dump_tree(wrapper_id)` 查看控件树结构
2. 使用 `smart_find(description)` 智能定位
3. 增加超时时间：`window_wait(wrapper_id, timeout=10)`
4. 确认使用了正确的后端（uia/win32）

### Q: 操作慢响应应用时超时

**A**:
1. 使用 `timings_slow()` 降低操作速度
2. 使用 `timings_set(window_find_timeout=30)` 增加超时
3. 使用 `adaptive_execute()` 自适应执行（自动重试）

### Q: MCP 客户端连接不上服务器

**A**:
1. 确认服务器正在运行
2. 检查 stdio 模式下的命令路径是否正确
3. HTTP 模式下检查端口是否被占用：`netstat -ano | findstr 10789`
4. 查看服务器日志获取详细错误

### Q: 中文输入乱码

**A**:
1. 使用 `safe_type_text()` 代替 `control_type_keys()`（自动使用剪贴板）
2. 确保文件编码为 UTF-8
3. 确认系统区域设置支持中文

### Q: 高 DPI 显示器上坐标不对

**A**:
1. 在程序清单中声明 DPI 感知（Python 可使用 `ctypes.windll.shcore.SetProcessDpiAwareness(1)`）
2. 使用控件级操作（`control_click`）代替屏幕坐标操作（`mouse_click`）

---

## 下一步

- 阅读 [架构设计文档](architecture.md) 了解系统设计
- 查看 [API 参考](../references/api_reference.md) 了解全部 153 个工具
- 浏览 [100 条工作流](../references/workflows.md) 获取现成的自动化方案
- 阅读 [常见问题](faq.md) 获取更多帮助
- 查看 [示例代码](examples/) 学习更多用法
- 阅读 [贡献指南](../CONTRIBUTING.md) 参与项目开发
