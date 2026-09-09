# Credits / 参考成果声明

本项目在开发过程中参考、借鉴了以下开源项目、文档和资源。在此向所有原作者表示感谢。

---

## 核心依赖库

### 1. pywinauto
- **项目地址**: https://github.com/pywinauto/pywinauto
- **许可证**: BSD 3-Clause License
- **用途**: Windows GUI 自动化核心库，本项目的所有 API 封装均基于此库
- **参考内容**: 全部 16 个核心模块的公开 API（application, keyboard, mouse, clipboard, timings, controls, findwindows, taskbar, sysinfo 等）

### 2. FastMCP
- **项目地址**: https://github.com/jlowin/fastmcp
- **许可证**: MIT License
- **用途**: MCP (Model Context Protocol) 服务器框架
- **参考内容**: FastMCP 4.x 的工具注册机制、stdio/HTTP 传输、JSON Schema 生成

### 3. pywin32
- **项目地址**: https://github.com/mhammond/pywin32
- **许可证**: PSF License
- **用途**: Windows API Python 绑定，剪贴板操作等底层功能
- **参考内容**: win32clipboard 模块的使用方式

### 4. comtypes
- **项目地址**: https://github.com/enthought/comtypes
- **许可证**: MIT License
- **用途**: COM 接口访问，UIA 后端支持

### 5. Pydantic
- **项目地址**: https://github.com/pydantic/pydantic
- **许可证**: MIT License
- **用途**: 数据验证和设置管理

---

## 架构参考项目

### 6. wenyubo2008/pywinauto-mcp
- **项目地址**: https://github.com/wenyubo2008/pywinauto-mcp
- **许可证**: 未明确声明（按原仓库为准）
- **用途**: MCP 服务器架构设计参考
- **参考内容**:
  - FastMCP + pywinauto 的整体架构模式
  - portmanteau 工具命名模式（如 `app_start`, `control_click`）
  - Pydantic models 的参数定义方式
  - 会话管理（app_id / wrapper_id）的设计思路
- **说明**: 本项目在其基础上进行了大幅扩展，从原始的基础封装增强到 153 工具 + 100 工作流 + 生成级能力

---

## 文档参考

### 7. pywinauto 官方文档 (kancloud 镜像)
- **文档地址**: https://www.kancloud.cn/gnefnuy/pywinauto_doc/1193047
- **原文档**: https://pywinauto.readthedocs.io/
- **许可证**: 按原文档为准
- **用途**: pywinauto API 使用方法参考
- **参考内容**:
  - keyboard 模块的按键语法
  - Application/WindowSpecification 的使用方式
  - 各种控件类型的操作方法
  - timings 配置说明

### 8. MCP 官方规范
- **文档地址**: https://modelcontextprotocol.io/
- **许可证**: MIT License
- **用途**: MCP 协议规范参考
- **参考内容**: 工具定义、传输协议、JSON-RPC 消息格式

---

## 开源规范参考

### 9. Keep a Changelog
- **项目地址**: https://keepachangelog.com/
- **许可证**: MIT License
- **用途**: CHANGELOG.md 的格式规范

### 10. Conventional Commits
- **项目地址**: https://www.conventionalcommits.org/
- **许可证**: CC BY 3.0
- **用途**: 提交信息规范

### 11. Contributor Covenant
- **项目地址**: https://www.contributor-covenant.org/
- **许可证**: CC BY 4.0
- **用途**: CODE_OF_CONDUCT.md 的行为准则模板（版本 2.0）

### 12. Semantic Versioning
- **项目地址**: https://semver.org/
- **许可证**: CC BY 3.0
- **用途**: 版本号命名规范

---

## 示例代码参考

### 13. pywinauto 官方示例
- **项目地址**: https://github.com/pywinauto/pywinauto/tree/master/examples
- **许可证**: BSD 3-Clause License
- **用途**: 基础自动化示例的写法参考

### 14. FastMCP 官方示例
- **项目地址**: https://github.com/jlowin/fastmcp/tree/main/examples
- **许可证**: MIT License
- **用途**: MCP 服务器和工具注册的写法参考

---

## 声明

1. 本项目所有代码均为独立编写，未直接复制上述任何项目的源代码
2. 参考的架构设计、命名模式和最佳实践均属于通用编程思想，不构成侵权
3. 所有依赖库均通过 pip 安装，使用时遵守各自的许可证条款
4. 如原作者认为本项目有任何侵权之处，请通过 GitHub Issues 联系，我们将立即处理

---

## 贡献者

感谢所有为本项目做出贡献的人！

- 项目发起者和主要开发者
- 所有提交 Issue 和 PR 的贡献者
- 所有使用本项目并提供反馈的用户

---

*最后更新: 2026-09-09*
