# PyWinAuto MCP — 100 条桌面 GUI 常用工作流

本文件收录 100 条可直接执行的桌面 GUI 自动化工作流，按 20 个场景分类，每类 5 条。
每条工作流包含：用途说明、所需参数、执行步骤（工具调用序列）。

工作流可通过 `workflow_execute(workflow_id, params)` 工具一键执行，也可手动按步骤调用。

---

## 目录

1. [应用生命周期](#1-应用生命周期-wf001-wf005)
2. [窗口管理](#2-窗口管理-wf006-wf010)
3. [文本输入与编辑](#3-文本输入与编辑-wf011-wf015)
4. [按钮与控件交互](#4-按钮与控件交互-wf016-wf020)
5. [菜单与导航](#5-菜单与导航-wf021-wf025)
6. [列表与组合框](#6-列表与组合框-wf026-wf030)
7. [文件对话框操作](#7-文件对话框操作-wf031-wf035)
8. [对话框处理](#8-对话框处理-wf036-wf040)
9. [键盘快捷键](#9-键盘快捷键-wf041-wf045)
10. [鼠标操作](#10-鼠标操作-wf046-wf050)
11. [数据提取](#11-数据提取-wf051-wf055)
12. [验证与等待](#12-验证与等待-wf056-wf060)
13. [浏览器自动化](#13-浏览器自动化-wf061-wf065)
14. [系统操作](#14-系统操作-wf066-wf070)
15. [截图与捕获](#15-截图与捕获-wf071-wf075)
16. [表单填写](#16-表单填写-wf076-wf080)
17. [表格/网格操作](#17-表格网格操作-wf081-wf085)
18. [树控件操作](#18-树控件操作-wf086-wf090)
19. [标签页操作](#19-标签页操作-wf091-wf095)
20. [错误恢复与重试](#20-错误恢复与重试-wf096-wf100)

---

## 1. 应用生命周期 (WF001-WF005)

### WF001: 启动应用并等待主窗口
**用途**: 启动一个应用程序，等待其主窗口出现并获取窗口句柄。
**参数**: `cmd_line` (应用路径), `backend` (默认 "uia"), `timeout` (默认 10)
**步骤**:
1. `app_start(cmd_line, backend, timeout)` → 获取 `app_id`
2. 等待最多 `timeout` 秒：循环 `app_windows(app_id)` 直到返回非空
3. `app_top_window(app_id)` → 获取 `wrapper_id` 和窗口信息
4. `window_wait(wrapper_id, wait_for="ready", timeout=5)`
**返回**: `{app_id, wrapper_id, window_info}`

### WF002: 连接到已运行应用
**用途**: 连接到已经在运行的应用程序（按标题/进程/路径匹配）。
**参数**: `title` 或 `process` 或 `path`, `backend` (默认 "uia")
**步骤**:
1. `app_connect(backend, title=..., process=..., path=...)` → 获取 `app_id`
2. `app_top_window(app_id)` → 获取 `wrapper_id`
**返回**: `{app_id, wrapper_id}`

### WF003: 安全关闭应用
**用途**: 优雅地关闭应用（先尝试正常关闭，超时后强制终止）。
**参数**: `app_id`, `grace_timeout` (默认 5)
**步骤**:
1. `app_top_window(app_id)` → 获取主窗口 `wrapper_id`
2. `control_close(wrapper_id)` — 尝试正常关闭
3. 等待 `grace_timeout` 秒：`app_is_process_running(app_id)`
4. 如果仍在运行：`app_kill(app_id, soft=False)` — 强制终止
5. `close_session(app_id)`
**返回**: `{closed: true, method: "close"|"kill"}`

### WF004: 重启应用
**用途**: 关闭并重新启动应用程序。
**参数**: `cmd_line`, `backend` (默认 "uia")
**步骤**:
1. 尝试 `app_connect(backend, title_re=...)` 查找已运行实例
2. 如果找到：执行 WF003 安全关闭
3. 执行 WF001 启动应用并等待
**返回**: `{app_id, wrapper_id, restarted: true}`

### WF005: 批量启动多个应用
**用途**: 依次启动多个应用程序，返回所有会话 ID。
**参数**: `apps` (列表，每项含 `cmd_line` 和可选 `backend`)
**步骤**:
1. 对每个 app：`app_start(cmd_line, backend)`
2. 对每个 app：`app_top_window(app_id)` 等待窗口
3. 收集所有 `app_id` 和 `wrapper_id`
**返回**: `{sessions: [{app_id, wrapper_id, cmd_line}]}`

---

## 2. 窗口管理 (WF006-WF010)

### WF006: 查找并聚焦窗口
**用途**: 按标题查找窗口并将其置于前台。
**参数**: `title` 或 `title_re`, `backend` (默认 "uia")
**步骤**:
1. `desktop_window(backend, title=..., title_re=...)` → 获取 `wrapper_id`
2. `control_set_focus(wrapper_id)`
3. `window_wait(wrapper_id, wait_for="visible", timeout=3)`
**返回**: `{wrapper_id, focused: true}`

### WF007: 窗口排列（平铺/层叠）
**用途**: 将多个窗口按指定方式排列。
**参数**: `window_titles` (列表), `mode` ("tile_h"|"tile_v"|"cascade"), `monitor` (默认 1)
**步骤**:
1. 获取屏幕尺寸：`sysinfo_os_arch()` + 系统 API（或使用固定分辨率）
2. 对每个标题：`desktop_window(title=...)` → `wrapper_id`
3. 根据 mode 计算每个窗口的 x, y, width, height
4. 对每个窗口：`control_move_window(wrapper_id, x, y, width, height)`
**返回**: `{arranged: count, mode}`

### WF008: 最小化所有非活动窗口
**用途**: 最小化除当前活动窗口外的所有顶层窗口。
**参数**: 无
**步骤**:
1. `desktop_active_window()` → 获取活动窗口 `active_wrapper_id`
2. `desktop_windows()` → 获取所有窗口列表
3. 对每个窗口：如果 `wrapper_id != active_wrapper_id`，执行 `control_minimize(wrapper_id)`
**返回**: `{minimized: count, kept_active: active_title}`

### WF009: 窗口截图并保存
**用途**: 截取指定窗口的完整内容并保存为图片文件。
**参数**: `wrapper_id` 或 `title`, `save_path`, `backend` (默认 "uia")
**步骤**:
1. 如果提供 title：`desktop_window(backend, title=...)` → `wrapper_id`
2. `control_set_focus(wrapper_id)` — 确保窗口在前台
3. `control_capture_as_image(wrapper_id, save_path)`
**返回**: `{saved: save_path, size}`

### WF010: 监控窗口出现/消失
**用途**: 等待指定标题的窗口出现或消失，返回事件信息。
**参数**: `title` 或 `title_re`, `event` ("appear"|"disappear"), `timeout` (默认 10)
**步骤**:
1. 记录开始时间
2. 循环（每 0.5 秒）：`find_windows(title=..., title_re=...)`
3. 如果 event="appear" 且找到窗口 → 返回窗口信息
4. 如果 event="disappear" 且窗口消失 → 返回消失确认
5. 超时则返回超时错误
**返回**: `{event, window_info, elapsed}`

---

## 3. 文本输入与编辑 (WF011-WF015)

### WF011: 安全输入文本到编辑框
**用途**: 定位编辑框，清空原有内容，输入新文本（支持特殊字符）。
**参数**: `wrapper_id` (父窗口), `text`, `criteria` (定位编辑框的条件，默认 control_type="Edit")
**步骤**:
1. `control_child_window(wrapper_id, control_type="Edit", **criteria)` → `edit_id`
2. `control_set_focus(edit_id)`
3. `keyboard_send_keys(keys="^a")` — 全选原有内容
4. `keyboard_send_keys(keys="{DELETE}")` — 删除
5. 如果文本含特殊字符：`clipboard_set_data(text)` + `keyboard_send_keys(keys="^v")`
6. 否则：`control_set_edit_text(edit_id, text)`
**返回**: `{edit_id, text_set: text}`

### WF012: 追加文本到编辑框
**用途**: 在编辑框现有内容末尾追加文本。
**参数**: `edit_id`, `text`
**步骤**:
1. `control_set_focus(edit_id)`
2. `keyboard_send_keys(keys="^{END}")` — 跳到末尾
3. `clipboard_set_data(text)`
4. `keyboard_send_keys(keys="^v")`
**返回**: `{appended: text}`

### WF013: 替换编辑框中的指定文本
**用途**: 查找编辑框中的指定文本并替换为新文本。
**参数**: `edit_id`, `find_text`, `replace_text`
**步骤**:
1. `control_get_text(edit_id)` → 获取当前内容
2. 如果 `find_text` 在内容中：
   - `keyboard_send_keys(keys="^f")` — 打开查找（如果应用支持）
   - 或：全选内容，用新内容替换后整体设置
3. 简单方案：获取全文 → Python 替换 → `control_set_edit_text(edit_id, new_text)`
**返回**: `{replaced: true, old: find_text, new: replace_text}`

### WF014: 多行文本批量输入
**用途**: 向多行文本编辑器（如记事本）逐行输入文本。
**参数**: `edit_id`, `lines` (字符串列表), `line_delay` (默认 0.05)
**步骤**:
1. `control_set_focus(edit_id)`
2. 对每一行：
   - `clipboard_set_data(line)`
   - `keyboard_send_keys(keys="^v")`
   - `keyboard_send_keys(keys="{ENTER}")`
   - 等待 `line_delay` 秒
**返回**: `{lines_entered: count}`

### WF015: 撤销/重做/全选/复制/粘贴组合
**用途**: 对当前焦点控件执行标准编辑操作序列。
**参数**: `edit_id`, `actions` (列表，如 ["select_all", "copy", "paste"])
**步骤**:
1. `control_set_focus(edit_id)`
2. 映射 actions 到快捷键：
   - "select_all" → `^a`
   - "copy" → `^c`
   - "cut" → `^x`
   - "paste" → `^v`
   - "undo" → `^z`
   - "redo" → `^y`
   - "delete" → `{DELETE}`
   - "home" → `^{HOME}`
   - "end" → `^{END}`
3. 依次执行 `keyboard_send_keys(keys=...)`
**返回**: `{actions_executed: actions}`

---

## 4. 按钮与控件交互 (WF016-WF020)

### WF016: 安全点击按钮
**用途**: 定位按钮，验证其可用且可见，然后点击（带重试）。
**参数**: `wrapper_id` (父窗口), `criteria` (按钮定位条件), `retries` (默认 3)
**步骤**:
1. 循环 `retries` 次：
   - `control_child_window(wrapper_id, control_type="Button", **criteria)` → `btn_id`
   - `control_is_enabled(btn_id)` — 检查是否可用
   - `control_is_visible(btn_id)` — 检查是否可见
   - 如果可用且可见：`control_click(btn_id)` → 成功
   - 否则等待 0.5 秒重试
2. 全部重试失败则返回错误
**返回**: `{btn_id, clicked: true, attempts}`

### WF017: 切换复选框状态
**用途**: 将复选框设置为指定状态（勾选/取消勾选）。
**参数**: `checkbox_id`, `target_state` (true=勾选, false=取消)
**步骤**:
1. `control_is_checked(checkbox_id)` → 获取当前状态
2. 如果当前状态 != target_state：
   - `control_click(checkbox_id)` — 点击切换
   - 等待 0.2 秒
   - `control_is_checked(checkbox_id)` — 验证
3. 如果验证失败，再点击一次
**返回**: `{current_state, target_state, changed}`

### WF018: 选择单选按钮
**用途**: 在一组单选按钮中选择指定的选项。
**参数**: `wrapper_id` (父容器), `radio_criteria` (目标单选按钮定位条件)
**步骤**:
1. `control_child_window(wrapper_id, control_type="RadioButton", **radio_criteria)` → `radio_id`
2. `control_is_visible(radio_id)` — 验证可见
3. `control_click(radio_id)` — 点击选择
4. 等待 0.2 秒
5. `control_get_properties(radio_id)` — 验证选中状态（IsSelected 属性）
**返回**: `{radio_id, selected: true}`

### WF019: 切换开关/Toggle 控件
**用途**: 切换 UIA Toggle 控件（如开关按钮）到指定状态。
**参数**: `toggle_id`, `target_state` (true=开, false=关)
**步骤**:
1. `control_is_checked(toggle_id)` → 获取当前状态（ToggleState）
2. 如果当前状态 != target_state：
   - `control_invoke(toggle_id)` 或 `control_click(toggle_id)`
   - 等待 0.3 秒
   - 再次验证状态
**返回**: `{current_state, target_state}`

### WF020: 批量点击多个按钮
**用途**: 按顺序点击多个按钮（如向导的 Next > Next > Finish）。
**参数**: `wrapper_id`, `button_criteria_list` (按钮定位条件列表)
**步骤**:
1. 对每个 criteria：
   - `control_child_window(wrapper_id, control_type="Button", **criteria)` → `btn_id`
   - `control_click(btn_id)`
   - 等待 0.5 秒（让界面响应）
   - 如果需要等待新窗口：`window_wait(...)`
**返回**: `{clicked: count, buttons: [btn_ids]}`

---

## 5. 菜单与导航 (WF021-WF025)

### WF021: 通过菜单栏选择菜单项
**用途**: 通过窗口菜单栏选择指定路径的菜单项（如 File > Save As）。
**参数**: `wrapper_id` (主窗口), `menu_path` (如 "File->Save As...")
**步骤**:
1. `control_set_focus(wrapper_id)` — 确保窗口激活
2. `control_menu_select(wrapper_id, path=menu_path)`
3. 等待 0.5 秒让菜单响应
4. 如果预期有对话框出现：`window_wait(...)` 等待新窗口
**返回**: `{menu_selected: menu_path}`

### WF022: 获取菜单全部项并选择
**用途**: 先获取菜单的所有项，再根据文本选择指定项。
**参数**: `wrapper_id`, `menu_path` (可选，子菜单路径), `target_item`
**步骤**:
1. `menu_get_items(wrapper_id, path=menu_path)` → 获取菜单项列表
2. 在列表中查找 `target_item`（支持模糊匹配）
3. 如果找到：拼接完整路径 `menu_path + "->" + target_item`
4. `control_menu_select(wrapper_id, path=完整路径)`
**返回**: `{items: [...], selected: target_item}`

### WF023: 右键菜单操作
**用途**: 在指定控件上右键点击，然后从上下文菜单中选择项。
**参数**: `wrapper_id` (目标控件), `menu_item` (上下文菜单项文本), `x`, `y` (可选坐标)
**步骤**:
1. `control_right_click(wrapper_id, x, y)` — 右键点击弹出上下文菜单
2. 等待 0.3 秒
3. `desktop_window(control_type="Menu")` 或查找弹出菜单窗口
4. `control_child_window(menu_id, control_type="MenuItem", title=menu_item)` → `item_id`
5. `control_click(item_id)`
**返回**: `{context_menu_item: menu_item, clicked: true}`

### WF024: 键盘快捷键打开菜单
**用途**: 使用 Alt 键激活菜单栏，然后用方向键导航并选择菜单项。
**参数**: `wrapper_id`, `menu_keys` (如 "%f" 打开 File, "{DOWN}{ENTER}")
**步骤**:
1. `control_set_focus(wrapper_id)`
2. `keyboard_send_keys(keys="%")` — 按 Alt 激活菜单栏
3. 等待 0.2 秒
4. `keyboard_send_keys(keys=menu_keys)` — 发送菜单导航键
**返回**: `{menu_keys_sent: menu_keys}`

### WF025: 最近打开文件列表选择
**用途**: 从应用的 "最近打开文件" 菜单中选择指定文件。
**参数**: `wrapper_id`, `file_name` (文件名或索引), `menu_path` (默认 "File->Recent")
**步骤**:
1. `menu_get_items(wrapper_id, path=menu_path)` → 获取最近文件列表
2. 按 `file_name` 模糊匹配或按索引选择
3. 拼接完整路径并 `control_menu_select(wrapper_id, path=...)`
4. 等待文件加载：`window_wait(wrapper_id, wait_for="ready", timeout=10)`
**返回**: `{selected_file: file_name, loaded: true}`

---

## 6. 列表与组合框 (WF026-WF030)

### WF026: 从组合框选择项
**用途**: 展开组合框，从下拉列表中选择指定项。
**参数**: `combo_id`, `item_text` 或 `index`
**步骤**:
1. `control_set_focus(combo_id)`
2. `combobox_get_items(combo_id)` → 获取所有项
3. 验证 `item_text` 存在于列表中
4. 如果提供 `item_text`：`combobox_select(combo_id, item_text)`
5. 如果提供 `index`：`control_select(combo_id, index=index)`
6. 等待 0.3 秒
7. `control_selected_text(combo_id)` — 验证选择结果
**返回**: `{selected: item_text, items: [...]}`

### WF027: 获取列表框全部项
**用途**: 提取列表框中所有项的文本，返回完整列表。
**参数**: `list_id`
**步骤**:
1. `control_get_item_texts(list_id)` → 获取所有项文本
2. 如果上述失败：尝试 `control_descendants(list_id, control_type="ListItem")` → 逐个 `control_get_text`
3. 返回项列表和总数
**返回**: `{items: [...], count}`

### WF028: 列表多选（Ctrl+点击）
**用途**: 在支持多选的列表中选择多个项。
**参数**: `list_id`, `item_texts` (要选择的项文本列表)
**步骤**:
1. `control_set_focus(list_id)`
2. `keyboard_send_keys(keys="^a")` — 先全选（如果需要清除则先取消）
3. 对每个 `item_text`：
   - 查找列表项：`control_child_window(list_id, control_type="ListItem", title=item_text)` → `item_id`
   - 按住 Ctrl：`keyboard_key_press(key="VK_CONTROL")`
   - `control_click(item_id)`
   - 释放 Ctrl：`keyboard_key_release(key="VK_CONTROL")`
**返回**: `{selected_items: item_texts}`

### WF029: 列表项双击打开
**用途**: 在列表/文件浏览器中双击指定项以打开。
**参数**: `list_id`, `item_text` 或 `index`
**步骤**:
1. `control_child_window(list_id, control_type="ListItem", title=item_text)` → `item_id`
2. `control_set_focus(item_id)`
3. `control_double_click(item_id)`
4. 等待 1 秒让应用响应
5. 如果预期新窗口：`desktop_window(...)` 查找并等待
**返回**: `{item_opened: item_text}`

### WF030: 动态添加项到列表
**用途**: 通过应用的添加按钮/对话框向列表中添加新项。
**参数**: `wrapper_id`, `add_button_criteria`, `new_item_text`, `confirm_button_criteria`
**步骤**:
1. 执行 WF016 点击 "添加" 按钮
2. 等待添加对话框出现：`window_wait(...)`
3. 在对话框中找到输入框：`control_child_window(dialog_id, control_type="Edit")` → `edit_id`
4. 执行 WF011 输入 `new_item_text`
5. 执行 WF016 点击确认按钮
6. 验证新项出现在列表中：`control_get_item_texts(list_id)`
**返回**: `{added: new_item_text, verified: true}`

---

## 7. 文件对话框操作 (WF031-WF035)

### WF031: 在"打开"对话框中选择文件
**用途**: 在标准 Windows "打开" 文件对话框中输入路径并打开文件。
**参数**: `dialog_id`, `file_path`, `backend` (默认 "uia")
**步骤**:
1. `window_wait(dialog_id, wait_for="visible", timeout=5)` — 等待对话框
2. 找到文件名输入框：`control_child_window(dialog_id, control_type="Edit", found_index=1)` → `file_edit_id`
   （或用 `auto_id="FileNameControlHost"` / `class_name="Edit"`）
3. `control_set_focus(file_edit_id)`
4. `keyboard_send_keys(keys="^a")` — 全选
5. `clipboard_set_data(file_path)`
6. `keyboard_send_keys(keys="^v")` — 粘贴路径
7. 找到"打开"按钮：`control_child_window(dialog_id, control_type="Button", title="打开")` → `open_btn_id`
8. `control_click(open_btn_id)`
**返回**: `{file_opened: file_path}`

### WF032: 在"另存为"对话框中保存文件
**用途**: 在标准 "另存为" 对话框中设置文件名和保存类型，然后保存。
**参数**: `dialog_id`, `file_name`, `save_path` (可选目录), `file_type` (可选)
**步骤**:
1. `window_wait(dialog_id, wait_for="visible", timeout=5)`
2. 如果提供 `save_path`：在地址栏输入路径（类似 WF031）
3. 找到文件名输入框并输入 `file_name`（执行 WF011）
4. 如果提供 `file_type`：找到保存类型组合框并选择（执行 WF026）
5. 找到"保存"按钮并点击
6. 如果出现"文件已存在"确认对话框：点击"是"
**返回**: `{file_saved: file_name, path: save_path}`

### WF033: 浏览文件夹对话框导航
**用途**: 在 "浏览文件夹" 对话框中导航到指定目录并确认。
**参数**: `dialog_id`, `target_path`
**步骤**:
1. `window_wait(dialog_id, wait_for="visible", timeout=5)`
2. 尝试找到路径输入框（新版对话框有地址栏）
3. `clipboard_set_data(target_path)`
4. 在地址栏 `keyboard_send_keys(keys="^v")` + `{ENTER}`
5. 等待目录加载
6. 找到"确定"/"选择文件夹"按钮并点击
**返回**: `{folder_selected: target_path}`

### WF034: 取消文件对话框
**用途**: 安全地关闭打开/保存文件对话框（取消操作）。
**参数**: `dialog_id`
**步骤**:
1. 找到"取消"按钮：`control_child_window(dialog_id, control_type="Button", title="取消")`
2. `control_click(cancel_btn_id)`
3. 或直接：`keyboard_send_keys(keys="{ESC}")`
4. 验证对话框已关闭：`window_exists(dialog_id)` 应返回 false
**返回**: `{dialog_cancelled: true}`

### WF035: 从文件对话框获取文件列表
**用途**: 提取文件对话框中当前目录的所有文件和文件夹名称。
**参数**: `dialog_id`
**步骤**:
1. 找到文件列表视图：`control_child_window(dialog_id, control_type="List")` 或 `"DataGrid"` → `list_id`
2. `control_descendants(list_id, control_type="ListItem")` 或 `"DataItem"` → 获取所有项
3. 对每个项：`control_get_text(item_id)` → 获取名称
4. 区分文件和文件夹（通过图标/类型属性）
**返回**: `{files: [...], folders: [...], count}`

---

## 8. 对话框处理 (WF036-WF040)

### WF036: 处理确认对话框（是/否）
**用途**: 自动检测并响应 Yes/No 确认对话框。
**参数**: `expected_title` (可选), `action` ("yes"|"no"), `timeout` (默认 5)
**步骤**:
1. 循环等待最多 `timeout` 秒：
   - `desktop_window(control_type="Window", title_re=".*确认.*|.*Confirm.*")` → 查找对话框
   - 或按 `expected_title` 查找
2. 找到对话框后：
   - 如果 action="yes"：找到"是"/"Yes"按钮并点击
   - 如果 action="no"：找到"否"/"No"按钮并点击
3. 等待对话框关闭
**返回**: `{dialog_handled: true, action, dialog_title}`

### WF037: 处理 OK 对话框
**用途**: 检测并点击消息框的"确定"/"OK"按钮。
**参数**: `expected_title` (可选), `timeout` (默认 5)
**步骤**:
1. 循环等待：`desktop_window(title_re=".*" + expected_title + ".*")` 或查找标准消息框
2. 找到"确定"按钮：`control_child_window(dialog_id, control_type="Button", title="确定")`
3. `control_click(ok_btn_id)`
4. 验证对话框已关闭
**返回**: `{ok_clicked: true, dialog_title}`

### WF038: 处理错误/警告对话框
**用途**: 检测错误或警告对话框，记录消息内容，然后关闭。
**参数**: `timeout` (默认 5), `dismiss` (默认 true)
**步骤**:
1. 循环等待：查找标题含 "错误"/"Error"/"警告"/"Warning" 的窗口
2. 找到对话框后：
   - 提取消息文本：`control_child_window(dialog_id, control_type="Text")` → `control_get_text`
   - 截图保存：`control_capture_as_image(dialog_id, save_path=...)`
   - 记录错误信息
3. 如果 `dismiss=true`：找到"确定"按钮并点击
**返回**: `{error_message, screenshot_path, dismissed}`

### WF039: 处理进度对话框
**用途**: 等待带进度条的对话框完成（如文件复制、下载进度）。
**参数**: `dialog_id`, `timeout` (默认 60), `poll_interval` (默认 1)
**步骤**:
1. `window_wait(dialog_id, wait_for="visible", timeout=5)`
2. 找到进度条：`control_child_window(dialog_id, control_type="ProgressBar")` → `progress_id`
3. 循环（每 `poll_interval` 秒）直到超时：
   - `progress_get_position(progress_id)` → 获取当前进度
   - 如果进度 >= 100 或对话框消失 → 完成
   - 记录进度变化
4. 如果对话框仍存在但进度停滞：返回超时警告
**返回**: `{completed: true, final_progress, elapsed}`

### WF040: 批量处理弹出对话框
**用途**: 在执行主操作过程中，自动处理可能出现的各种弹出对话框。
**参数**: `dialog_handlers` (字典：标题关键词 → 处理动作), `main_action` (主操作函数)
**步骤**:
1. 启动后台轮询线程（或在主操作间隙轮询）：
   - 每 0.5 秒 `enumerate_windows()` 检查新窗口
   - 对每个新窗口，匹配 `dialog_handlers` 中的标题关键词
   - 匹配成功则执行对应动作（点击 OK/Yes/No/Cancel）
2. 执行主操作
3. 主操作完成后停止轮询
4. 返回处理过的对话框列表
**返回**: `{dialogs_handled: [{title, action}], main_result}`

---

## 9. 键盘快捷键 (WF041-WF045)

### WF041: 全局保存（Ctrl+S）
**用途**: 对当前活动窗口执行保存操作，并等待保存完成。
**参数**: `wrapper_id` (可选，指定窗口), `wait_time` (默认 1)
**步骤**:
1. 如果提供 `wrapper_id`：`control_set_focus(wrapper_id)`
2. `keyboard_send_keys(keys="^s")`
3. 等待 `wait_time` 秒
4. 如果出现"另存为"对话框：执行 WF032
5. 验证标题栏是否不再有 "未保存" 标记（如果适用）
**返回**: `{saved: true, shortcut: "Ctrl+S"}`

### WF042: 全局复制粘贴文本
**用途**: 从源控件复制文本，粘贴到目标控件。
**参数**: `source_id`, `target_id`, `clear_target` (默认 true)
**步骤**:
1. `control_set_focus(source_id)`
2. `keyboard_send_keys(keys="^a")` — 全选源文本
3. `keyboard_send_keys(keys="^c")` — 复制
4. `control_set_focus(target_id)`
5. 如果 `clear_target`：`keyboard_send_keys(keys="^a{DELETE}")`
6. `keyboard_send_keys(keys="^v")` — 粘贴
7. 验证：`control_get_text(target_id)` 应包含复制的文本
**返回**: `{copied: true, source_text, target_verified: true}`

### WF043: 应用快捷键序列
**用途**: 对指定窗口依次执行多个键盘快捷键组合。
**参数**: `wrapper_id`, `shortcuts` (列表，如 ["^a", "^c", "%{F4}"]), `delay` (默认 0.1)
**步骤**:
1. `control_set_focus(wrapper_id)`
2. 对每个 shortcut：
   - `keyboard_send_keys(keys=shortcut)`
   - 等待 `delay` 秒
3. 返回执行的快捷键列表
**返回**: `{shortcuts_executed: shortcuts}`

### WF044: 功能键操作（F1-F12）
**用途**: 发送功能键（如 F1 帮助、F2 重命名、F5 刷新、F11 全屏）。
**参数**: `wrapper_id`, `function_key` (如 "F1", "F5", "F11"), `modifiers` (可选，如 "ctrl", "shift", "alt")
**步骤**:
1. `control_set_focus(wrapper_id)`
2. 构建按键字符串：
   - 无修饰符：`{F5}`
   - Ctrl：`^{F5}`
   - Shift：`+{F5}`
   - Alt：`%{F5}`
   - 组合：`^+{F5}` (Ctrl+Shift+F5)
3. `keyboard_send_keys(keys=组合键)`
4. 等待应用响应
**返回**: `{function_key_sent: 组合键}`

### WF045: 系统级快捷键
**用途**: 发送 Windows 系统级快捷键（Win+D 显示桌面、Alt+Tab 切换、Win+L 锁屏等）。
**参数**: `shortcut_name` ("show_desktop"|"switch_window"|"lock"|"task_manager"|"run"|"search"|"action_center")
**步骤**:
1. 映射 shortcut_name 到按键：
   - "show_desktop" → `{VK_LWIN down}d{VK_LWIN up}`
   - "switch_window" → `%{TAB}`
   - "lock" → `{VK_LWIN down}l{VK_LWIN up}`
   - "task_manager" → `^+{ESC}`
   - "run" → `{VK_LWIN down}r{VK_LWIN up}`
   - "search" → `{VK_LWIN down}s{VK_LWIN up}`
   - "action_center" → `{VK_LWIN down}a{VK_LWIN up}`
2. `keyboard_send_keys(keys=映射后的按键)`
**返回**: `{system_shortcut: shortcut_name, keys_sent}`

---

## 10. 鼠标操作 (WF046-WF050)

### WF046: 点击屏幕坐标
**用途**: 在屏幕指定坐标处执行点击（无需定位控件）。
**参数**: `x`, `y`, `button` (默认 "left"), `double` (默认 false)
**步骤**:
1. `mouse_move(x, y)` — 移动鼠标到目标位置
2. 等待 0.1 秒
3. `mouse_click(button=button, x=x, y=y, double=double)`
4. 可选：截图验证点击效果
**返回**: `{clicked_at: {x, y}, button, double}`

### WF047: 拖拽文件/对象
**用途**: 从源坐标拖拽到目标坐标（如拖拽文件到回收站、拖拽排序）。
**参数**: `src_x`, `src_y`, `dst_x`, `dst_y`, `button` (默认 "left"), `duration` (默认 0.5)
**步骤**:
1. `mouse_move(src_x, src_y)` — 移到起点
2. 等待 0.2 秒
3. `mouse_press(button=button, x=src_x, y=src_y)` — 按下
4. 分步移动（模拟平滑拖拽）：
   - 计算中间点，分 5 步移动
   - 每步等待 `duration/5` 秒
5. `mouse_move(dst_x, dst_y)` — 到达终点
6. 等待 0.2 秒
7. `mouse_release(button=button, x=dst_x, y=dst_y)` — 释放
**返回**: `{dragged: {from: {src_x, src_y}, to: {dst_x, dst_y}}}`

### WF048: 鼠标悬停显示提示
**用途**: 将鼠标悬停在控件上，等待工具提示出现并提取文本。
**参数**: `wrapper_id`, `hover_time` (默认 1.5), `x`, `y` (可选坐标)
**步骤**:
1. 获取控件位置：`control_get_rectangle(wrapper_id)` → 计算中心点
2. `mouse_move(center_x, center_y)` — 移到控件中心
3. 等待 `hover_time` 秒（让工具提示出现）
4. 查找工具提示窗口：`desktop_window(control_type="ToolTip")` 或 `class_name="tooltips_class32"`
5. 如果找到：`control_get_text(tooltip_id)` → 获取提示文本
6. 截图保存（可选）
**返回**: `{tooltip_text, hover_position}`

### WF049: 鼠标滚轮滚动
**用途**: 在指定位置滚动鼠标滚轮（向上/向下/水平）。
**参数**: `x`, `y` (可选，默认当前位置), `direction` ("up"|"down"), `amount` (默认 3), `steps` (默认 1)
**步骤**:
1. 如果提供 x,y：`mouse_move(x, y)`
2. 循环 `steps` 次：
   - `mouse_scroll(direction=direction, amount=amount)`
   - 等待 0.2 秒
3. 可选：截图验证滚动效果
**返回**: `{scrolled: {direction, amount, steps}, at_position: {x, y}}`

### WF050: 画框选择（拖拽选择区域）
**用途**: 在画布/桌面/图像编辑器中拖拽画框选择区域。
**参数**: `start_x`, `start_y`, `end_x`, `end_y`
**步骤**:
1. `mouse_move(start_x, start_y)`
2. `mouse_press(button="left", x=start_x, y=start_y)`
3. 等待 0.1 秒
4. `mouse_move(end_x, end_y)`
5. 等待 0.1 秒
6. `mouse_release(button="left", x=end_x, y=end_y)`
7. 截图验证选择框
**返回**: `{selection_rect: {start_x, start_y, end_x, end_y}}`

---

## 11. 数据提取 (WF051-WF055)

### WF051: 提取窗口全部文本
**用途**: 递归提取窗口及其所有子控件的文本内容。
**参数**: `wrapper_id`, `depth` (默认 10)
**步骤**:
1. `window_dump_tree(wrapper_id, depth=depth)` → 获取控件树文本
2. `control_descendants(wrapper_id)` → 获取所有后代控件
3. 对每个后代控件：尝试 `control_get_text(desc_id)` → 收集非空文本
4. 按控件层级组织结果（树形结构）
5. 返回结构化文本数据
**返回**: `{all_text: [...], tree_dump, control_count}`

### WF052: 提取表单所有字段值
**用途**: 从表单对话框中提取所有输入字段（编辑框、组合框、复选框等）的当前值。
**参数**: `form_id`
**步骤**:
1. `control_descendants(form_id, control_type="Edit")` → 所有编辑框
2. 对每个编辑框：`control_get_text(edit_id)` → 值
3. `control_descendants(form_id, control_type="ComboBox")` → 所有组合框
4. 对每个组合框：`control_selected_text(combo_id)` → 选中值
5. `control_descendants(form_id, control_type="CheckBox")` → 所有复选框
6. 对每个复选框：`control_is_checked(cb_id)` → 状态
7. `control_descendants(form_id, control_type="RadioButton")` → 所有单选按钮
8. 对每个单选按钮：检查 IsSelected 属性
9. 汇总所有字段值，按控件名称/索引组织
**返回**: `{fields: {edits: [...], combos: [...], checkboxes: [...], radios: [...]}}`

### WF053: 提取表格/数据网格全部数据
**用途**: 从 DataGrid/ListView 控件中提取所有行和列的数据。
**参数**: `grid_id`
**步骤**:
1. `control_descendants(grid_id, control_type="Header")` → 获取表头
2. 对每个 HeaderItem：`control_get_text(header_id)` → 列名
3. `control_descendants(grid_id, control_type="DataItem")` 或 `"ListItem"` → 获取所有行
4. 对每行：
   - `control_descendants(row_id, control_type="Text")` → 获取单元格
   - 对每个单元格：`control_get_text(cell_id)` → 值
5. 组装为二维数组（行 × 列）
6. 返回表头 + 数据行
**返回**: `{headers: [...], rows: [[...], ...], row_count, col_count}`

### WF054: 提取控件属性快照
**用途**: 获取控件的所有可用属性，用于调试和定位。
**参数**: `wrapper_id`
**步骤**:
1. `control_get_properties(wrapper_id)` → 获取所有属性
2. `control_get_rectangle(wrapper_id)` → 位置和大小
3. `control_get_class_name(wrapper_id)` → 类名
4. `control_get_backend(wrapper_id)` → 后端
5. `control_get_handle(wrapper_id)` → 句柄
6. `control_is_visible(wrapper_id)` → 可见性
7. `control_is_enabled(wrapper_id)` → 可用性
8. `control_is_active(wrapper_id)` → 活动状态
9. 汇总为完整属性快照
**返回**: `{properties: {...}, rectangle, class_name, backend, handle, states}`

### WF055: 提取窗口列表及状态
**用途**: 枚举当前所有顶层窗口，返回标题、类名、进程、状态等信息。
**参数**: `visible_only` (默认 true), `backend` (默认 "uia")
**步骤**:
1. `enumerate_windows(backend=backend)` → 获取所有窗口
2. 如果 `visible_only`：过滤 `is_visible == true` 的窗口
3. 对每个窗口：补充 `is_enabled`, `rect` (如果可获取)
4. 按进程 ID 分组
5. 返回窗口列表和统计信息
**返回**: `{windows: [...], total_count, visible_count, processes: [...]}`

---

## 12. 验证与等待 (WF056-WF060)

### WF056: 等待窗口出现并验证
**用途**: 等待指定标题的窗口出现，验证其可见且可用，返回窗口信息。
**参数**: `title` 或 `title_re`, `timeout` (默认 10), `backend` (默认 "uia")
**步骤**:
1. 记录开始时间
2. 循环（每 0.5 秒）直到超时：
   - `find_windows(backend, title=..., title_re=...)` → 查找窗口句柄
   - 如果找到：`desktop_window(backend, handle=句柄)` → `wrapper_id`
   - `window_wait(wrapper_id, wait_for="ready", timeout=3)` → 验证就绪
   - 返回窗口信息
3. 超时返回错误
**返回**: `{wrapper_id, window_info, waited: elapsed}`

### WF057: 验证控件文本包含指定内容
**用途**: 检查控件的文本是否包含预期内容（支持精确/模糊/正则匹配）。
**参数**: `wrapper_id`, `expected_text`, `match_mode` ("exact"|"contains"|"regex"), `case_sensitive` (默认 false)
**步骤**:
1. `control_get_text(wrapper_id)` → 获取实际文本
2. 根据 `match_mode` 比较：
   - "exact": 实际文本 == expected_text（考虑大小写）
   - "contains": expected_text in 实际文本
   - "regex": re.search(expected_text, 实际文本)
3. 返回匹配结果和实际文本
4. 如果不匹配，返回差异信息
**返回**: `{matched: true|false, actual_text, expected_text, match_mode}`

### WF058: 等待控件状态变化
**用途**: 等待控件的可见性/可用性/文本发生变化，返回变化前后的状态。
**参数**: `wrapper_id`, `property` ("visible"|"enabled"|"text"|"checked"), `expected_value`, `timeout` (默认 10)
**步骤**:
1. 获取初始状态：
   - "visible" → `control_is_visible(wrapper_id)`
   - "enabled" → `control_is_enabled(wrapper_id)`
   - "text" → `control_get_text(wrapper_id)`
   - "checked" → `control_is_checked(wrapper_id)`
2. 循环（每 0.3 秒）直到超时：
   - 重新获取当前状态
   - 如果当前状态 == expected_value → 返回成功
3. 超时返回失败，包含初始和最终状态
**返回**: `{changed: true|false, property, initial_value, final_value, expected_value, elapsed}`

### WF059: 验证按钮点击后状态变化
**用途**: 点击按钮前后验证控件状态变化（如复选框勾选、文本变化、窗口出现）。
**参数**: `button_id`, `target_id` (被验证的控件), `property`, `expected_after`, `timeout` (默认 3)
**步骤**:
1. 获取点击前状态（同 WF058 的初始状态获取）
2. `control_click(button_id)` — 点击按钮
3. 等待最多 `timeout` 秒：循环检查 `target_id` 的 `property`
4. 如果达到 `expected_after` → 验证成功
5. 返回点击前后状态对比
**返回**: `{verified: true|false, property, before, after, expected_after, elapsed}`

### WF060: 轮询验证直到条件满足
**用途**: 反复执行验证函数，直到条件满足或超时（通用等待原语）。
**参数**: `verify_func` (验证逻辑描述), `interval` (默认 0.5), `timeout` (默认 15), `description`
**步骤**:
1. 记录开始时间
2. 循环（每 `interval` 秒）直到超时：
   - 执行验证操作（如检查文本、检查窗口存在、检查进程状态）
   - 如果验证通过 → 返回成功
   - 否则继续等待
3. 超时返回失败，包含最后一次验证结果
4. 记录总等待时间和尝试次数
**返回**: `{passed: true|false, description, attempts, elapsed, last_result}`

---

## 13. 浏览器自动化 (WF061-WF065)

### WF061: 在浏览器地址栏输入 URL
**用途**: 聚焦浏览器窗口，在地址栏输入 URL 并导航。
**参数**: `browser_title` 或 `browser_wrapper_id`, `url`
**步骤**:
1. 如果提供 title：`desktop_window(title_re=".*" + browser_title + ".*")` → `browser_id`
2. `control_set_focus(browser_id)`
3. `keyboard_send_keys(keys="^l")` — 聚焦地址栏（Chrome/Edge/Firefox 通用）
4. 等待 0.3 秒
5. `clipboard_set_data(url)`
6. `keyboard_send_keys(keys="^v")` — 粘贴 URL
7. `keyboard_send_keys(keys="{ENTER}")` — 回车导航
8. 等待页面加载（可通过标题变化或进度条判断）
**返回**: `{url_navigated: url, browser_id}`

### WF062: 浏览器标签页管理
**用途**: 新建、切换、关闭浏览器标签页。
**参数**: `browser_id`, `action` ("new"|"switch_next"|"switch_prev"|"close"|"reopen"), `url` (可选，新标签页的 URL)
**步骤**:
1. `control_set_focus(browser_id)`
2. 映射 action 到快捷键：
   - "new" → `^t`（新建标签页）
   - "switch_next" → `^{TAB}`（下一个标签）
   - "switch_prev" → `^+{TAB}`（上一个标签）
   - "close" → `^w`（关闭当前标签）
   - "reopen" → `^+t`（重新打开关闭的标签）
3. `keyboard_send_keys(keys=快捷键)`
4. 如果 action="new" 且提供 url：执行 WF061 输入 URL
5. 等待 0.5 秒让浏览器响应
**返回**: `{tab_action: action, keys_sent}`

### WF063: 浏览器表单填写
**用途**: 在网页表单中填写文本字段（通过 Tab 键导航字段）。
**参数**: `browser_id`, `fields` (有序列表，每项为字段值), `submit` (默认 false)
**步骤**:
1. `control_set_focus(browser_id)`
2. 点击第一个输入框（通过坐标或 Tab 导航到第一个字段）
3. 对每个 field_value：
   - `clipboard_set_data(field_value)`
   - `keyboard_send_keys(keys="^v")` — 粘贴
   - `keyboard_send_keys(keys="{TAB}")` — 跳到下一个字段
   - 等待 0.2 秒
4. 如果 `submit=true`：`keyboard_send_keys(keys="{ENTER}")` — 提交表单
**返回**: `{fields_filled: count, submitted}`

### WF064: 浏览器截图整页
**用途**: 截取浏览器当前页面的完整截图（可视区域 + 滚动拼接）。
**参数**: `browser_id`, `save_path`, `full_page` (默认 false)
**步骤**:
1. `control_set_focus(browser_id)`
2. 如果 `full_page`：
   - 获取页面总高度（通过 JS 或滚动到底部判断）
   - 循环滚动并截取每个可视区域
   - 拼接所有截图为整页图
3. 否则：`control_capture_as_image(browser_id, save_path)`
4. 返回截图路径和尺寸
**返回**: `{screenshot_saved: save_path, full_page, size}`

### WF065: 浏览器下载文件处理
**用途**: 触发浏览器下载，等待下载完成，获取下载的文件路径。
**参数**: `browser_id`, `download_trigger` (触发下载的操作描述), `timeout` (默认 30), `download_dir` (默认 "~/Downloads")
**步骤**:
1. 记录下载前 `download_dir` 中的文件列表
2. 执行下载触发操作（如点击下载按钮、输入下载 URL）
3. 循环等待最多 `timeout` 秒：
   - 检查 `download_dir` 中是否出现新文件
   - 检查文件大小是否稳定（不再增长 = 下载完成）
   - 检查浏览器下载栏是否显示 "完成"
4. 下载完成后返回新文件的完整路径
**返回**: `{downloaded_file: path, file_size, elapsed}`

---

## 14. 系统操作 (WF066-WF070)

### WF066: 通过开始菜单启动应用
**用途**: 打开开始菜单，搜索并启动指定应用程序。
**参数**: `app_name` (应用名称，如 "记事本", "calc", "chrome")
**步骤**:
1. `keyboard_send_keys(keys="{VK_LWIN}")` — 打开开始菜单
2. 等待 0.5 秒
3. `taskbar_get_search_edit()` → 获取搜索框 `search_id`
4. `control_set_focus(search_id)`
5. `clipboard_set_data(app_name)`
6. `keyboard_send_keys(keys="^v")` — 输入应用名
7. 等待 1 秒让搜索结果出现
8. `keyboard_send_keys(keys="{ENTER}")` — 启动第一个搜索结果
9. 等待应用启动：`app_connect(title_re=".*" + app_name + ".*")` 或 `app_start`
**返回**: `{app_launched: app_name, search_used: true}`

### WF067: 任务栏操作
**用途**: 点击任务栏上的应用图标、系统托盘图标，或切换活动窗口。
**参数**: `action` ("click_app"|"show_desktop"|"open_tray"|"click_tray_icon"|"show_start"), `app_name` (可选), `tray_icon` (可选)
**步骤**:
1. 如果 action="click_app"：
   - `taskbar_click_on_button(text=app_name)` — 点击任务栏应用按钮
2. 如果 action="show_desktop"：
   - 找到任务栏右下角"显示桌面"区域并点击（坐标点击）
   - 或 `keyboard_send_keys(keys="{VK_LWIN down}d{VK_LWIN up}")`
3. 如果 action="open_tray"：
   - `taskbar_get_system_tray()` → 点击显示隐藏图标
4. 如果 action="click_tray_icon"：
   - 在系统托盘中找到 `tray_icon` 并点击
5. 如果 action="show_start"：
   - `taskbar_get_start_button()` → `control_click(start_id)`
**返回**: `{taskbar_action: action, executed: true}`

### WF068: 切换活动窗口（Alt+Tab 方式）
**用途**: 通过 Alt+Tab 在打开的窗口之间切换到指定应用。
**参数**: `target_title` (目标窗口标题关键词), `max_tabs` (默认 10)
**步骤**:
1. `desktop_active_window()` → 获取当前活动窗口
2. 如果当前窗口标题已包含 `target_title` → 无需切换
3. 按住 Alt：`keyboard_key_press(key="VK_MENU")`
4. 循环最多 `max_tabs` 次：
   - `keyboard_send_keys(keys="{TAB}")` — 切换到下一个窗口
   - 等待 0.3 秒
   - `desktop_active_window()` → 检查新活动窗口标题
   - 如果标题包含 `target_title` → 找到目标
5. 释放 Alt：`keyboard_key_release(key="VK_MENU")`
6. 等待窗口完全激活
**返回**: `{switched_to: target_title, tabs_used, current_title}`

### WF069: 系统托盘图标菜单操作
**用途**: 右键点击系统托盘图标，从弹出菜单中选择指定项。
**参数**: `icon_name` (托盘图标名称/提示), `menu_item` (菜单项文本)
**步骤**:
1. `taskbar_get_system_tray()` → 获取系统托盘区域
2. 在托盘中查找 `icon_name` 对应的图标（通过工具提示文本匹配）
3. `control_right_click(icon_id)` — 右键点击弹出菜单
4. 等待 0.3 秒
5. 查找弹出菜单：`desktop_window(control_type="Menu")` 或上下文菜单窗口
6. `control_child_window(menu_id, control_type="MenuItem", title=menu_item)` → `item_id`
7. `control_click(item_id)` — 选择菜单项
**返回**: `{tray_icon: icon_name, menu_item_selected: menu_item}`

### WF070: 锁定/休眠/关机
**用途**: 执行系统级操作（锁定工作站、休眠、关机、重启）。
**参数**: `action` ("lock"|"sleep"|"shutdown"|"restart"|"sign_out"), `force` (默认 false)
**步骤**:
1. 映射 action 到系统命令或快捷键：
   - "lock" → `keyboard_send_keys(keys="{VK_LWIN down}l{VK_LWIN up}")`
   - "sleep" → 执行 `rundll32.exe powrprof.dll,SetSuspendState 0,1,0`（通过 app_start）
   - "shutdown" → `app_start(cmd_line="shutdown /s /t 0" + (force ? " /f" : ""))`
   - "restart" → `app_start(cmd_line="shutdown /r /t 0" + (force ? " /f" : ""))`
   - "sign_out" → `app_start(cmd_line="shutdown /l")`
2. 执行对应操作
3. 注意：这些操作会影响系统状态，执行前应确认
**返回**: `{system_action: action, executed: true}`

---

## 15. 截图与捕获 (WF071-WF075)

### WF071: 截取指定窗口
**用途**: 截取指定窗口的完整内容（包括标题栏和边框），保存为图片。
**参数**: `wrapper_id` 或 `title`, `save_path`, `backend` (默认 "uia"), `set_foreground` (默认 true)
**步骤**:
1. 如果提供 title：`desktop_window(backend, title=...)` → `wrapper_id`
2. 如果 `set_foreground`：`control_set_focus(wrapper_id)` — 确保窗口在前台
3. 等待 0.3 秒让窗口重绘
4. `control_capture_as_image(wrapper_id, save_path)`
5. 验证文件已保存且非空
**返回**: `{screenshot_saved: save_path, window_title, size}`

### WF072: 截取屏幕区域
**用途**: 截取屏幕指定矩形区域的内容。
**参数**: `x1`, `y1`, `x2`, `y2`, `save_path`
**步骤**:
1. 计算区域宽度和高度
2. 使用 PIL ImageGrab 截取屏幕区域（或通过 pywinauto 的截图功能）
3. 保存到 `save_path`
4. 验证截图尺寸和文件大小
5. 返回截图路径和区域信息
**返回**: `{screenshot_saved: save_path, region: {x1, y1, x2, y2}, size}`

### WF073: 截取控件元素
**用途**: 截取窗口中特定控件的图像（如按钮、图表、图像区域）。
**参数**: `wrapper_id` (父窗口), `control_criteria` (控件定位条件), `save_path`
**步骤**:
1. `control_child_window(wrapper_id, **control_criteria)` → `control_id`
2. `control_is_visible(control_id)` — 验证控件可见
3. `control_capture_as_image(control_id, save_path)`
4. 验证截图
**返回**: `{control_screenshot: save_path, control_info}`

### WF074: 定时连续截图
**用途**: 按指定间隔连续截取屏幕/窗口，用于录制操作过程或监控变化。
**参数**: `wrapper_id` (可选), `count`, `interval` (默认 1), `save_dir`, `prefix` (默认 "screenshot")
**步骤**:
1. 创建 `save_dir`（如果不存在）
2. 循环 `count` 次：
   - 如果提供 `wrapper_id`：`control_capture_as_image(wrapper_id, save_path=...)`
   - 否则：截取全屏
   - 文件名：`{prefix}_{index:04d}.png`
   - 等待 `interval` 秒
3. 返回所有截图文件路径列表
**返回**: `{screenshots: [...], count, interval, save_dir}`

### WF075: 对比截图检测变化
**用途**: 截取当前窗口图像，与参考截图对比，检测 UI 变化。
**参数**: `wrapper_id`, `reference_path`, `threshold` (默认 0.95), `diff_save_path` (可选)
**步骤**:
1. `control_capture_as_image(wrapper_id)` → 获取当前图像（内存中）
2. 加载 `reference_path` 参考图像
3. 调整尺寸一致（如果需要）
4. 计算图像相似度（均方误差 / 结构相似度 SSIM）
5. 如果相似度 < `threshold`：
   - 生成差异图像（高亮变化区域）
   - 保存到 `diff_save_path`
   - 返回变化检测结果
6. 返回相似度和变化区域坐标
**返回**: `{similarity, changed: true|false, threshold, diff_image, changed_regions}`

---

## 16. 表单填写 (WF076-WF080)

### WF076: 填写文本字段组
**用途**: 按顺序填写表单中的多个文本输入框（通过 Tab 键导航）。
**参数**: `form_id`, `first_field_criteria` (第一个字段定位条件), `values` (有序值列表), `field_names` (可选字段名列表)
**步骤**:
1. `control_child_window(form_id, **first_field_criteria)` → `first_id`
2. `control_click(first_id)` — 点击第一个字段获得焦点
3. 对每个 value（及可选 field_name）：
   - `keyboard_send_keys(keys="^a")` — 全选原有内容
   - `clipboard_set_data(value)`
   - `keyboard_send_keys(keys="^v")` — 粘贴新值
   - `keyboard_send_keys(keys="{TAB}")` — 跳到下一个字段
   - 等待 0.2 秒
4. 返回填写的字段数和值
**返回**: `{fields_filled: count, values, field_names}`

### WF077: 填写带标签的表单
**用途**: 通过标签文本定位对应的输入框，填写表单（不依赖字段顺序）。
**参数**: `form_id`, `field_map` (字典：标签文本 → 字段值)
**步骤**:
1. 对每个 (label_text, value) in field_map：
   - 查找标签控件：`control_child_window(form_id, control_type="Text", title=label_text)` → `label_id`
   - 获取标签位置：`control_get_rectangle(label_id)`
   - 查找标签旁边的输入框（通过位置关系或 Tab 顺序）
   - 或：查找标签后的第一个 Edit 控件（通过 descendants 顺序）
   - `control_set_focus(edit_id)`
   - 执行 WF011 输入 value
2. 返回填写结果
**返回**: `{fields_filled: field_map, method: "label_based"}`

### WF078: 选择表单中的下拉选项
**用途**: 为表单中的多个组合框/下拉列表选择指定选项。
**参数**: `form_id`, `selections` (字典：组合框标识 → 选项文本), `identifier_type` ("auto_id"|"title"|"index")
**步骤**:
1. 对每个 (combo_identifier, item_text) in selections：
   - 根据 `identifier_type` 构建定位条件
   - `control_child_window(form_id, control_type="ComboBox", **条件)` → `combo_id`
   - 执行 WF026 选择 `item_text`
   - 验证：`control_selected_text(combo_id)` == item_text
2. 返回所有选择结果
**返回**: `{selections_applied: selections, verified: count}`

### WF079: 设置表单复选框组
**用途**: 批量设置表单中多个复选框的勾选状态。
**参数**: `form_id`, `checkbox_states` (字典：复选框标识 → true/false)
**步骤**:
1. 对每个 (cb_identifier, target_state) in checkbox_states：
   - 查找复选框：`control_child_window(form_id, control_type="CheckBox", title=cb_identifier)` → `cb_id`
   - 执行 WF017 切换到 `target_state`
   - 验证：`control_is_checked(cb_id)` == target_state
2. 返回设置结果
**返回**: `{checkboxes_set: checkbox_states, verified: count}`

### WF080: 提交表单并验证结果
**用途**: 填写表单后点击提交按钮，等待结果，验证提交成功/失败。
**参数**: `form_id`, `submit_button_criteria`, `expected_result` ("success"|"error"|"dialog"), `success_indicator` (可选，成功标志文本), `timeout` (默认 10)
**步骤**:
1. 执行 WF016 点击提交按钮
2. 等待最多 `timeout` 秒：
   - 检查是否出现结果对话框（WF036/WF037）
   - 检查表单区域文本是否包含 `success_indicator`
   - 检查是否出现错误提示（红色文本/错误图标）
3. 根据 `expected_result` 验证：
   - "success"：确认成功标志出现，无错误
   - "error"：确认错误提示出现
   - "dialog"：确认结果对话框出现
4. 返回提交结果和验证信息
**返回**: `{submitted: true, result: expected_result, verified: true|false, details}`

---

## 17. 表格/网格操作 (WF081-WF085)

### WF081: 选择表格行
**用途**: 在 DataGrid/ListView 中选择指定行（按索引或行内容匹配）。
**参数**: `grid_id`, `row_index` 或 `row_match` (行内容匹配文本), `multi` (默认 false), `row_indices` (可选，多选索引列表)
**步骤**:
1. 如果提供 `row_index`：
   - `control_descendants(grid_id, control_type="DataItem")` → 获取所有行
   - 选择第 `row_index` 行：`control_click(row_id)`
2. 如果提供 `row_match`：
   - 遍历所有行，查找包含 `row_match` 文本的行
   - 点击匹配的行
3. 如果 `multi` 且提供 `row_indices`：
   - 按住 Ctrl：`keyboard_key_press(key="VK_CONTROL")`
   - 对每个索引：点击对应行
   - 释放 Ctrl
4. 验证选中行高亮
**返回**: `{row_selected: index|match_text, multi, selected_count}`

### WF082: 获取表格单元格值
**用途**: 获取 DataGrid/ListView 中指定行和列的单元格文本值。
**参数**: `grid_id`, `row_index`, `col_index` 或 `col_name`
**步骤**:
1. `control_descendants(grid_id, control_type="DataItem")` → 获取所有行
2. 选择第 `row_index` 行 → `row_id`
3. `control_descendants(row_id, control_type="Text")` → 获取该行所有单元格
4. 如果提供 `col_name`：先获取表头，找到 `col_name` 对应的列索引
5. 选择第 `col_index` 个单元格 → `cell_id`
6. `control_get_text(cell_id)` → 获取单元格值
**返回**: `{cell_value, row_index, col_index, col_name}`

### WF083: 编辑表格单元格
**用途**: 双击进入单元格编辑模式，输入新值，确认编辑。
**参数**: `grid_id`, `row_index`, `col_index`, `new_value`
**步骤**:
1. 执行 WF082 定位到目标单元格 → `cell_id`
2. `control_double_click(cell_id)` — 双击进入编辑模式
3. 等待 0.3 秒
4. `keyboard_send_keys(keys="^a")` — 全选原有内容
5. `clipboard_set_data(new_value)`
6. `keyboard_send_keys(keys="^v")` — 输入新值
7. `keyboard_send_keys(keys="{ENTER}")` — 确认编辑
8. 等待 0.3 秒
9. 验证：执行 WF082 重新获取单元格值 == new_value
**返回**: `{cell_edited: true, new_value, verified: true}`

### WF084: 表格列排序
**用途**: 点击表头列标题对表格数据进行排序（升序/降序切换）。
**参数**: `grid_id`, `col_name`, `direction` ("asc"|"desc"|"toggle")
**步骤**:
1. 查找表头：`control_child_window(grid_id, control_type="Header")` → `header_id`
2. 查找目标列标题：`control_child_window(header_id, control_type="HeaderItem", title=col_name)` → `col_header_id`
3. 获取当前排序状态（通过排序箭头图标或属性）
4. 根据 `direction` 决定点击次数：
   - "toggle"：点击 1 次
   - "asc"：如果当前不是升序，点击 1-2 次
   - "desc"：如果当前不是降序，点击 1-2 次
5. `control_click(col_header_id)` — 点击排序
6. 等待表格重排
7. 验证排序方向
**返回**: `{column_sorted: col_name, direction, verified}`

### WF085: 表格数据导出
**用途**: 提取表格全部数据，导出为 CSV/JSON 格式文件。
**参数**: `grid_id`, `output_path`, `format` ("csv"|"json"), `include_headers` (默认 true)
**步骤**:
1. 执行 WF053 提取表格全部数据 → `{headers, rows}`
2. 如果 `format="csv"`：
   - 构建 CSV 文本（表头 + 每行用逗号分隔）
   - 写入 `output_path`（UTF-8 with BOM）
3. 如果 `format="json"`：
   - 构建 JSON 数组（每行为字典，key=列名）
   - 写入 `output_path`（缩进 2 空格）
4. 验证文件已保存且数据行数一致
**返回**: `{exported: output_path, format, row_count, col_count, headers}`

---

## 18. 树控件操作 (WF086-WF090)

### WF086: 展开树节点路径
**用途**: 按路径依次展开树控件中的节点（如 "Root\Child\Grandchild"）。
**参数**: `tree_id`, `path` (节点路径，用 `\` 分隔), `expand_all` (默认 false)
**步骤**:
1. 分割路径为节点名列表
2. 当前层级 = tree_id
3. 对每个节点名：
   - 查找子节点：`control_child_window(current_id, control_type="TreeItem", title=节点名)` → `node_id`
   - 检查展开状态：`control_get_expand_state(node_id)`
   - 如果未展开：`control_expand(node_id)`
   - 等待 0.3 秒让子节点加载
   - current_id = node_id
4. 如果 `expand_all`：对最终节点的所有子节点递归展开
5. 返回展开的节点路径
**返回**: `{path_expanded: path, nodes_expanded: count}`

### WF087: 选择树节点
**用途**: 按路径选择树控件中的指定节点。
**参数**: `tree_id`, `path`
**步骤**:
1. 执行 WF086 展开路径（确保目标节点可见）
2. 获取最终节点 → `node_id`
3. `control_click(node_id)` — 点击选择
4. 等待 0.2 秒
5. 验证节点被选中（通过 IsSelected 属性或高亮状态）
**返回**: `{node_selected: path, node_id, verified}`

### WF088: 获取树节点子项
**用途**: 获取指定树节点的所有直接子节点名称和状态。
**参数**: `tree_id`, `path` (可选，根节点为默认)
**步骤**:
1. 如果提供 path：执行 WF086 展开到目标节点 → `node_id`
2. 否则：`node_id = tree_id`
3. `control_children(node_id)` 或 `control_descendants(node_id, control_type="TreeItem")` → 获取子节点
4. 对每个子节点：
   - `control_get_text(child_id)` → 节点名称
   - `control_get_expand_state(child_id)` → 展开状态
   - `control_is_visible(child_id)` → 可见性
5. 返回子节点列表
**返回**: `{children: [{name, expand_state, visible}], count, parent_path}`

### WF089: 树节点重命名
**用途**: 选中树节点，按 F2 进入重命名，输入新名称，确认。
**参数**: `tree_id`, `path`, `new_name`
**步骤**:
1. 执行 WF087 选择目标节点 → `node_id`
2. `keyboard_send_keys(keys="{F2}")` — 进入重命名模式
3. 等待 0.3 秒
4. `keyboard_send_keys(keys="^a")` — 全选原有名称
5. `clipboard_set_data(new_name)`
6. `keyboard_send_keys(keys="^v")` — 输入新名称
7. `keyboard_send_keys(keys="{ENTER}")` — 确认重命名
8. 等待 0.5 秒
9. 验证：`control_get_text(node_id)` == new_name
**返回**: `{node_renamed: true, old_path: path, new_name, verified}`

### WF090: 树节点拖拽排序
**用途**: 将树节点从一个位置拖拽到另一个位置（重新排序或移动）。
**参数**: `tree_id`, `source_path`, `target_path`, `drop_position` ("before"|"after"|"inside")
**步骤**:
1. 执行 WF086 展开源路径和目标路径
2. 获取源节点 → `source_id`，目标节点 → `target_id`
3. 获取两个节点的屏幕坐标：`control_get_rectangle(source_id)`, `control_get_rectangle(target_id)`
4. 根据 `drop_position` 计算放置坐标：
   - "before"：目标节点上方
   - "after"：目标节点下方
   - "inside"：目标节点中心
5. 执行 WF047 拖拽：从源节点中心到目标位置
6. 等待树更新
7. 验证节点已移动到新位置
**返回**: `{node_moved: source_path, target: target_path, position: drop_position, verified}`

---

## 19. 标签页操作 (WF091-WF095)

### WF091: 切换到指定标签页
**用途**: 在 Tab 控件中切换到指定标题或索引的标签页。
**参数**: `tab_id`, `tab_title` 或 `tab_index`
**步骤**:
1. 如果提供 `tab_title`：
   - `control_child_window(tab_id, control_type="TabItem", title=tab_title)` → `tab_item_id`
   - `control_click(tab_item_id)` — 点击切换
2. 如果提供 `tab_index`：
   - `control_children(tab_id)` → 获取所有 TabItem
   - 选择第 `tab_index` 个 → `tab_item_id`
   - `control_click(tab_item_id)`
3. 等待 0.3 秒让标签页内容加载
4. 验证：`tab_get_selected(tab_id)` == 目标标签
**返回**: `{tab_switched: tab_title|tab_index, verified: true}`

### WF092: 获取所有标签页信息
**用途**: 提取 Tab 控件中所有标签页的标题、选中状态、索引。
**参数**: `tab_id`
**步骤**:
1. `control_children(tab_id)` 或 `control_descendants(tab_id, control_type="TabItem")` → 获取所有标签项
2. 对每个标签项：
   - `control_get_text(item_id)` → 标题
   - 检查 IsSelected 属性 → 是否选中
   - 记录索引
3. 返回标签页列表和当前选中索引
**返回**: `{tabs: [{title, index, selected}], count, selected_index}`

### WF093: 关闭标签页
**用途**: 关闭指定标签页（点击关闭按钮或使用快捷键）。
**参数**: `tab_id`, `tab_title` 或 `tab_index`, `close_method` ("button"|"shortcut"|"middle_click")
**步骤**:
1. 执行 WF091 切换到目标标签页
2. 根据 `close_method`：
   - "button"：查找标签页上的关闭按钮（X），点击
   - "shortcut"：`keyboard_send_keys(keys="^w")`（通用关闭标签快捷键）
   - "middle_click"：在标签项上执行中键点击
3. 等待 0.3 秒
4. 验证：执行 WF092，确认目标标签已不在列表中
**返回**: `{tab_closed: tab_title|tab_index, method: close_method, verified}`

### WF094: 新建标签页
**用途**: 在 Tab 控件中新建标签页（点击 "+" 按钮或使用快捷键）。
**参数**: `tab_id`, `method` ("button"|"shortcut"), `new_tab_title` (可选，验证用)
**步骤**:
1. 记录当前标签数量：执行 WF092 → `old_count`
2. 根据 `method`：
   - "button"：查找 "+" 或 "新建标签页" 按钮并点击
   - "shortcut"：`keyboard_send_keys(keys="^t")`
3. 等待 0.5 秒让新标签页创建
4. 验证：执行 WF092，确认标签数量增加
5. 如果提供 `new_tab_title`：验证新标签标题匹配
**返回**: `{tab_created: true, method, new_count, verified}`

### WF095: 遍历所有标签页提取内容
**用途**: 依次切换到每个标签页，提取页面内容/文本，汇总返回。
**参数**: `tab_id`, `extract_func` (提取逻辑描述), `delay` (默认 0.5)
**步骤**:
1. 执行 WF092 获取所有标签页列表
2. 对每个标签页：
   - 执行 WF091 切换到该标签
   - 等待 `delay` 秒让内容加载
   - 执行提取操作（如 WF051 提取全部文本，或 WF053 提取表格数据）
   - 保存提取结果
3. 切换回原始标签页
4. 返回所有标签页的提取结果汇总
**返回**: `{tab_contents: [{title, index, content}], total_tabs}`

---

## 20. 错误恢复与重试 (WF096-WF100)

### WF096: 带重试的点击操作
**用途**: 尝试点击控件，如果失败则等待后重试，最多重试指定次数。
**参数**: `wrapper_id` (父窗口), `control_criteria`, `max_retries` (默认 3), `retry_delay` (默认 1), `click_method` ("click"|"click_input"|"double_click")
**步骤**:
1. 循环 `max_retries` 次：
   - 尝试查找控件：`control_child_window(wrapper_id, **control_criteria)` → `control_id`
   - 如果找到：
     - 检查 `control_is_visible(control_id)` 和 `control_is_enabled(control_id)`
     - 如果可用且可见：
       - 执行点击（根据 `click_method`）
       - 等待 0.3 秒
       - 返回成功
   - 如果失败：等待 `retry_delay` 秒后重试
2. 全部重试失败：返回错误，包含最后一次失败原因
3. 可选：截图记录失败时的界面状态
**返回**: `{clicked: true|false, attempts, last_error, control_found: true|false}`

### WF097: 应用崩溃恢复
**用途**: 检测应用是否崩溃（无响应/进程消失），如果崩溃则重启并恢复状态。
**参数**: `app_id`, `cmd_line` (重启用的命令行), `check_interval` (默认 2), `max_checks` (默认 5), `recovery_actions` (可选，重启后要执行的操作列表)
**步骤**:
1. 循环 `max_checks` 次（每 `check_interval` 秒）：
   - `app_is_process_running(app_id)` → 检查进程是否存在
   - 如果进程消失：应用已崩溃
   - 尝试 `app_top_window(app_id)`：如果超时无响应，可能挂起
2. 如果检测到崩溃/挂起：
   - 尝试 `app_kill(app_id, soft=False)` — 强制终止残留进程
   - 执行 WF001 重新启动应用 → 新 `app_id`
   - 如果提供 `recovery_actions`：依次执行恢复操作（如重新打开文件、恢复窗口位置）
3. 返回恢复结果和新的 app_id
**返回**: `{recovered: true|false, crash_detected: true|false, new_app_id, recovery_actions_executed}`

### WF098: 对话框意外弹出处理
**用途**: 在执行主操作时，监控并自动处理意外弹出的对话框（错误、警告、确认等）。
**参数**: `main_action_wrapper` (主操作描述), `dialog_handlers` (字典：标题关键词 → 按钮文本), `poll_interval` (默认 0.5), `timeout` (默认 30)
**步骤**:
1. 启动主操作
2. 在主操作执行期间，每 `poll_interval` 秒：
   - `enumerate_windows()` → 检查是否有新窗口出现
   - 对每个新窗口，匹配 `dialog_handlers` 中的标题关键词
   - 如果匹配：
     - 记录对话框标题和出现时间
     - 在对话框中查找对应按钮（OK/Yes/No/Cancel/关闭）
     - 点击按钮关闭对话框
     - 记录处理结果
3. 主操作完成后，返回处理过的对话框列表
4. 如果有未处理的对话框，返回警告
**返回**: `{dialogs_handled: [{title, button, timestamp}], unhandled: [...], main_action_completed}`

### WF099: 超时回退策略
**用途**: 尝试主要操作方法，如果超时则回退到备选方法，直到成功或全部失败。
**参数**: `strategies` (有序策略列表，每项为操作描述和超时), `wrapper_id` (操作目标)
**步骤**:
1. 对每个 strategy（按顺序）：
   - 记录开始时间
   - 尝试执行该策略的操作
   - 设置该策略的超时时间
   - 如果在超时内成功完成 → 返回成功，记录使用的策略
   - 如果超时或失败：
     - 记录失败原因
     - 等待短暂间隔（0.5 秒）
     - 继续下一个策略
2. 如果所有策略都失败：
   - 返回失败，包含每个策略的失败原因
   - 截图记录最终界面状态
   - 建议人工干预
3. 返回成功使用的策略和结果
**返回**: `{succeeded: true|false, strategy_used, attempts: [{strategy, result, elapsed}], final_error}`

### WF100: 完整自动化场景执行与验证
**用途**: 按顺序执行一系列工作流步骤，每步验证后再继续，失败时可选择中止或跳过，最终生成执行报告。
**参数**: `workflow_steps` (步骤列表，每步含：工作流ID、参数、验证条件、失败策略 "abort"|"skip"|"retry"), `report_path` (可选，报告保存路径)
**步骤**:
1. 初始化执行报告：`{total_steps, passed: [], failed: [], skipped: [], start_time}`
2. 对每个 step：
   - 记录步骤开始时间
   - 执行对应工作流（传入参数）
   - 执行验证条件（如 WF057 验证文本、WF056 等待窗口等）
   - 如果验证通过：
     - 记录到 passed
     - 继续下一步
   - 如果验证失败：
     - 根据失败策略：
       - "abort"：记录到 failed，中止执行，生成报告
       - "skip"：记录到 skipped，继续下一步
       - "retry"：重试该步骤最多 3 次，仍失败则按 abort 处理
3. 所有步骤完成后：
   - 计算总耗时、通过率
   - 生成详细执行报告（每步的参数、结果、验证状态、耗时）
   - 如果提供 `report_path`：保存报告为 JSON 文件
4. 返回执行报告摘要
**返回**: `{report: {total, passed_count, failed_count, skipped_count, pass_rate, duration, steps: [...]}, report_saved: path}`

---

## 工作流执行说明

所有工作流可通过 `workflow_execute(workflow_id, params)` 工具一键执行：

```
workflow_execute(
    workflow_id="WF011",
    params={
        "wrapper_id": "ctrl_abc123",
        "text": "Hello World",
        "criteria": {"control_type": "Edit"}
    }
)
```

也可以手动按步骤调用对应的基础工具。工作流文件中的步骤描述了精确的工具调用序列和参数传递关系。

**注意**: 部分工作流（如 WF070 系统操作、WF097 应用崩溃恢复）涉及系统级操作，执行前请确认环境安全。
