# 架构设计文档

## 1. 系统总览

PyWinAuto MCP 是一个基于 [pywinauto](https://github.com/pywinauto/pywinauto) 的 Windows GUI 自动化工具集，通过 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 协议将自动化能力暴露给 AI 客户端。

系统采用三层架构：

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client (AI)                        │
│              (Claude / Cursor / 自定义客户端)              │
└──────────────────────────┬──────────────────────────────┘
                           │ MCP Protocol (stdio / HTTP)
┌──────────────────────────▼──────────────────────────────┐
│                   MCP Server Layer                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  mcp_server.py (FastMCP 4.x)                      │  │
│  │  - 153 工具注册                                    │  │
│  │  - stdio / HTTP Streamable 传输                    │  │
│  │  - 显式参数版本（兼容 FastMCP 4.x 严格签名）        │  │
│  │  - 优雅关闭（会话清理）                              │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ 函数调用
┌──────────────────────────▼──────────────────────────────┐
│                  Wrapper & Engine Layer                   │
│  ┌──────────────────┐  ┌────────────────────────────┐  │
│  │ pywinauto_wrapper │  │ generation_engine.py        │  │
│  │  - 143 API 封装   │  │  - NL2Workflow 生成器       │  │
│  │  - 100 工作流引擎  │  │  - SmartLocator 定位器      │  │
│  │  - 会话管理        │  │  - AdaptiveExec 执行器      │  │
│  │  - 输入校验        │  │  - UIAnalyzer 分析器        │  │
│  │  - 重试/超时       │  │  - ScenarioLib 模板库       │  │
│  │  - 错误分类        │  │  - ScriptGen 脚本生成器     │  │
│  └──────────────────┘  └────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ pywinauto API
┌──────────────────────────▼──────────────────────────────┐
│                  pywinauto Library                         │
│  - application (Application, WindowSpecification)         │
│  - keyboard / mouse / clipboard / timings                 │
│  - controls (hwndwrapper, uiawrapper, common_controls)   │
│  - findwindows / taskbar / sysinfo                        │
└───────────────────────────────────────────────────────────┘
```

## 2. 核心模块

### 2.1 pywinauto_wrapper.py

**职责**：封装 pywinauto 全部 API，提供统一的 JSON 序列化接口，管理会话状态。

**核心组件**：

#### 会话管理
```
_app_sessions: dict[app_id, {app, created, last_used}]
_wrapper_sessions: dict[wrapper_id, {wrapper, created, last_used}]
```
- 使用 `RLock` 保证线程安全
- 2 小时 TTL 自动过期
- `app_id` 格式：`app_xxxxxxxxxxxx`（12位十六进制）
- `wrapper_id` 格式：`ctrl_xxxxxxxxxxxx`

#### 输入校验器
| 校验器 | 校验内容 |
|--------|----------|
| `_validate_backend` | 'uia' / 'win32' |
| `_validate_mouse_button` | 'left' / 'right' / 'middle' |
| `_validate_scroll_direction` | 'up' / 'down' / 'left' / 'right' |
| `_validate_nonempty` | 非空字符串 |
| `_validate_positive` | 正数 |
| `_validate_timeout` | 正数（>300s 警告） |
| `_validate_workflow_id` | WF001-WF999 格式 |

#### 重试与超时
- `_with_retry(func, retries, delay, backoff, retry_on)`：指数退避重试
- `_with_timeout(func, timeout)`：线程级超时（daemon 线程）
- `RetryExhaustedError` / `OperationTimeoutError` 自定义异常

#### 错误分类
`_classify_error(e)` 自动识别 7 类错误并提供恢复建议：
- `element_not_found`：检查定位条件、查看控件树、增加超时
- `timeout`：增加超时、降低速度、检查 CPU
- `element_disabled`：等待前置条件、检查依赖字段
- `element_not_visible`：滚动、展开、切换标签页
- `permission_denied`：需要管理员权限
- `session_expired`：重新连接/启动
- `unknown`：查看日志

#### 工作流引擎
- 100 条预置工作流（20 类 × 5 条）
- 35 条可执行，65 条指南
- 自定义工作流执行（`workflow_execute_custom`）
- 步骤级特性：条件分支、重试、超时、忽略错误、变量传递
- 条件表达式引擎：`$var$ == "value"`、`and`/`or`/`not`、点号路径

### 2.2 generation_engine.py

**职责**：提供生成级智能能力，从自然语言到可执行自动化。

#### NL2Workflow（自然语言转工作流）
```
输入文本 → 分句 → 动作模板匹配 → 参数提取 → 控件类型检测
        → 自动补全 → 步骤验证 → 置信度计算 → 输出
```
- 19 个动作模板（启动/连接/关闭/查找/聚焦/截图/输入/点击/快捷键/菜单/等待等）
- 自动补全：启动应用后自动获取主窗口，点击前自动查找目标控件
- 输出：步骤列表 + 推理过程 + 置信度 + 验证结果

#### SmartLocator（智能元素定位）
```
描述文本 → 控件类型检测 → 关键词提取 → 控件树遍历
        → 多维度评分 → 排序 → 最佳匹配自动注册
```
- 16 种控件类型自动检测
- 4 级模糊匹配：精确(1.0) > 包含(0.8+) > 缩写(0.6) > 字符相似度(0.5)
- 评分维度：控件类型(0.4) + 标题模糊匹配(0.3×N) + auto_id(0.4) + 可见/可用(0.1)

#### AdaptiveExec（自适应自愈执行）
```
步骤执行 → 失败？ → 错误分类 → 应用恢复策略 → 重试
                                    ↓ 全部失败
                              记录并停止/继续
```
- 6 类错误 × 2-4 种恢复策略
- 指数退避重试
- 完整恢复日志

#### UIAnalyzer（UI 理解分析）
- `analyze_ui`：界面结构统计 + 类型分布 + 自然语言描述
- `describe_element`：控件自然语言描述
- `find_interactive_elements`：可交互元素发现（17种类型过滤）

#### ScenarioLib（场景模板库）
- 10 个预置场景，每个定义参数 schema
- 参数化填充 + 步骤验证

#### ScriptGen（脚本生成器）
- 25+ 工具的代码生成
- 自动变量管理
- 标准 Python 脚本结构

### 2.3 mcp_server.py

**职责**：MCP 协议服务器，将 wrapper 函数暴露为 MCP 工具。

**技术选型**：[FastMCP 4.x](https://github.com/jlowin/fastmcp)

**关键设计**：

#### 显式参数版本
FastMCP 4.x 要求严格的函数签名（不支持 `**kwargs` / `*args`）。为所有含 `**kwargs` 的函数创建了显式参数版本：
- `app_connect_explicit`：8 个定位参数
- `app_window_explicit`：9 个定位参数
- `control_child_window_explicit`：8 个定位参数
- `timings_set_explicit`：17 个时序参数
- `batch_execute_explicit`：JSON 字符串参数
- `adaptive_execute_explicit`：JSON 字符串参数
- 等等...

#### 工具注册
```python
def _build_tool_registry() -> dict:
    registry = {}
    for name, func in pw.ALL_FUNCTIONS.items():
        if name in explicit_overrides:
            registry[name] = explicit_overrides[name]
        else:
            registry[name] = func
    return registry
```

#### 传输模式
- **stdio**（默认）：标准输入输出，适合本地 MCP 客户端
- **HTTP Streamable**：HTTP 流式传输，适合远程访问

#### 优雅关闭
- 服务器退出时自动清理全部会话
- 启动时执行健康检查并记录日志

## 3. 数据流

### 3.1 基础工具调用流

```
MCP Client
    │ JSON-RPC request (tool_name, params)
    ▼
MCP Server (FastMCP)
    │ 路由到注册的工具函数
    ▼
tool_wrapper (错误处理装饰器)
    │ 捕获异常 → 标准化返回
    ▼
explicit_version (参数适配)
    │ JSON 字符串 → dict / list
    ▼
pywinauto_wrapper function
    │ 输入校验 → 会话查找 → pywinauto API 调用
    ▼
pywinauto Library
    │ Windows UI Automation
    ▼
Windows GUI Application
```

### 3.2 自然语言自动化流（v3.0）

```
用户: "启动记事本，输入Hello，保存"
    │
    ▼
generate_workflow(description)
    │ 分句: ["启动记事本", "输入Hello", "保存"]
    │ 匹配: [app_start, safe_type_text, keyboard_send_keys]
    │ 补全: + app_top_window (自动获取主窗口)
    ▼
生成 4 步工作流 + 推理过程 + 置信度 0.9
    │
    ▼ (可选 auto_execute=True)
workflow_execute_custom(steps)
    │ 逐步执行，变量传递
    ▼
执行结果 + 上下文
```

### 3.3 自适应自愈流

```
步骤执行
    │
    ├─ 成功 → 下一步
    │
    └─ 失败
        │
        ▼
    错误分类 (6 类)
        │
        ▼
    应用恢复策略 (按序)
        │
        ├─ 扩大搜索范围
        ├─ 增加等待时间
        ├─ 切换后端
        └─ 使用 smart_find
        │
        ▼
    重试 (指数退避)
        │
        ├─ 成功 → 继续
        └─ 全部失败 → 记录恢复日志 → 停止/继续
```

## 4. 会话状态机

```
                    app_start / app_connect
                          │
                          ▼
                    ┌──────────┐
                    │  Active  │ ←── last_used 更新（每次调用）
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          ▼          ▼
        正常使用    2h无访问    服务器关闭
              │          │          │
              │          ▼          ▼
              │    ┌──────────┐  ┌──────┐
              │    │ Expired  │  │ Closed│
              │    └──────────┘  └──────┘
              │          │          │
              ▼          ▼          ▼
        继续使用    自动清理     清理全部
```

## 5. 扩展性设计

### 5.1 添加新工具

1. 在 `pywinauto_wrapper.py` 中添加封装函数
2. 注册到 `ALL_FUNCTIONS` 字典
3. 如果函数含 `**kwargs`，在 `mcp_server.py` 中添加显式参数版本
4. 在 `explicit_overrides` 中注册
5. 添加单元测试
6. 更新 `references/api_reference.md`

### 5.2 添加新工作流

1. 在 `pywinauto_wrapper.py` 的工作流注册区添加 `_register_workflow()`
2. 在 `references/workflows.md` 添加详细文档
3. 添加测试

### 5.3 添加新场景模板

1. 在 `generation_engine.py` 的 `SCENARIOS` 字典添加场景定义
2. 定义参数 schema 和步骤模板
3. 添加测试

### 5.4 添加新错误恢复策略

1. 在 `generation_engine.py` 的 `_RECOVERY_STRATEGIES` 添加策略
2. 在 `_classify_error` 中添加错误分类关键词
3. 在 `adaptive_execute` 中添加策略执行逻辑

## 6. 性能考量

| 操作 | 耗时 | 优化策略 |
|------|------|----------|
| 工具调用 | <10ms | 内存会话，无 IPC |
| 元素查找 | 50-500ms | 缓存会话，限定搜索深度 |
| 控件树遍历 | 100ms-2s | 深度限制（默认3），候选上限500 |
| 智能定位 | 200ms-3s | 多维度评分，提前剪枝 |
| 工作流执行 | 取决于步骤 | 步骤间等待可配置 |
| 健康检查 | <100ms | 轻量级检查 |

## 7. 安全设计

- **输入校验**：所有关键参数在执行前校验
- **会话隔离**：app_id/wrapper_id 仅在当前进程有效
- **无网络依赖**：纯本地操作，不发送数据到外部
- **权限透明**：需要管理员权限时明确提示
- **错误信息脱敏**：不暴露内部路径和敏感信息
- **操作可追溯**：调用统计记录每次工具调用

## 8. 测试策略

| 层级 | 覆盖范围 | 数量 |
|------|----------|------|
| 单元测试 | 版本/校验/错误分类/会话/重试/工作流/条件评估/生成引擎 | 72 |
| 集成测试 | MCP 服务器工具注册 | 153 工具 |
| 冒烟测试 | 基础操作（sysinfo/timings/clipboard/find_windows） | 5 |
| 自检脚本 | 环境依赖/模块导入/健康检查 | 7 大类 |

## 9. 相关文档

- [API 参考](../references/api_reference.md)
- [工作流参考](../references/workflows.md)
- [元素定位策略](../references/element_locators.md)
- [使用指南](../references/usage_guide.md)
- [快速开始](getting_started.md)
- [常见问题](faq.md)
- [贡献指南](../CONTRIBUTING.md)
- [变更日志](../CHANGELOG.md)
