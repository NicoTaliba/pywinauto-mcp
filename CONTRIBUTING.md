# Contributing to PyWinAuto MCP

首先感谢你考虑为 PyWinAuto MCP 做贡献！🎉

本文档描述了如何参与本项目的开发，包括代码规范、提交流程、测试要求等。

## 行为准则

参与本项目即表示你同意遵守 [Code of Conduct](CODE_OF_CONDUCT.md)。请确保所有互动都是尊重和包容的。

## 如何贡献

### 1. 报告 Bug

如果你发现了 Bug，请通过 [GitHub Issues](https://github.com/your-org/pywinauto-mcp/issues) 报告，并使用 **Bug Report** 模板。

好的 Bug 报告应包含：

- **清晰的标题**：简明描述问题
- **复现步骤**：详细的操作步骤
- **预期行为**：你期望发生什么
- **实际行为**：实际发生了什么
- **环境信息**：Windows 版本、Python 版本、pywinauto 版本
- **最小复现代码**：如果可能，提供能复现问题的最小代码片段
- **截图/日志**：相关的截图或错误日志

### 2. 请求新功能

如果你有新功能的想法，请通过 [GitHub Issues](https://github.com/your-org/pywinauto-mcp/issues) 提交，并使用 **Feature Request** 模板。

好的功能请求应包含：

- **问题描述**：这个功能解决什么问题
- **解决方案描述**：你希望如何实现
- **替代方案**：你考虑过的其他方案
- **附加上下文**：截图、原型、相关链接等

### 3. 提交代码

#### 开发流程

1. **Fork 仓库**并克隆到本地
   ```bash
   git clone https://github.com/your-username/pywinauto-mcp.git
   cd pywinauto-mcp
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或修复 Bug
   git checkout -b fix/your-bug-fix
   ```

3. **安装开发依赖**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **编写代码**，遵循下方的代码规范

5. **运行测试**，确保所有测试通过
   ```bash
   python tests/test_wrapper.py
   python scripts/self_check.py
   ```

6. **提交代码**，遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范
   ```bash
   git add .
   git commit -m "feat: add new workflow for Excel automation"
   ```

7. **推送分支**并创建 Pull Request
   ```bash
   git push origin feature/your-feature-name
   ```

#### Pull Request 要求

- **标题**：使用 Conventional Commits 格式（`feat:` / `fix:` / `docs:` 等）
- **描述**：清晰说明变更内容、原因和影响
- **关联 Issue**：如果修复了某个 Issue，请在描述中引用（如 `Fixes #123`）
- **测试**：确保所有现有测试通过，并为新功能添加测试
- **文档**：如果变更影响用户使用，请更新相关文档
- **代码审查**：至少需要一位维护者审查通过才能合并

## 代码规范

### Python 代码风格

- 遵循 [PEP 8](https://peps.python.org/pep-0008/) 代码风格
- 使用 4 空格缩进，不使用 Tab
- 行宽不超过 120 字符
- 使用有意义的变量名和函数名
- 函数和类必须有 docstring（Google 风格）

```python
def example_function(param1: str, param2: int = 0) -> dict[str, Any]:
    """简要描述函数功能。

    详细描述函数的行为、参数含义和返回值。

    Args:
        param1: 第一个参数的描述
        param2: 第二个参数的描述，默认为 0

    Returns:
        返回值的描述，包含字段说明

    Raises:
        ValueError: 参数无效时抛出
    """
    pass
```

### 类型注解

- 所有公共函数必须有完整的类型注解
- 使用 `from __future__ import annotations` 支持延迟求值
- 复杂类型使用 `typing` 模块（`Optional`, `Union`, `Callable` 等）

### 导入顺序

```python
# 1. 标准库
import os
import sys
import time

# 2. 第三方库
import pywinauto
from fastmcp import FastMCP

# 3. 本地模块
from .pywinauto_wrapper import ALL_FUNCTIONS
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块 | 小写+下划线 | `generation_engine.py` |
| 类 | 大驼峰 | `SmartLocator`, `AdaptiveExecutor` |
| 函数/方法 | 小写+下划线 | `generate_workflow()`, `find_element()` |
| 常量 | 全大写+下划线 | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| 变量 | 小写+下划线 | `app_id`, `wrapper_id` |
| 私有成员 | 单下划线前缀 | `_internal_method()`, `_private_var` |

## 测试规范

### 测试要求

- 所有新功能必须有对应的单元测试
- Bug 修复必须添加回归测试
- 测试覆盖率不低于 80%
- 测试必须在 Windows 环境下运行

### 测试结构

```python
class TestFeatureName(unittest.TestCase):
    """测试类描述。"""

    @classmethod
    def setUpClass(cls):
        """测试类级别的初始化。"""
        pass

    def setUp(self):
        """每个测试方法前的初始化。"""
        pass

    def test_feature_behavior(self):
        """测试方法描述。"""
        # Arrange
        # Act
        # Assert
        pass

    def tearDown(self):
        """每个测试方法后的清理。"""
        pass
```

### 运行测试

```bash
# 运行全部测试
python tests/test_wrapper.py

# 运行特定测试类
python -m pytest tests/test_wrapper.py::TestGenerationEngine -v

# 运行特定测试方法
python -m pytest tests/test_wrapper.py::TestGenerationEngine::test_generate_workflow_basic -v
```

## 文档规范

### 文档类型

- **README.md**：项目入口，特性概览，快速开始
- **docs/**：详细文档（架构、指南、FAQ）
- **references/**：API 参考、工作流参考
- **代码注释**：复杂逻辑必须有行内注释

### Markdown 规范

- 使用标准 Markdown 语法
- 标题层级不超过 4 级
- 代码块必须指定语言
- 链接使用相对路径
- 表格格式对齐

## 发布流程

### 版本号规范

遵循 [Semantic Versioning](https://semver.org/)：

- **主版本号 (MAJOR)**：不兼容的 API 变更
- **次版本号 (MINOR)**：向后兼容的功能新增
- **修订号 (PATCH)**：向后兼容的 Bug 修复

### 发布步骤

1. 更新 `CHANGELOG.md`，添加新版本条目
2. 更新版本号（`pywinauto_wrapper.py` 中的 `VERSION`，`mcp_server.py` 中的版本）
3. 确保所有测试通过
4. 创建 Git Tag：`git tag v3.1.0`
5. 推送 Tag：`git push origin v3.1.0`
6. 在 GitHub Releases 页面创建发布

## 获取帮助

- **文档**：阅读 [docs/](docs/) 和 [references/](references/)
- **FAQ**：查看 [docs/faq.md](docs/faq.md)
- **Issues**：搜索已有的 [GitHub Issues](https://github.com/your-org/pywinauto-mcp/issues)
- **讨论**：在 [GitHub Discussions](https://github.com/your-org/pywinauto-mcp/discussions) 提问

## 致谢

感谢所有为这个项目做出贡献的人！

<a href="https://github.com/your-org/pywinauto-mcp/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=your-org/pywinauto-mcp" />
</a>
