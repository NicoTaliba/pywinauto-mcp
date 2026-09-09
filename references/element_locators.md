# PyWinAuto MCP — 元素定位指南

## 定位条件总览

所有查找类工具（`window_find`, `app_window`, `control_child_window`, `desktop_window`, `find_windows`, `find_elements`）支持以下定位条件：

| 条件 | 类型 | UIA | Win32 | 说明 |
|------|------|-----|-------|------|
| `title` | str | ✓ | ✓ | 精确/模糊匹配窗口文本 |
| `title_re` | str | ✓ | ✓ | 正则匹配窗口文本 |
| `class_name` | str | ✓ | ✓ | 窗口类名精确匹配 |
| `class_name_re` | str | ✓ | ✓ | 窗口类名正则匹配 |
| `control_type` | str | ✓ | ✗ | UIA 控件类型（如 "Button", "Edit"） |
| `auto_id` | str | ✓ | ✗ | UIA Automation ID |
| `control_id` | int | ✗ | ✓ | Win32 控件 ID |
| `handle` | int | ✓ | ✓ | 窗口句柄 |
| `found_index` | int | ✓ | ✓ | 匹配结果中的零基索引 |
| `process` | int | ✓ | ✓ | 进程 ID 过滤 |
| `backend` | str | — | — | "uia" 或 "win32" |

## UIA 控件类型参考

常见 `control_type` 值：

| control_type | 说明 | 典型操作 |
|--------------|------|----------|
| `Button` | 按钮 | click, invoke |
| `Edit` | 编辑框/文本框 | set_text, get_text, type_keys |
| `Text` | 静态文本 | get_text |
| `ComboBox` | 组合框 | select, get_item_texts |
| `List` | 列表 | select, selected_index |
| `ListItem` | 列表项 | select, click |
| `CheckBox` | 复选框 | check, uncheck, is_checked |
| `RadioButton` | 单选按钮 | click, select |
| `Tab` | 标签控件 | select (tab), tab_get_selected |
| `TabItem` | 标签页 | click, select |
| `Tree` | 树控件 | tree_select, tree_expand |
| `TreeItem` | 树节点 | expand, collapse, select |
| `Menu` | 菜单 | menu_select, menu_get_items |
| `MenuItem` | 菜单项 | click, invoke |
| `Slider` | 滑块 | slider_get_position, slider_set_position |
| `ProgressBar` | 进度条 | progress_get_position |
| `ScrollBar` | 滚动条 | scroll |
| `Spinner` | 微调按钮 | click, set_value |
| `StatusBar` | 状态栏 | get_text |
| `ToolBar` | 工具栏 | child_window, click |
| `ToolTip` | 工具提示 | get_text |
| `Window` | 窗口 | close, maximize, set_focus |
| `Pane` | 面板/容器 | child_window, descendants |
| `Group` | 分组框 | child_window |
| `Header` | 表头 | — |
| `HeaderItem` | 表头项 | click |
| `DataGrid` | 数据网格 | descendants, child_window |
| `DataItem` | 数据项 | select, click |
| `Calendar` | 日历 | — |
| `Document` | 文档控件 | get_text, set_text |
| `SplitButton` | 拆分按钮 | click, expand |
| `AppBar` | 应用栏 | — |

## 定位策略示例

### 策略 1：通过 auto_id（最稳定）

```
control_child_window(
    wrapper_id="ctrl_xxx",
    control_type="Button",
    auto_id="okButton"
)
```

### 策略 2：通过 control_type + found_index

```
# 找到窗口中第 3 个 Edit 控件（零基索引=2）
control_child_window(
    wrapper_id="ctrl_xxx",
    control_type="Edit",
    found_index=2
)
```

### 策略 3：通过 title（文本匹配）

```
control_child_window(
    wrapper_id="ctrl_xxx",
    control_type="Button",
    title="OK"
)
```

### 策略 4：通过 title_re（正则匹配）

```
control_child_window(
    wrapper_id="ctrl_xxx",
    title_re=".*Save.*"
)
```

### 策略 5：通过 class_name

```
control_child_window(
    wrapper_id="ctrl_xxx",
    class_name="TButton"
)
```

### 策略 6：组合条件

```
control_child_window(
    wrapper_id="ctrl_xxx",
    control_type="Button",
    class_name="Button",
    found_index=0
)
```

## 模糊匹配规则

pywinauto 的 `title` 匹配使用 `findbestmatch` 算法，支持：

1. **大小写不敏感**：`title="ok"` 匹配 "OK"
2. **忽略 & 符号**：`title="File"` 匹配 "&File"
3. **忽略前后空格**：`title="OK"` 匹配 " OK "
4. **相似度匹配**：`title="Save"` 可能匹配 "Save As"（相似度足够高时）
5. **数字后缀**：`title="Edit"` 匹配 "Edit0", "Edit1" 等

**注意**：模糊匹配可能导致意外匹配。如果需要精确匹配，使用 `title_re` 并加上 `^...$` 锚点：
```
title_re="^OK$"
```

## 控件树探查流程

当不知道如何定位控件时，按以下步骤探查：

```
1. window_dump_tree(wrapper_id=窗口ID, depth=2)
   → 查看顶层控件结构

2. 如果需要更深层：
   window_dump_tree(wrapper_id=窗口ID, depth=5)

3. 对感兴趣的容器控件：
   control_children(wrapper_id=容器ID)
   → 列出直接子控件

4. 或者：
   control_descendants(wrapper_id=容器ID)
   → 列出所有后代控件

5. 获取特定控件的详细属性：
   control_get_properties(wrapper_id=控件ID)
   → 查看所有可用属性（包括 auto_id, control_type 等）
```

## 常见应用的控件特征

### 记事本 (Notepad)
- 窗口 class_name: `Notepad`
- 编辑区: `control_type="Edit"`, class_name=`Edit`
- 菜单: `control_type="MenuBar"` 或通过 `menu_select`

### 计算器 (Calculator)
- 数字按钮: `auto_id="num{0-9}Button"`
- 运算符: `auto_id="plusButton"`, `minusButton`, `multiplyButton`, `divideButton`
- 等号: `auto_id="equalButton"`
- 结果: `control_type="Text"`, `auto_id="CalculatorResults"`

### 文件对话框 (Open/Save)
- 文件名输入: `control_type="Edit"`, `found_index=1`（通常）
- 文件类型组合框: `control_type="ComboBox"`
- 打开/保存按钮: `control_type="Button"`, `title="Open"` 或 `"Save"`
- 取消按钮: `control_type="Button"`, `title="Cancel"`

### 设置应用 (Windows Settings)
- 全部使用 UIA 后端
- 搜索框: `control_type="Edit"`, `auto_id="SearchTextBox"`
- 导航列表: `control_type="List"` 或 `Tree`
- 开关: `control_type="CheckBox"` 或 `ToggleButton`

## 定位失败排查清单

1. ☐ 后端是否正确？（UIA 应用必须用 `backend="uia"`）
2. ☐ 控件是否已加载？（用 `window_wait` 等待）
3. ☐ 控件是否可见？（用 `control_is_visible` 检查）
3. ☐ 控件是否在需要先展开的容器内？（树节点、折叠面板等）
4. ☐ `control_type` 值是否正确？（用 `control_get_properties` 确认）
5. ☐ `auto_id` 是否存在？（不是所有应用都设置 auto_id）
6. ☐ 是否有多个匹配？（用 `found_index` 消除歧义）
7. ☐ 文本是否因本地化而变化？（用 `auto_id` 或 `control_type` 代替 `title`）
8. ☐ 控件是否在另一个窗口/对话框中？（先找到正确的父窗口）
