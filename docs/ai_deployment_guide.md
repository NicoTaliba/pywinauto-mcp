# AI 自动部署指南

> 本文档面向 AI 编程助手（Cursor、Claude Code、Copilot、Continue 等），提供 pywinauto-mcp 的自动部署流程。AI 可直接按照本文档步骤执行部署，无需人工干预。

---

## 目录

- [部署概述](#部署概述)
- [通用部署流程（所有工具通用）](#通用部署流程)
- [Cursor 部署指南](#cursor-部署指南)
- [Claude Code 部署指南](#claude-code-部署指南)
- [VS Code + GitHub Copilot 部署指南](#vs-code--github-copilot-部署指南)
- [JetBrains AI Assistant 部署指南](#jetbrains-ai-assistant-部署指南)
- [Continue.dev 部署指南](#continuedev-部署指南)
- [通用 MCP 客户端配置](#通用-mcp-客户端配置)
- [部署验证清单](#部署验证清单)
- [故障排查](#故障排查)
- [AI 执行注意事项](#ai-执行注意事项)

---

## 部署概述

### 目标

将 pywinauto-mcp 部署为 MCP 服务器，使 AI 编程助手能够通过 MCP 协议调用 162 个 Windows GUI 自动化工具。

### 前置条件

| 项目 | 要求 | 检查命令 |
|------|------|----------|
| 操作系统 | Windows 10/11 | `ver` |
| Python | >= 3.10 | `python --version` |
| pip | 最新版 | `pip --version` |
| 网络 | 可访问 PyPI | `pip install --dry-run pywinauto` |
| 权限 | 普通用户（管理员权限可选） | `whoami` |

### 部署产物

部署完成后应具备：
1. Python 虚拟环境（推荐）或全局依赖安装
2. pywinauto-mcp 代码仓库（克隆或本地路径）
3. MCP 服务器可启动验证通过
4. AI 工具的 MCP 配置已更新
5. 工具调用测试通过

---

## 通用部署流程

> 以下流程适用于所有 AI 编程工具，AI 应按顺序执行。

### 步骤 1：环境检查

```bash
# 检查 Python 版本（需要 >= 3.10）
python --version

# 检查 pip
pip --version

# 检查操作系统（必须是 Windows）
ver
```

**AI 判断逻辑**：
- 如果 Python < 3.10 → 提示用户升级 Python，停止部署
- 如果不是 Windows → 提示不支持，停止部署
- 如果 pip 不可用 → 安装 pip：`python -m ensurepip --upgrade`

### 步骤 2：获取代码

**方式 A：克隆 GitHub 仓库（推荐）**

```bash
git clone https://github.com/walkzzz/pywinauto-mcp.git
cd pywinauto-mcp
```

**方式 B：使用本地已有代码**

如果代码已在本地，直接进入项目目录：
```bash
cd <pywinauto-mcp 项目路径>
```

**AI 判断逻辑**：
- 如果 git 不可用 → 下载 ZIP 并解压，或提示用户安装 git
- 如果目录已存在 → 进入目录，执行 `git pull` 更新

### 步骤 3：创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 验证 Python 路径
where python
```

**AI 判断逻辑**：
- 如果用户明确要求全局安装 → 跳过虚拟环境
- 如果虚拟环境已存在 → 直接激活
- 激活失败 → 检查执行策略：`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 步骤 4：安装依赖

```bash
# 安装核心依赖
pip install pywinauto fastmcp pywin32 comtypes pydantic six

# 或使用 requirements.txt
pip install -r requirements.txt
```

**AI 判断逻辑**：
- 如果安装失败 → 尝试升级 pip：`python -m pip install --upgrade pip`
- 如果 pywin32 安装后导入失败 → 运行：`python Scripts\pywin32_postinstall.py -install`
- 如果网络超时 → 使用国内镜像：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pywinauto fastmcp`

### 步骤 5：环境自检

```bash
# 运行自检脚本
python scripts/self_check.py
```

**预期输出**：所有检查项显示 `OK`，最终显示 `ALL CHECKS PASSED`。

**AI 判断逻辑**：
- 如果有检查失败 → 根据失败项修复后重新运行
- 常见失败：依赖未安装 → 回到步骤 4；Python 版本过低 → 提示升级

### 步骤 6：验证 MCP 服务器

```bash
# 列出所有工具（验证服务器可启动且工具注册正常）
python scripts/mcp_server.py --list-tools
```

**预期输出**：
```
Registered 162/162 tools
Total: 162 tools
```

**AI 判断逻辑**：
- 如果工具数 < 162 → 检查是否有导入错误，查看完整输出
- 如果服务器启动失败 → 查看错误信息，常见原因：依赖缺失、端口占用

### 步骤 7：配置 AI 工具的 MCP 连接

根据使用的 AI 工具，选择下方对应的配置方式。

### 步骤 8：验证工具调用

在 AI 工具中发送测试指令：
> "列出 pywinauto-mcp 的所有可用工具"
> 或
> "使用 pywinauto-mcp 检查系统信息"

AI 应能调用 `health_check` 或 `get_capabilities` 工具并返回结果。

---

## Cursor 部署指南

### 工具特点

- AI 原生 IDE，内置 MCP 支持
- 支持全局 MCP 配置和项目级 MCP 配置
- 配置文件位置：`%APPDATA%\Cursor\User\mcp.json`（全局）或 `.cursor/mcp.json`（项目级）

### 部署步骤

#### 1. 完成通用部署流程（步骤 1-6）

#### 2. 配置 MCP 服务器

**方式 A：项目级配置（推荐，随项目共享）**

在项目根目录创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "pywinauto": {
      "command": "python",
      "args": [
        "${workspaceFolder}\\scripts\\mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "${workspaceFolder}\\scripts"
      }
    }
  }
}
```

**方式 B：全局配置（所有项目可用）**

编辑 `%APPDATA%\Cursor\User\mcp.json`：

```json
{
  "mcpServers": {
    "pywinauto": {
      "command": "python",
      "args": [
        "C:\\path\\to\\pywinauto-mcp\\scripts\\mcp_server.py"
      ]
    }
  }
}
```

#### 3. 使用虚拟环境（可选但推荐）

如果使用了虚拟环境，将 `command` 改为虚拟环境的 Python：

```json
{
  "mcpServers": {
    "pywinauto": {
      "command": "C:\\path\\to\\pywinauto-mcp\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\pywinauto-mcp\\scripts\\mcp_server.py"]
    }
  }
}
```

#### 4. 重启 Cursor

配置修改后需要重启 Cursor 或重新加载窗口：
- 按 `Ctrl+Shift+P`
- 输入 `Reload Window`
- 回车执行

#### 5. 验证

在 Cursor 的 AI 对话中输入：
> "你能调用 pywinauto 的哪些工具？"

AI 应能列出工具或调用 `get_capabilities`。

### Cursor 特定提示

- Cursor 的 MCP 配置支持 `${workspaceFolder}` 变量，推荐项目级配置
- 如果 MCP 服务器启动失败，在 Cursor 设置中查看 MCP 日志
- 支持 HTTP 模式：将 `command`/`args` 替换为 `url` 字段

---

## Claude Code 部署指南

### 工具特点

- Anthropic 官方 CLI 工具
- 支持 MCP 配置文件：`%APPDATA%\Claude\claude_desktop_config.json`（桌面版）或 CLI 配置
- CLI 版本支持 `--mcp-config` 参数

### 部署步骤

#### 1. 完成通用部署流程（步骤 1-6）

#### 2. 配置 MCP 服务器

**Claude Desktop 配置**

编辑 `%APPDATA%\Claude\claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "pywinauto": {
      "command": "python",
      "args": ["C:\\path\\to\\pywinauto-mcp\\scripts\\mcp_server.py"]
    }
  }
}
```

**Claude Code CLI 配置**

创建配置文件 `~/.claude.json` 或使用命令行参数：

```bash
# 方式 1：使用配置文件
claude --mcp-config mcp_config.json

# mcp_config.json 内容
{
  "mcpServers": {
    "pywinauto": {
      "command": "python",
      "args": ["C:\\path\\to\\pywinauto-mcp\\scripts\\mcp_server.py"]
    }
  }
}
```

#### 3. 重启 Claude

- Desktop 版：完全退出并重新打开
- CLI 版：退出后重新启动

#### 4. 验证

在 Claude 对话中输入：
> "列出 pywinauto-mcp 的工具"

或检查 MCP 状态：
```bash
claude mcp list
```

### Claude Code 特定提示

- Claude Code 支持在对话中动态添加 MCP 服务器：`/mcp add pywinauto python C:\path\to\mcp_server.py`
- 使用 `claude mcp list` 查看已连接的 MCP 服务器
- 使用 `claude mcp remove pywinauto` 移除服务器

---

## VS Code + GitHub Copilot 部署指南

### 工具特点

- GitHub Copilot 支持 MCP（预览版）
- 通过 VS Code 设置配置 MCP 服务器
- 配置位置：VS Code 设置 → MCP

### 部署步骤

#### 1. 完成通用部署流程（步骤 1-6）

#### 2. 安装 Copilot MCP 支持

确保 VS Code 版本 >= 1.90，GitHub Copilot 扩展已启用 MCP 功能。

#### 3. 配置 MCP 服务器

**方式 A：通过 VS Code 设置 UI**

1. 打开设置（`Ctrl+,`）
2. 搜索 `MCP`
3. 找到 `Copilot > Mcp: Servers`
4. 点击 `Edit in settings.json`

**方式 B：直接编辑 settings.json**

```json
{
  "copilot.mcp.servers": [
    {
      "name": "pywinauto",
      "command": "python",
      "args": ["C:\\path\\to\\pywinauto-mcp\\scripts\\mcp_server.py"]
    }
  ]
}
```

#### 4. 重启 VS Code

#### 5. 验证

在 Copilot Chat 中输入：
> "使用 pywinauto MCP 工具检查系统信息"

### VS Code 特定提示

- Copilot 的 MCP 支持仍在快速迭代，确保扩展为最新版
- 部分版本需要在设置中手动启用 MCP 预览功能
- 支持通过 `mcp.json` 文件配置（项目根目录）

---

## JetBrains AI Assistant 部署指南

### 工具特点

- JetBrains IDE（PyCharm、IntelliJ 等）的 AI 助手
- 支持 MCP 服务器配置（2024.2+ 版本）
- 配置位置：Settings → Tools → AI Assistant → MCP Servers

### 部署步骤

#### 1. 完成通用部署流程（步骤 1-6）

#### 2. 配置 MCP 服务器

1. 打开 Settings（`Ctrl+Alt+S`）
2. 导航到 Tools → AI Assistant → MCP Servers
3. 点击 `+` 添加新服务器
4. 填写配置：

```
Name: pywinauto
Type: Stdio
Command: python
Arguments: C:\path\to\pywinauto-mcp\scripts\mcp_server.py
```

5. 点击 OK 保存

#### 3. 启用服务器

在 MCP Servers 列表中，确保 `pywinauto` 服务器已启用（复选框勾选）。

#### 4. 验证

在 AI Assistant 对话中输入：
> "调用 pywinauto 的 health_check 工具"

### JetBrains 特定提示

- 确保 IDE 版本 >= 2024.2，旧版本不支持 MCP
- 服务器配置支持环境变量设置
- 可以在项目级和全局级分别配置

---

## Continue.dev 部署指南

### 工具特点

- 开源 AI 编程助手，支持 VS Code 和 JetBrains
- 高度可定制，支持多种 MCP 配置方式
- 配置文件：`~/.continue/config.json`

### 部署步骤

#### 1. 完成通用部署流程（步骤 1-6）

#### 2. 安装 Continue 扩展

- VS Code：在扩展市场搜索 "Continue"
- JetBrains：在插件市场搜索 "Continue"

#### 3. 配置 MCP 服务器

编辑 `~/.continue/config.json`：

```json
{
  "models": [...],
  "mcpServers": {
    "pywinauto": {
      "command": "python",
      "args": ["C:\\path\\to\\pywinauto-mcp\\scripts\\mcp_server.py"]
    }
  }
}
```

#### 4. 重载 Continue

- 按 `Ctrl+Shift+P`
- 输入 `Continue: Reload`
- 回车执行

#### 5. 验证

在 Continue 对话中输入：
> "列出 pywinauto MCP 的工具"

或使用 Continue 的 MCP 检查功能。

### Continue 特定提示

- Continue 支持在 `config.json` 中配置多个 MCP 服务器
- 支持通过 URL 连接远程 MCP 服务器
- 可以使用 `continue mcp list` 命令查看已连接的服务器

---

## 通用 MCP 客户端配置

### 标准 MCP 配置格式

所有兼容 MCP 协议的客户端都使用以下 JSON 格式：

```json
{
  "mcpServers": {
    "pywinauto": {
      "command": "python",
      "args": ["C:\\path\\to\\pywinauto-mcp\\scripts\\mcp_server.py"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### HTTP 模式配置

如果需要远程访问或多客户端共享，使用 HTTP 模式：

```json
{
  "mcpServers": {
    "pywinauto": {
      "url": "http://127.0.0.1:10789/mcp"
    }
  }
}
```

启动 HTTP 服务器：
```bash
python scripts/mcp_server.py --http --host 127.0.0.1 --port 10789
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MCP_TRANSPORT` | `stdio` | 传输模式：`stdio` 或 `http` |
| `MCP_HOST` | `127.0.0.1` | HTTP 绑定地址 |
| `MCP_PORT` | `10789` | HTTP 端口 |
| `MCP_PATH` | `/mcp` | HTTP 端点路径 |

---

## 部署验证清单

AI 部署完成后，应逐项验证：

### 基础验证

- [ ] Python 版本 >= 3.10
- [ ] 所有依赖安装成功（pywinauto, fastmcp, pywin32, comtypes, pydantic）
- [ ] `python scripts/self_check.py` 全部通过
- [ ] `python scripts/mcp_server.py --list-tools` 显示 162 个工具

### MCP 连接验证

- [ ] AI 工具的 MCP 配置已保存
- [ ] AI 工具已重启/重载
- [ ] MCP 服务器状态显示为已连接
- [ ] AI 能识别到 pywinauto 工具

### 功能验证

- [ ] AI 能调用 `health_check` 并返回健康状态
- [ ] AI 能调用 `get_capabilities` 并返回工具列表
- [ ] AI 能调用 `sysinfo_os_arch` 返回系统架构
- [ ] AI 能调用 `workflow_list` 返回工作流列表

### 进阶验证（可选）

- [ ] AI 能调用 `generate_workflow` 生成工作流
- [ ] AI 能调用 `system_file_exists` 检查文件
- [ ] AI 能调用 `system_get_installed_software` 获取软件列表

---

## 故障排查

### 问题：MCP 服务器启动失败

**症状**：AI 工具显示 MCP 连接失败，或工具列表为空。

**排查步骤**：
1. 手动运行服务器查看错误：
   ```bash
   python scripts/mcp_server.py --list-tools
   ```
2. 检查 Python 路径是否正确（特别是虚拟环境）
3. 检查依赖是否完整：
   ```bash
   python -c "import pywinauto; import fastmcp; print('OK')"
   ```
4. 查看 AI 工具的 MCP 日志

### 问题：工具数量少于 162

**症状**：`--list-tools` 显示的工具数 < 162。

**排查步骤**：
1. 查看服务器启动日志中的警告信息
2. 检查是否有导入错误
3. 确认使用的是最新代码：`git pull`
4. 重新运行自检：`python scripts/self_check.py`

### 问题：AI 无法调用工具

**症状**：AI 能看到工具但调用失败。

**排查步骤**：
1. 检查工具参数是否正确
2. 查看工具返回的错误信息
3. 确认 MCP 服务器仍在运行
4. 检查是否有权限问题（UAC）

### 问题：pywin32 导入失败

**症状**：`ImportError: DLL load failed` 或类似错误。

**解决方法**：
```bash
# 运行 pywin32  post-install 脚本
python Scripts\pywin32_postinstall.py -install

# 或重新安装
pip uninstall pywin32
pip install pywin32
```

### 问题：操作需要管理员权限

**症状**：操作系统级应用时出现权限错误。

**解决方法**：
1. 以管理员身份运行 AI 工具
2. 或以管理员身份运行 MCP 服务器（HTTP 模式）
3. 避免操作需要管理员权限的应用

### 问题：中文乱码

**症状**：输入中文后出现乱码或问号。

**解决方法**：
1. 使用 `safe_type_text` 代替 `control_type_keys`
2. 确保系统区域设置支持中文
3. 确保 Python 文件编码为 UTF-8

---

## AI 执行注意事项

### 安全原则

1. **不修改系统关键设置**：不修改注册表、系统服务、环境变量（除非用户明确要求）
2. **不安装未经确认的软件**：下载安装包前应确认来源可信
3. **不删除用户文件**：清理操作前应确认
4. **不泄露敏感信息**：不在输出中包含 token、密码、密钥等

### 执行策略

1. **分步执行**：按步骤执行，每步验证后再继续
2. **失败回退**：如果某步失败，尝试替代方案，不要静默跳过
3. **状态报告**：每完成一个重要步骤，向用户报告进度
4. **用户确认**：涉及系统修改的操作（安装/卸载），应先确认

### 常见替代方案

| 问题 | 替代方案 |
|------|----------|
| git 不可用 | 下载 ZIP 解压 |
| pip 安装失败 | 使用国内镜像、升级 pip |
| 虚拟环境激活失败 | 使用全局 Python，或修改执行策略 |
| MCP 配置不生效 | 检查路径、重启工具、查看日志 |
| 服务器启动失败 | 检查依赖、查看错误输出 |

### 部署完成标志

当以下条件全部满足时，部署完成：
1. `self_check.py` 全部通过
2. `--list-tools` 显示 162 个工具
3. AI 工具能识别并调用 pywinauto 工具
4. `health_check` 调用返回 `healthy: true`

---

## 相关文档

- [快速开始指南](getting_started.md)
- [架构设计文档](architecture.md)
- [常见问题](faq.md)
- [API 参考](../references/api_reference.md)
- [100+ 工作流参考](../references/workflows.md)
- [贡献指南](../CONTRIBUTING.md)
- [变更日志](../CHANGELOG.md)

---

*最后更新: 2026-09-09 | 版本: v3.1.0*
