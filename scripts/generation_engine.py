"""
PyWinAuto MCP — Generation Engine (v3.0)

生成级能力引擎：将 Skill 从"工具封装"提升到"智能生成与自适应编排"。

核心能力：
  1. NL2Workflow   — 自然语言描述 → 可执行工作流步骤
  2. SmartLocator   — 智能元素定位（模糊匹配+语义排序+自动遍历）
  3. AdaptiveExec   — 自适应自愈执行（错误分析+策略调整+自动恢复）
  4. UIAnalyzer     — UI 理解与分析（界面结构描述+可交互元素发现）
  5. ScenarioLib    — 场景模板库（10+ 常见应用场景）
  6. ScriptGen      — 脚本生成器（工作流 → 独立可运行 pywinauto 脚本）

设计原则：
  - 零外部依赖：不依赖 LLM API，纯规则+模板+统计实现
  - 可解释：每个生成结果附带推理过程和置信度
  - 可验证：生成的工作流步骤可通过 workflow_validate_steps 验证
  - 可执行：生成结果可直接通过 workflow_execute_custom 执行
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Re-import wrapper for tool access
import sys
import os
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
import pywinauto_wrapper as pw


# ===========================================================================
# 1. NL2Workflow — 自然语言转工作流生成器
# ===========================================================================

# 动作关键词 → 工具模板映射
_ACTION_TEMPLATES: list[dict[str, Any]] = [
    # 应用生命周期
    {
        "patterns": [r"启动|打开|运行|开始.*(应用|程序|软件)", r"launch|start|open.*app"],
        "tool": "app_start",
        "param_extract": {"cmd_line": r"(?:启动|打开|运行|launch|start)\s+['\"]?([\w.\-]+(?:\.exe)?)",
                           "backend": r"(uia|win32)"},
        "description": "启动应用程序",
        "default_params": {"backend": "uia", "timeout": 10},
        "next_step_hint": "app_top_window",
    },
    {
        "patterns": [r"连接|关联.*(已经|正在)?运行", r"connect.*running"],
        "tool": "app_connect",
        "param_extract": {"title": r"(?:标题|title)[:\s]*['\"]?([^'\"\s,，]+)",
                           "process": r"(\d+)\s*(?:进程|pid|process)"},
        "description": "连接到已运行应用",
        "default_params": {"backend": "uia"},
    },
    {
        "patterns": [r"关闭|退出|终止.*(应用|程序)", r"close|kill|quit.*app"],
        "tool": "app_kill",
        "param_extract": {},
        "description": "关闭应用",
        "requires": ["app_id"],
    },
    # 窗口操作
    {
        "patterns": [r"查找|找到|定位.*窗口", r"find.*window"],
        "tool": "desktop_window",
        "param_extract": {"title": r"(?:标题|title|窗口名)[:\s]*['\"]?([^'\"\s,，]+)",
                           "title_re": r"(?:正则|regex|pattern)[:\s]*['\"]?([^'\"]+)"},
        "description": "查找窗口",
        "default_params": {"backend": "uia"},
    },
    {
        "patterns": [r"聚焦|激活|前置|切换到.*窗口", r"focus|activate.*window"],
        "tool": "control_set_focus",
        "param_extract": {},
        "description": "聚焦窗口",
        "requires": ["wrapper_id"],
    },
    {
        "patterns": [r"最大化|最小化|还原.*窗口", r"maximize|minimize"],
        "tool": "control_maximize",
        "param_extract": {},
        "description": "窗口管理",
        "requires": ["wrapper_id"],
    },
    {
        "patterns": [r"截图|截屏|快照|capture|screenshot"],
        "tool": "control_capture_as_image",
        "param_extract": {"save_path": r"(?:保存|save|路径|path)[:\s]*['\"]?([^'\"\s,，]+)"},
        "description": "截取窗口截图",
        "requires": ["wrapper_id"],
    },
    # 文本输入
    {
        "patterns": [r"输入|键入|填写|写入|打字|type|input|enter.*text"],
        "tool": "safe_type_text",
        "param_extract": {"text": r"(?:输入|键入|填写|写入|type|input)\s+['\"]?([^'\"\n]+?)(?:['\"]?\s*(?:到|在|into|to)|$)"},
        "description": "安全输入文本",
        "requires": ["wrapper_id"],
        "default_params": {"clear_first": True, "use_clipboard": True},
    },
    {
        "patterns": [r"清空|清除|删除.*(内容|文本)", r"clear|delete.*text"],
        "tool": "keyboard_send_keys",
        "param_extract": {},
        "description": "清空文本",
        "fixed_params": {"keys": "^a{DELETE}"},
        "requires": ["wrapper_id"],
    },
    # 点击操作
    {
        "patterns": [r"点击|单击|按下|点一下|click|press.*button"],
        "tool": "safe_click",
        "param_extract": {"button": r"(左键|右键|中键|left|right|middle)"},
        "description": "安全点击",
        "requires": ["wrapper_id"],
        "default_params": {"button": "left", "retries": 3},
    },
    {
        "patterns": [r"双击|double.?click"],
        "tool": "control_double_click",
        "param_extract": {},
        "description": "双击",
        "requires": ["wrapper_id"],
    },
    {
        "patterns": [r"右键|right.?click"],
        "tool": "control_right_click",
        "param_extract": {},
        "description": "右键点击",
        "requires": ["wrapper_id"],
    },
    # 键盘快捷键
    {
        "patterns": [r"快捷键|组合键|按.*(ctrl|alt|shift|win)|press.*(ctrl|alt|shift)"],
        "tool": "keyboard_send_keys",
        "param_extract": {"keys": r"(?:快捷键|组合键|按下|press)\s+['\"]?([^'\"\s,，]+)"},
        "description": "发送快捷键",
    },
    {
        "patterns": [r"保存|save"],
        "tool": "keyboard_send_keys",
        "param_extract": {},
        "description": "保存 (Ctrl+S)",
        "fixed_params": {"keys": "^s"},
    },
    {
        "patterns": [r"复制|copy"],
        "tool": "keyboard_send_keys",
        "param_extract": {},
        "description": "复制 (Ctrl+C)",
        "fixed_params": {"keys": "^c"},
    },
    {
        "patterns": [r"粘贴|paste"],
        "tool": "keyboard_send_keys",
        "param_extract": {},
        "description": "粘贴 (Ctrl+V)",
        "fixed_params": {"keys": "^v"},
    },
    {
        "patterns": [r"全选|select.?all"],
        "tool": "keyboard_send_keys",
        "param_extract": {},
        "description": "全选 (Ctrl+A)",
        "fixed_params": {"keys": "^a"},
    },
    # 菜单操作
    {
        "patterns": [r"菜单|menu|选择.*(菜单项|选项)"],
        "tool": "control_menu_select",
        "param_extract": {"path": r"(?:菜单|menu|路径|path)[:\s]*['\"]?([^'\"]+)"},
        "description": "菜单选择",
        "requires": ["wrapper_id"],
    },
    # 等待
    {
        "patterns": [r"等待|等一会|延时|sleep|wait"],
        "tool": "keyboard_send_keys",
        "param_extract": {},
        "description": "等待（通过延时实现）",
        "fixed_params": {"keys": ""},
        "step_overrides": {"wait": 2.0},
    },
]

# 控件类型关键词映射
_CONTROL_TYPE_KEYWORDS: dict[str, list[str]] = {
    "Button": ["按钮", "btn", "button", "确定", "取消", "提交", "保存", "打开", "关闭"],
    "Edit": ["输入框", "编辑框", "文本框", "edit", "input", "textbox", "搜索框", "地址栏"],
    "ComboBox": ["下拉框", "组合框", "下拉菜单", "combobox", "dropdown", "select"],
    "ListBox": ["列表框", "列表", "listbox", "list"],
    "CheckBox": ["复选框", "勾选框", "checkbox", "check"],
    "RadioButton": ["单选框", "单选按钮", "radiobutton", "radio"],
    "Tab": ["标签页", "选项卡", "tab", "页签"],
    "TreeView": ["树", "树形控件", "treeview", "tree"],
    "DataGrid": ["表格", "数据网格", "datagrid", "grid", "列表视图"],
    "Slider": ["滑块", "滑动条", "slider"],
    "ProgressBar": ["进度条", "progressbar", "progress"],
    "Menu": ["菜单", "menu", "菜单栏"],
    "MenuItem": ["菜单项", "menu item"],
    "Document": ["文档", "document", "内容区"],
    "Pane": ["面板", "pane", "容器"],
    "Window": ["窗口", "window", "对话框", "dialog"],
}


def _extract_params(text: str, extract_map: dict[str, str]) -> dict[str, Any]:
    """从自然语言文本中提取参数值。"""
    params = {}
    for param_name, pattern in extract_map.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Type conversion
            if value.isdigit():
                value = int(value)
            elif value.lower() in ("true", "false"):
                value = value.lower() == "true"
            params[param_name] = value
    return params


def _detect_control_type(text: str) -> Optional[str]:
    """从文本中检测控件类型。"""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for ctrl_type, keywords in _CONTROL_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                scores[ctrl_type] = scores.get(ctrl_type, 0) + len(kw)
    if scores:
        return max(scores, key=scores.get)
    return None


def _detect_target_element(text: str) -> dict[str, Any]:
    """从文本中检测目标元素的定位信息。"""
    result: dict[str, Any] = {}

    # 控件类型
    ctrl_type = _detect_control_type(text)
    if ctrl_type:
        result["control_type"] = ctrl_type

    # 标题/名称（引号中的内容）
    title_match = re.search(r"['\"]([^'\"]{2,40})['\"]", text)
    if title_match:
        result["title"] = title_match.group(1)

    # auto_id（常见模式）
    auto_id_match = re.search(r"(?:id|auto_id|automation_id)[:\s]*['\"]?([\w]+)", text, re.IGNORECASE)
    if auto_id_match:
        result["auto_id"] = auto_id_match.group(1)

    return result


def generate_workflow(description: str, context: Optional[dict[str, Any]] = None,
                       auto_execute: bool = False) -> dict[str, Any]:
    """根据自然语言描述生成可执行工作流。

    Args:
        description: 自然语言任务描述，如"启动记事本，输入Hello World，然后保存"
        context: 已有上下文（如 app_id, wrapper_id）
        auto_execute: 如果为 True，生成后立即执行

    Returns:
        Dict with generated steps, reasoning, confidence, and optional execution result

    示例:
        generate_workflow("启动记事本，输入Hello，然后点击保存按钮")
        → 生成 4 步工作流并返回推理过程
    """
    if not description or not description.strip():
        return {"status": "error", "error": "描述不能为空"}

    context = context or {}
    start_time = time.time()
    reasoning: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []

    # 分句处理（支持中英文标点）
    sentences = re.split(r"[，,。.；;！!？?\n]+", description)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        sentences = [description.strip()]

    var_counter = {"app_id": 0, "wrapper_id": 0, "edit_id": 0, "btn_id": 0}

    for sent_idx, sentence in enumerate(sentences):
        matched = False
        best_match: Optional[dict[str, Any]] = None
        best_score = 0

        # 匹配动作模板
        for template in _ACTION_TEMPLATES:
            for pattern in template["patterns"]:
                if re.search(pattern, sentence, re.IGNORECASE):
                    score = len(pattern)
                    if score > best_score:
                        best_score = score
                        best_match = template
                    break

        if best_match:
            matched = True
            tool = best_match["tool"]
            step: dict[str, Any] = {
                "tool": tool,
                "description": best_match["description"],
                "params": {},
            }

            # 提取参数
            extracted = _extract_params(sentence, best_match.get("param_extract", {}))
            step["params"].update(extracted)

            # 固定参数
            if "fixed_params" in best_match:
                step["params"].update(best_match["fixed_params"])

            # 默认参数
            if "default_params" in best_match:
                for k, v in best_match["default_params"].items():
                    if k not in step["params"]:
                        step["params"][k] = v

            # 步骤覆盖（如 wait）
            if "step_overrides" in best_match:
                step.update(best_match["step_overrides"])

            # 处理需要的会话变量
            requires = best_match.get("requires", [])
            for req in requires:
                if req in context:
                    step["params"][req] = context[req]
                elif req == "wrapper_id" and steps:
                    # 尝试从上一步的 output_key 获取
                    for prev in reversed(steps):
                        if prev.get("output_key") == "wrapper_id":
                            step["params"]["wrapper_id"] = "$wrapper_id$"
                            break

            # 设置 output_key 用于变量传递
            if tool == "app_start":
                step["output_key"] = "app_id"
                step["wait"] = step.get("wait", 1.0)
                context["app_id"] = "$app_id$"
                # 自动添加获取顶层窗口
                steps.append(step)
                reasoning.append({
                    "sentence": sentence,
                    "action": "检测到启动应用",
                    "tool": tool,
                    "params": list(step["params"].keys()),
                })
                # 添加 app_top_window
                top_step = {
                    "tool": "app_top_window",
                    "description": "获取应用主窗口",
                    "params": {"app_id": "$app_id$"},
                    "output_key": "wrapper_id",
                    "wait": 0.5,
                }
                steps.append(top_step)
                context["wrapper_id"] = "$wrapper_id$"
                reasoning.append({
                    "sentence": "(自动)",
                    "action": "自动获取主窗口",
                    "tool": "app_top_window",
                })
                continue

            elif tool in ("safe_click", "control_double_click", "control_right_click"):
                # 检测目标元素，自动添加查找步骤
                target = _detect_target_element(sentence)
                if target and "wrapper_id" in context:
                    find_step = {
                        "tool": "control_child_window",
                        "description": f"查找目标控件: {target.get('control_type', target.get('title', 'unknown'))}",
                        "params": {"wrapper_id": "$wrapper_id$"},
                        "output_key": "target_id",
                        "wait": 0.3,
                    }
                    find_step["params"].update(target)
                    steps.append(find_step)
                    step["params"]["wrapper_id"] = "$target_id$"
                    reasoning.append({
                        "sentence": sentence,
                        "action": "检测到点击操作，自动查找目标控件",
                        "target": target,
                    })

            elif tool == "safe_type_text":
                if "wrapper_id" not in step["params"] and "wrapper_id" in context:
                    step["params"]["wrapper_id"] = "$wrapper_id$"

            steps.append(step)
            reasoning.append({
                "sentence": sentence,
                "action": best_match["description"],
                "tool": tool,
                "params": list(step["params"].keys()),
                "confidence": min(0.95, 0.5 + best_score / 100),
            })

        if not matched:
            # 未匹配到动作，记录为待处理
            reasoning.append({
                "sentence": sentence,
                "action": "未识别的操作",
                "tool": None,
                "note": "该句未匹配到预定义动作模板，已跳过",
            })

    # 验证生成的步骤
    validation = pw.workflow_validate_steps(steps) if steps else {"valid": True, "errors": []}

    # 计算置信度
    matched_count = sum(1 for r in reasoning if r.get("tool"))
    confidence = round(min(1.0, matched_count / max(len(sentences), 1) * 0.9), 2)

    result = {
        "status": "success",
        "description": description,
        "steps": steps,
        "step_count": len(steps),
        "reasoning": reasoning,
        "confidence": confidence,
        "validation": validation,
        "elapsed_seconds": round(time.time() - start_time, 3),
    }

    # 自动执行
    if auto_execute and steps and validation["valid"]:
        exec_result = pw.workflow_execute_custom(steps, name="nl_generated")
        result["execution"] = exec_result
        result["execution_status"] = exec_result.get("status", "unknown")

    return result


def generate_and_execute(description: str, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """根据自然语言描述生成工作流并立即执行。"""
    return generate_workflow(description, context=context, auto_execute=True)


# ===========================================================================
# 2. SmartLocator — 智能元素定位器
# ===========================================================================

def _fuzzy_match_score(text: str, pattern: str) -> float:
    """计算模糊匹配得分（0-1）。"""
    if not text or not pattern:
        return 0.0
    text_lower = text.lower()
    pattern_lower = pattern.lower()

    # 精确匹配
    if text_lower == pattern_lower:
        return 1.0
    # 包含匹配
    if pattern_lower in text_lower:
        return 0.8 + 0.2 * (len(pattern_lower) / len(text_lower))
    if text_lower in pattern_lower:
        return 0.7
    # 首字母缩写匹配
    text_initials = "".join(w[0] for w in re.findall(r"\w+", text_lower))
    if pattern_lower == text_initials:
        return 0.6
    # 字符级相似度（Levenshtein 近似）
    m, n = len(text_lower), len(pattern_lower)
    if m == 0 or n == 0:
        return 0.0
    # 简单的公共字符比例
    common = sum(1 for c in pattern_lower if c in text_lower)
    return round(common / max(m, n) * 0.5, 3)


def smart_find(description: str, wrapper_id: Optional[str] = None,
                backend: str = "uia", max_results: int = 10,
                search_depth: int = 3) -> dict[str, Any]:
    """根据自然语言描述智能查找控件元素。

    Args:
        description: 元素描述，如"确定按钮"、"用户名输入框"、"左侧的下拉框"
        wrapper_id: 父容器 wrapper_id（None 则搜索整个桌面）
        backend: 'uia' or 'win32'
        max_results: 最大返回结果数
        search_depth: 控件树搜索深度

    Returns:
        Dict with matched elements sorted by relevance score

    示例:
        smart_find("确定按钮", wrapper_id="ctrl_xxx")
        → 返回匹配的按钮元素，按相关性排序
    """
    start_time = time.time()
    pw._validate_backend(backend)

    # 解析描述中的控件类型和关键词
    ctrl_type = _detect_control_type(description)
    target_info = _detect_target_element(description)

    # 提取搜索关键词（去掉控件类型词）
    keywords = description
    for kw_list in _CONTROL_TYPE_KEYWORDS.values():
        for kw in kw_list:
            keywords = re.sub(re.escape(kw), "", keywords, flags=re.IGNORECASE)
    keywords = [k.strip() for k in re.split(r"[\s,，的]+", keywords) if len(k.strip()) > 1]

    # 获取候选元素
    candidates: list[dict[str, Any]] = []

    try:
        if wrapper_id:
            wrapper = pw._get_wrapper(wrapper_id)
            # 获取所有后代
            try:
                descendants = wrapper.descendants()
            except Exception:
                descendants = wrapper.children()

            for elem in descendants[:500]:
                try:
                    info = pw._wrapper_info(elem)
                    info["_element"] = elem
                    candidates.append(info)
                except Exception:
                    continue
        else:
            # 搜索桌面
            from pywinauto import Desktop
            desktop = Desktop(backend=backend)
            for win in desktop.windows()[:20]:
                try:
                    info = pw._wrapper_info(win)
                    info["_element"] = win
                    candidates.append(info)
                    # 子元素
                    try:
                        for child in win.descendants()[:100]:
                            try:
                                cinfo = pw._wrapper_info(child)
                                cinfo["_element"] = child
                                candidates.append(cinfo)
                            except Exception:
                                continue
                    except Exception:
                        continue
                except Exception:
                    continue
    except Exception as e:
        return {"status": "error", "error": str(e), "candidates_found": 0}

    # 评分排序
    scored: list[dict[str, Any]] = []
    for cand in candidates:
        score = 0.0
        reasons = []

        # 控件类型匹配
        cand_type = cand.get("control_type", "")
        if ctrl_type and cand_type:
            if ctrl_type.lower() in cand_type.lower() or cand_type.lower() in ctrl_type.lower():
                score += 0.4
                reasons.append(f"控件类型匹配({ctrl_type})")

        # 标题/名称匹配
        cand_text = cand.get("text", "") or cand.get("name", "")
        if cand_text:
            for kw in keywords:
                kw_score = _fuzzy_match_score(cand_text, kw)
                if kw_score > 0:
                    score += kw_score * 0.3
                    reasons.append(f"关键词'{kw}'匹配({kw_score:.2f})")

            # 标题精确匹配
            if target_info.get("title") and target_info["title"].lower() == cand_text.lower():
                score += 0.3
                reasons.append("标题精确匹配")

        # auto_id 匹配
        if target_info.get("auto_id") and cand.get("automation_id"):
            if target_info["auto_id"].lower() == cand["automation_id"].lower():
                score += 0.4
                reasons.append("auto_id 精确匹配")

        # 可见性和可用性加分
        if cand.get("is_visible"):
            score += 0.05
        if cand.get("is_enabled"):
            score += 0.05

        if score > 0.1:  # 阈值过滤
            scored.append({
                "score": round(score, 3),
                "reasons": reasons,
                "info": {k: v for k, v in cand.items() if k != "_element"},
                "_element": cand.get("_element"),
            })

    # 排序并限制数量
    scored.sort(key=lambda x: x["score"], reverse=True)
    scored = scored[:max_results]

    # 注册最佳匹配为 wrapper 会话
    best_wrapper_id = None
    if scored:
        best = scored[0]["_element"]
        if best is not None:
            try:
                best_wrapper_id = pw._register_wrapper(best)
            except Exception:
                pass

    return {
        "status": "success",
        "description": description,
        "detected_control_type": ctrl_type,
        "detected_keywords": keywords,
        "candidates_scanned": len(candidates),
        "matches_found": len(scored),
        "best_match_wrapper_id": best_wrapper_id,
        "matches": [
            {
                "score": m["score"],
                "reasons": m["reasons"],
                "text": m["info"].get("text", ""),
                "control_type": m["info"].get("control_type", ""),
                "class_name": m["info"].get("class_name", ""),
                "automation_id": m["info"].get("automation_id", ""),
                "is_visible": m["info"].get("is_visible"),
                "is_enabled": m["info"].get("is_enabled"),
                "rect": m["info"].get("rect"),
            }
            for m in scored
        ],
        "elapsed_seconds": round(time.time() - start_time, 3),
    }


# ===========================================================================
# 3. AdaptiveExec — 自适应自愈执行引擎
# ===========================================================================

# 错误恢复策略库
_RECOVERY_STRATEGIES: dict[str, list[dict[str, Any]]] = {
    "element_not_found": [
        {"name": "扩大搜索范围", "action": "remove_filter", "params": ["title", "auto_id"]},
        {"name": "增加超时等待", "action": "add_wait", "params": {"wait": 2.0}},
        {"name": "切换后端", "action": "switch_backend", "params": {"backend": "win32"}},
        {"name": "使用智能定位", "action": "use_smart_find", "params": {}},
    ],
    "timeout": [
        {"name": "增加超时时间", "action": "increase_timeout", "params": {"multiplier": 2.0}},
        {"name": "降低操作速度", "action": "slow_down", "params": {}},
        {"name": "检查应用响应", "action": "check_cpu", "params": {}},
    ],
    "element_disabled": [
        {"name": "等待前置条件", "action": "add_wait", "params": {"wait": 3.0}},
        {"name": "检查依赖字段", "action": "check_dependencies", "params": {}},
    ],
    "element_not_visible": [
        {"name": "滚动到可见区域", "action": "scroll_into_view", "params": {}},
        {"name": "展开父容器", "action": "expand_parent", "params": {}},
        {"name": "切换标签页", "action": "switch_tab", "params": {}},
    ],
    "permission_denied": [
        {"name": "提示需要管理员权限", "action": "notify", "params": {"message": "需要以管理员身份运行"}},
    ],
    "session_expired": [
        {"name": "重新连接应用", "action": "reconnect", "params": {}},
        {"name": "重新启动应用", "action": "restart_app", "params": {}},
    ],
}


def adaptive_execute(steps: list[dict[str, Any]], max_retries_per_step: int = 3,
                     auto_recover: bool = True, stop_on_error: bool = True,
                     name: str = "adaptive_workflow") -> dict[str, Any]:
    """自适应自愈执行引擎：执行工作流步骤，失败时自动分析并尝试恢复。

    Args:
        steps: 工作流步骤列表
        max_retries_per_step: 每步最大重试次数
        auto_recover: 是否启用自动恢复策略
        stop_on_error: 恢复失败后是否停止
        name: 工作流名称

    Returns:
        Dict with execution results, recovery actions, and final status
    """
    start_time = time.time()
    context: dict[str, Any] = {}
    step_results = []
    recovery_log: list[dict[str, Any]] = []
    total_recoveries = 0

    for i, step in enumerate(steps):
        tool_name = step.get("tool", "unknown")
        description = step.get("description", tool_name)
        step_recoveries = 0
        step_success = False
        last_error = None

        for attempt in range(max_retries_per_step + 1):
            try:
                result = pw._execute_step(step, context, step_index=i + 1)

                if result["status"] == "error":
                    raise RuntimeError(result.get("error", "Unknown error"))

                step_results.append(result)
                step_success = True
                break

            except Exception as e:
                last_error = e
                if attempt < max_retries_per_step and auto_recover:
                    # 分析错误并尝试恢复
                    classified = pw._classify_error(e)
                    category = classified.get("category", "unknown")
                    strategies = _RECOVERY_STRATEGIES.get(category, [])

                    if strategies and step_recoveries < len(strategies):
                        strategy = strategies[step_recoveries]
                        recovery_log.append({
                            "step": i + 1,
                            "tool": tool_name,
                            "attempt": attempt + 1,
                            "error": str(e),
                            "error_category": category,
                            "strategy": strategy["name"],
                            "action": strategy["action"],
                        })
                        step_recoveries += 1
                        total_recoveries += 1

                        # 应用恢复策略
                        if strategy["action"] == "add_wait":
                            wait_time = strategy["params"].get("wait", 2.0)
                            time.sleep(wait_time)
                        elif strategy["action"] == "increase_timeout":
                            step["timeout"] = step.get("timeout", 10) * strategy["params"].get("multiplier", 2.0)
                        elif strategy["action"] == "slow_down":
                            pw.timings_slow()
                        elif strategy["action"] == "use_smart_find":
                            # 尝试用 smart_find 重新定位
                            pass  # 需要更多上下文，暂跳过
                        else:
                            # 默认策略：等待后重试
                            time.sleep(1.0)
                    else:
                        time.sleep(0.5 * (attempt + 1))
                else:
                    break

        if not step_success:
            error_result = {
                "status": "error",
                "tool": tool_name,
                "description": description,
                "error": str(last_error) if last_error else "Unknown",
                "error_type": type(last_error).__name__ if last_error else "Unknown",
                "attempts": max_retries_per_step + 1,
                "recoveries_attempted": step_recoveries,
            }
            step_results.append(error_result)

            if stop_on_error:
                break

    elapsed = time.time() - start_time
    succeeded = sum(1 for r in step_results if r.get("status") == "success")
    errors = sum(1 for r in step_results if r.get("status") == "error")
    skipped = sum(1 for r in step_results if r.get("status") == "skipped")

    if errors == 0:
        status = "success"
    elif succeeded > 0:
        status = "partial"
    else:
        status = "failed"

    return {
        "status": status,
        "name": name,
        "total_steps": len(steps),
        "steps_completed": len(step_results),
        "succeeded": succeeded,
        "errors": errors,
        "skipped": skipped,
        "total_recoveries": total_recoveries,
        "recovery_log": recovery_log,
        "step_results": step_results,
        "context": {k: v for k, v in context.items() if not k.startswith("_")},
        "elapsed_seconds": round(elapsed, 3),
    }


# ===========================================================================
# 4. UIAnalyzer — UI 理解与分析器
# ===========================================================================

def analyze_ui(wrapper_id: Optional[str] = None, depth: int = 3,
               include_properties: bool = True) -> dict[str, Any]:
    """分析界面结构，生成结构化的 UI 描述。

    Args:
        wrapper_id: 窗口/控件 wrapper_id（None 则分析整个桌面）
        depth: 控件树分析深度
        include_properties: 是否包含详细属性

    Returns:
        Dict with UI structure summary, element counts, interactive elements, and description
    """
    start_time = time.time()

    try:
        if wrapper_id:
            root = pw._get_wrapper(wrapper_id)
            root_info = pw._wrapper_info(root)
        else:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            root = desktop
            root_info = {"class_name": "Desktop", "text": "Desktop", "control_type": "Desktop"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

    # 遍历控件树
    all_elements: list[dict[str, Any]] = []
    interactive_types = {"Button", "Edit", "ComboBox", "ListBox", "CheckBox",
                         "RadioButton", "Tab", "TreeView", "DataGrid", "Slider",
                         "MenuItem", "Document", "Hyperlink", "Spinner", "Custom"}

    def _traverse(element, current_depth, max_depth):
        if current_depth > max_depth:
            return
        try:
            info = pw._wrapper_info(element)
            info["depth"] = current_depth
            all_elements.append(info)
        except Exception:
            return
        try:
            for child in element.children():
                _traverse(child, current_depth + 1, max_depth)
        except Exception:
            pass

    if wrapper_id:
        _traverse(root, 0, depth)
    else:
        for win in root.windows()[:15]:
            _traverse(win, 0, depth)

    # 统计
    from collections import Counter
    type_counts = Counter(e.get("control_type", "Unknown") for e in all_elements)
    visible_count = sum(1 for e in all_elements if e.get("is_visible"))
    enabled_count = sum(1 for e in all_elements if e.get("is_enabled"))

    # 可交互元素
    interactive = [
        e for e in all_elements
        if e.get("control_type", "") in interactive_types
        and e.get("is_visible", False)
    ]

    # 生成自然语言描述
    description_parts = [
        f"界面包含 {len(all_elements)} 个控件元素（深度 {depth}）",
        f"其中 {visible_count} 个可见，{enabled_count} 个可用",
        f"可交互元素 {len(interactive)} 个",
    ]

    if type_counts:
        top_types = type_counts.most_common(5)
        type_desc = "、".join(f"{t}({c})" for t, c in top_types)
        description_parts.append(f"主要控件类型: {type_desc}")

    # 有文本的元素
    named_elements = [e for e in interactive if e.get("text")]
    if named_elements:
        names = [e["text"][:20] for e in named_elements[:10]]
        description_parts.append(f"命名控件: {'、'.join(names)}")

    return {
        "status": "success",
        "root": root_info,
        "summary": {
            "total_elements": len(all_elements),
            "visible": visible_count,
            "enabled": enabled_count,
            "interactive_count": len(interactive),
            "depth_analyzed": depth,
            "type_distribution": dict(type_counts.most_common()),
        },
        "interactive_elements": [
            {
                "text": e.get("text", ""),
                "control_type": e.get("control_type", ""),
                "class_name": e.get("class_name", ""),
                "automation_id": e.get("automation_id", ""),
                "is_enabled": e.get("is_enabled"),
                "rect": e.get("rect"),
                "depth": e.get("depth"),
            }
            for e in interactive[:50]
        ],
        "description": "；".join(description_parts),
        "elapsed_seconds": round(time.time() - start_time, 3),
    }


def describe_element(wrapper_id: str) -> dict[str, Any]:
    """生成控件的自然语言描述。

    Args:
        wrapper_id: 控件 wrapper_id

    Returns:
        Dict with element properties and natural language description
    """
    try:
        wrapper = pw._get_wrapper(wrapper_id)
        info = pw._wrapper_info(wrapper)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    parts = []

    # 类型
    ctrl_type = info.get("control_type", info.get("friendly_class_name", "Unknown"))
    parts.append(f"这是一个 {ctrl_type} 控件")

    # 名称/文本
    text = info.get("text", "")
    if text:
        parts.append(f"显示文本为 '{text[:50]}'")

    # 类名
    class_name = info.get("class_name", "")
    if class_name:
        parts.append(f"窗口类名为 {class_name}")

    # auto_id
    auto_id = info.get("automation_id", "")
    if auto_id:
        parts.append(f"自动化ID为 {auto_id}")

    # 状态
    states = []
    if info.get("is_visible"):
        states.append("可见")
    else:
        states.append("不可见")
    if info.get("is_enabled"):
        states.append("可用")
    else:
        states.append("不可用")
    parts.append(f"当前状态: {'、'.join(states)}")

    # 位置
    rect = info.get("rect", {})
    if rect:
        parts.append(f"位置: ({rect.get('left', 0)}, {rect.get('top', 0)}) "
                     f"大小: {rect.get('width', 0)}x{rect.get('height', 0)}")

    # 可用方法
    try:
        methods = [m for m in dir(wrapper) if not m.startswith("_") and callable(getattr(wrapper, m))]
        common_methods = [m for m in methods if m in (
            "click", "double_click", "right_click", "type_keys", "set_text",
            "select", "check", "uncheck", "expand", "collapse", "set_focus",
            "close", "maximize", "minimize", "scroll", "drag_mouse",
            "menu_select", "capture_as_image", "get_value", "set_value"
        )]
        if common_methods:
            parts.append(f"支持操作: {'、'.join(common_methods[:10])}")
    except Exception:
        pass

    return {
        "status": "success",
        "wrapper_id": wrapper_id,
        "properties": info,
        "description": "；".join(parts),
        "available_actions": common_methods if 'common_methods' in dir() else [],
    }


def find_interactive_elements(wrapper_id: Optional[str] = None,
                                control_type: Optional[str] = None,
                                only_visible: bool = True,
                                only_enabled: bool = True) -> dict[str, Any]:
    """查找界面中所有可交互元素。

    Args:
        wrapper_id: 父容器（None 则搜索桌面）
        control_type: 过滤控件类型
        only_visible: 只返回可见元素
        only_enabled: 只返回可用元素

    Returns:
        Dict with list of interactive elements
    """
    analysis = analyze_ui(wrapper_id, depth=4)
    if analysis["status"] != "success":
        return analysis

    elements = analysis.get("interactive_elements", [])

    if control_type:
        elements = [e for e in elements if control_type.lower() in e.get("control_type", "").lower()]
    if only_visible:
        elements = [e for e in elements if e.get("is_visible")]
    if only_enabled:
        elements = [e for e in elements if e.get("is_enabled")]

    return {
        "status": "success",
        "count": len(elements),
        "filter": {"control_type": control_type, "only_visible": only_visible, "only_enabled": only_enabled},
        "elements": elements,
    }


# ===========================================================================
# 5. ScenarioLib — 场景模板库
# ===========================================================================

SCENARIOS: dict[str, dict[str, Any]] = {
    "notepad_basic": {
        "name": "记事本基础操作",
        "description": "启动记事本，输入文本，保存文件",
        "category": "文本编辑",
        "params": [
            {"name": "text", "type": "string", "default": "Hello, World!", "description": "要输入的文本"},
            {"name": "save_path", "type": "string", "default": "", "description": "保存路径（空则不保存）"},
        ],
        "steps": [
            {"tool": "app_start", "params": {"cmd_line": "notepad.exe", "backend": "uia"}, "output_key": "app_id", "wait": 1.0, "description": "启动记事本"},
            {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "wrapper_id", "wait": 0.5, "description": "获取记事本窗口"},
            {"tool": "control_child_window", "params": {"wrapper_id": "$wrapper_id$", "control_type": "Document"}, "output_key": "edit_id", "wait": 0.3, "description": "定位文本编辑区"},
            {"tool": "safe_type_text", "params": {"wrapper_id": "$edit_id$", "text": "$text$", "clear_first": True}, "description": "输入文本"},
        ],
    },
    "calculator_math": {
        "name": "计算器数学运算",
        "description": "启动计算器，执行基本数学运算",
        "category": "系统工具",
        "params": [
            {"name": "expression", "type": "string", "default": "123+456", "description": "数学表达式（仅支持数字和+-*/）"},
        ],
        "steps": [
            {"tool": "app_start", "params": {"cmd_line": "calc.exe", "backend": "uia"}, "output_key": "app_id", "wait": 1.5, "description": "启动计算器"},
            {"tool": "app_top_window", "params": {"app_id": "$app_id$"}, "output_key": "wrapper_id", "wait": 0.5, "description": "获取计算器窗口"},
            {"tool": "keyboard_send_keys", "params": {"keys": "$expression$"}, "wait": 0.3, "description": "输入表达式"},
            {"tool": "keyboard_send_keys", "params": {"keys": "{ENTER}"}, "wait": 0.5, "description": "按等号计算"},
        ],
    },
    "browser_navigate": {
        "name": "浏览器导航",
        "description": "在已打开的浏览器中导航到指定URL",
        "category": "浏览器",
        "params": [
            {"name": "url", "type": "string", "default": "https://www.example.com", "description": "目标URL"},
            {"name": "browser_title", "type": "string", "default": "", "description": "浏览器窗口标题关键词"},
        ],
        "steps": [
            {"tool": "desktop_window", "params": {"backend": "uia", "title_re": "$browser_title$"}, "output_key": "browser_id", "wait": 0.5, "description": "查找浏览器窗口"},
            {"tool": "control_set_focus", "params": {"wrapper_id": "$browser_id$"}, "description": "聚焦浏览器"},
            {"tool": "keyboard_send_keys", "params": {"keys": "^l"}, "wait": 0.3, "description": "聚焦地址栏"},
            {"tool": "clipboard_set_data", "params": {"text": "$url$"}, "description": "复制URL到剪贴板"},
            {"tool": "keyboard_send_keys", "params": {"keys": "^v"}, "wait": 0.2, "description": "粘贴URL"},
            {"tool": "keyboard_send_keys", "params": {"keys": "{ENTER}"}, "wait": 1.0, "description": "导航"},
        ],
    },
    "form_fill": {
        "name": "表单填写",
        "description": "按标签定位并填写表单字段",
        "category": "表单操作",
        "params": [
            {"name": "form_wrapper_id", "type": "string", "required": True, "description": "表单容器 wrapper_id"},
            {"name": "fields", "type": "object", "default": {}, "description": "字段名到值的映射"},
        ],
        "steps": [
            {"tool": "find_interactive_elements", "params": {"wrapper_id": "$form_wrapper_id$", "control_type": "Edit"}, "output_key": "edit_fields", "description": "查找所有输入框"},
        ],
    },
    "dialog_confirm": {
        "name": "对话框确认",
        "description": "自动检测并点击确认对话框的确定按钮",
        "category": "对话框处理",
        "params": [
            {"name": "title_re", "type": "string", "default": ".*", "description": "对话框标题正则"},
            {"name": "button_text", "type": "string", "default": "确定", "description": "按钮文本"},
        ],
        "steps": [
            {"tool": "desktop_window", "params": {"backend": "uia", "title_re": "$title_re$"}, "output_key": "dialog_id", "wait": 0.5, "description": "查找对话框"},
            {"tool": "control_child_window", "params": {"wrapper_id": "$dialog_id$", "control_type": "Button", "title": "$button_text$"}, "output_key": "btn_id", "wait": 0.3, "description": "查找确定按钮"},
            {"tool": "safe_click", "params": {"wrapper_id": "$btn_id$"}, "description": "点击确定"},
        ],
    },
    "screenshot_capture": {
        "name": "窗口截图",
        "description": "截取指定窗口并保存为图片",
        "category": "截图捕获",
        "params": [
            {"name": "window_title", "type": "string", "required": True, "description": "窗口标题"},
            {"name": "save_path", "type": "string", "default": "screenshot.png", "description": "保存路径"},
        ],
        "steps": [
            {"tool": "desktop_window", "params": {"backend": "uia", "title": "$window_title$"}, "output_key": "win_id", "wait": 0.5, "description": "查找窗口"},
            {"tool": "control_set_focus", "params": {"wrapper_id": "$win_id$"}, "wait": 0.3, "description": "聚焦窗口"},
            {"tool": "control_capture_as_image", "params": {"wrapper_id": "$win_id$", "save_path": "$save_path$"}, "description": "截图并保存"},
        ],
    },
    "menu_navigation": {
        "name": "菜单导航",
        "description": "通过菜单栏路径选择菜单项",
        "category": "菜单操作",
        "params": [
            {"name": "wrapper_id", "type": "string", "required": True, "description": "窗口 wrapper_id"},
            {"name": "menu_path", "type": "string", "default": "File->Save", "description": "菜单路径，用->分隔"},
        ],
        "steps": [
            {"tool": "control_set_focus", "params": {"wrapper_id": "$wrapper_id$"}, "description": "聚焦窗口"},
            {"tool": "control_menu_select", "params": {"wrapper_id": "$wrapper_id$", "path": "$menu_path$"}, "wait": 0.5, "description": "选择菜单项"},
        ],
    },
    "clipboard_operations": {
        "name": "剪贴板操作",
        "description": "设置剪贴板内容并粘贴到目标控件",
        "category": "剪贴板",
        "params": [
            {"name": "text", "type": "string", "default": "", "description": "要复制的文本"},
            {"name": "target_wrapper_id", "type": "string", "default": "", "description": "目标控件 wrapper_id"},
        ],
        "steps": [
            {"tool": "clipboard_set_data", "params": {"text": "$text$"}, "description": "设置剪贴板"},
            {"tool": "control_set_focus", "params": {"wrapper_id": "$target_wrapper_id$"}, "description": "聚焦目标"},
            {"tool": "keyboard_send_keys", "params": {"keys": "^v"}, "wait": 0.2, "description": "粘贴"},
        ],
    },
    "window_management": {
        "name": "窗口管理",
        "description": "查找、聚焦、最大化/最小化窗口",
        "category": "窗口管理",
        "params": [
            {"name": "title", "type": "string", "required": True, "description": "窗口标题"},
            {"name": "action", "type": "string", "default": "focus", "description": "操作: focus/maximize/minimize/close"},
        ],
        "steps": [
            {"tool": "desktop_window", "params": {"backend": "uia", "title": "$title$"}, "output_key": "win_id", "wait": 0.5, "description": "查找窗口"},
        ],
    },
    "system_info": {
        "name": "系统信息收集",
        "description": "收集系统信息、窗口列表、运行状态",
        "category": "系统操作",
        "params": [],
        "steps": [
            {"tool": "sysinfo_os_arch", "params": {}, "output_key": "os_arch", "description": "获取系统架构"},
            {"tool": "enumerate_windows", "params": {"backend": "uia"}, "output_key": "windows", "description": "枚举所有窗口"},
            {"tool": "list_sessions", "params": {}, "output_key": "sessions", "description": "列出活跃会话"},
            {"tool": "health_check", "params": {}, "output_key": "health", "description": "健康检查"},
        ],
    },
}


def list_scenarios(category: Optional[str] = None) -> dict[str, Any]:
    """列出所有可用场景模板。"""
    scenarios = []
    for sid, sc in SCENARIOS.items():
        if category and sc["category"] != category:
            continue
        scenarios.append({
            "id": sid,
            "name": sc["name"],
            "description": sc["description"],
            "category": sc["category"],
            "param_count": len(sc["params"]),
            "step_count": len(sc["steps"]),
        })
    return {"count": len(scenarios), "scenarios": scenarios}


def apply_scenario(scenario_id: str, params: Optional[dict[str, Any]] = None,
                   auto_execute: bool = False) -> dict[str, Any]:
    """应用场景模板，生成工作流步骤并可选执行。

    Args:
        scenario_id: 场景 ID（如 'notepad_basic'）
        params: 场景参数
        auto_execute: 是否立即执行

    Returns:
        Dict with generated steps and optional execution result
    """
    if scenario_id not in SCENARIOS:
        available = list(SCENARIOS.keys())
        return {"status": "error", "error": f"Unknown scenario: {scenario_id}",
                "available": available}

    scenario = SCENARIOS[scenario_id]
    params = params or {}

    # 填充默认参数
    for pdef in scenario["params"]:
        if pdef["name"] not in params and "default" in pdef:
            params[pdef["name"]] = pdef["default"]

    # 生成步骤（深拷贝）
    import copy
    steps = copy.deepcopy(scenario["steps"])

    # 替换参数占位符
    for step in steps:
        for key, val in step.get("params", {}).items():
            if isinstance(val, str) and val.startswith("$") and val.endswith("$"):
                param_name = val[1:-1]
                if param_name in params:
                    step["params"][key] = params[param_name]

    result = {
        "status": "success",
        "scenario_id": scenario_id,
        "scenario_name": scenario["name"],
        "description": scenario["description"],
        "params": params,
        "steps": steps,
        "step_count": len(steps),
        "validation": pw.workflow_validate_steps(steps),
    }

    if auto_execute:
        exec_result = pw.workflow_execute_custom(steps, name=scenario["name"])
        result["execution"] = exec_result
        result["execution_status"] = exec_result.get("status", "unknown")

    return result


# ===========================================================================
# 6. ScriptGen — 脚本生成器
# ===========================================================================

def generate_script(steps: Optional[list[dict[str, Any]]] = None,
                    workflow_id: Optional[str] = None,
                    scenario_id: Optional[str] = None,
                    script_name: str = "generated_automation",
                    include_comments: bool = True) -> dict[str, Any]:
    """将工作流步骤生成为独立可运行的 pywinauto Python 脚本。

    Args:
        steps: 工作流步骤列表（与 workflow_id/scenario_id 三选一）
        workflow_id: 预置工作流 ID
        scenario_id: 场景模板 ID
        script_name: 生成的脚本名称
        include_comments: 是否包含注释

    Returns:
        Dict with generated script code and metadata
    """
    # 获取步骤
    if workflow_id and workflow_id in pw.WORKFLOWS:
        wf = pw.WORKFLOWS[workflow_id]
        steps = wf.get("steps", [])
        if script_name == "generated_automation":
            script_name = workflow_id.lower()
    elif scenario_id and scenario_id in SCENARIOS:
        sc = SCENARIOS[scenario_id]
        steps = sc.get("steps", [])
        if script_name == "generated_automation":
            script_name = scenario_id

    if not steps:
        return {"status": "error", "error": "No steps provided or invalid workflow/scenario ID"}

    lines = []
    lines.append(f'"""')
    lines.append(f"Auto-generated pywinauto automation script")
    lines.append(f"Generated by pywinauto-mcp generation engine v3.0")
    lines.append(f"Script: {script_name}")
    lines.append(f"Steps: {len(steps)}")
    lines.append(f'"""')
    lines.append("")
    lines.append("import time")
    lines.append("from pywinauto import Application, Desktop")
    lines.append("from pywinauto.keyboard import send_keys")
    lines.append("")
    lines.append("")
    lines.append(f"def {script_name}():")
    lines.append(f'    """Execute the automation workflow."""')

    variables: dict[str, str] = {}
    indent = "    "

    for i, step in enumerate(steps):
        tool = step.get("tool", "")
        params = step.get("params", {})
        output_key = step.get("output_key")
        description = step.get("description", tool)
        wait = step.get("wait", 0)

        if include_comments:
            lines.append(f"{indent}# Step {i+1}: {description}")

        # 根据工具类型生成代码
        code = _generate_step_code(tool, params, output_key, variables, indent)
        if code:
            lines.append(code)

        if wait > 0:
            lines.append(f"{indent}time.sleep({wait})")

        lines.append("")

    lines.append(f"{indent}print('Automation completed successfully')")
    lines.append("")
    lines.append("")
    lines.append('if __name__ == "__main__":')
    lines.append(f"    {script_name}()")
    lines.append("")

    script_code = "\n".join(lines)

    return {
        "status": "success",
        "script_name": script_name,
        "step_count": len(steps),
        "lines_of_code": len(lines),
        "script": script_code,
    }


def _generate_step_code(tool: str, params: dict[str, Any], output_key: Optional[str],
                         variables: dict[str, str], indent: str) -> str:
    """为单个步骤生成 Python 代码。"""
    prefix = f"{indent}"

    # 解析变量引用
    def _resolve(val):
        if isinstance(val, str) and val.startswith("$") and val.endswith("$"):
            var = val[1:-1]
            return variables.get(var, val)
        return repr(val)

    if tool == "app_start":
        cmd = _resolve(params.get("cmd_line", "notepad.exe"))
        backend = _resolve(params.get("backend", "uia"))
        var = output_key or "app"
        variables[output_key or "app_id"] = var
        return f"{prefix}{var} = Application(backend={backend}).start({cmd})"

    elif tool == "app_connect":
        backend = _resolve(params.get("backend", "uia"))
        var = output_key or "app"
        criteria = ", ".join(f"{k}={_resolve(v)}" for k, v in params.items() if k != "backend")
        variables[output_key or "app_id"] = var
        return f"{prefix}{var} = Application(backend={backend}).connect({criteria})"

    elif tool == "app_top_window":
        app_var = variables.get(params.get("app_id", ""), "app")
        var = output_key or "win"
        variables[output_key or "wrapper_id"] = var
        return f"{prefix}{var} = {app_var}.top_window()"

    elif tool == "app_window":
        app_var = variables.get(params.get("app_id", ""), "app")
        var = output_key or "win"
        criteria = ", ".join(f"{k}={_resolve(v)}" for k, v in params.items() if k != "app_id")
        variables[output_key or "wrapper_id"] = var
        return f"{prefix}{var} = {app_var}.window({criteria})"

    elif tool == "desktop_window":
        backend = _resolve(params.get("backend", "uia"))
        var = output_key or "win"
        criteria = ", ".join(f"{k}={_resolve(v)}" for k, v in params.items() if k != "backend")
        variables[output_key or "wrapper_id"] = var
        return f"{prefix}{var} = Desktop(backend={backend}).window({criteria})"

    elif tool == "control_child_window":
        parent_var = variables.get(params.get("wrapper_id", ""), "win")
        var = output_key or "ctrl"
        criteria = ", ".join(f"{k}={_resolve(v)}" for k, v in params.items() if k != "wrapper_id")
        variables[output_key or "target_id"] = var
        return f"{prefix}{var} = {parent_var}.child_window({criteria})"

    elif tool in ("control_click", "safe_click"):
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        button = params.get("button", "left")
        return f"{prefix}{ctrl_var}.click(button='{button}')"

    elif tool == "control_double_click":
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        return f"{prefix}{ctrl_var}.double_click()"

    elif tool == "control_right_click":
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        return f"{prefix}{ctrl_var}.right_click()"

    elif tool in ("control_type_keys", "safe_type_text"):
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        text = _resolve(params.get("text", params.get("keys", "")))
        return f"{prefix}{ctrl_var}.type_keys({text})"

    elif tool == "control_set_text":
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        text = _resolve(params.get("text", ""))
        return f"{prefix}{ctrl_var}.set_text({text})"

    elif tool == "control_set_focus":
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        return f"{prefix}{ctrl_var}.set_focus()"

    elif tool == "control_close":
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        return f"{prefix}{ctrl_var}.close()"

    elif tool == "control_maximize":
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        return f"{prefix}{ctrl_var}.maximize()"

    elif tool == "control_minimize":
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        return f"{prefix}{ctrl_var}.minimize()"

    elif tool == "control_menu_select":
        ctrl_var = variables.get(params.get("wrapper_id", ""), "ctrl")
        path = _resolve(params.get("path", ""))
        return f"{prefix}{ctrl_var}.menu_select({path})"

    elif tool == "keyboard_send_keys":
        keys = _resolve(params.get("keys", ""))
        return f"{prefix}send_keys({keys})"

    elif tool == "clipboard_set_data":
        text = _resolve(params.get("text", ""))
        return f"{prefix}import win32clipboard; win32clipboard.OpenClipboard(); win32clipboard.EmptyClipboard(); win32clipboard.SetClipboardText({text}); win32clipboard.CloseClipboard()"

    elif tool == "app_kill":
        app_var = variables.get(params.get("app_id", ""), "app")
        return f"{prefix}{app_var}.kill()"

    else:
        return f"{prefix}# TODO: {tool}({params}) — 自动生成不支持此工具，请手动实现"


# ===========================================================================
# 注册生成级工具到 ALL_FUNCTIONS
# ===========================================================================

GENERATION_TOOLS = {
    # NL2Workflow
    "generate_workflow": generate_workflow,
    "generate_and_execute": generate_and_execute,
    # SmartLocator
    "smart_find": smart_find,
    # AdaptiveExec
    "adaptive_execute": adaptive_execute,
    # UIAnalyzer
    "analyze_ui": analyze_ui,
    "describe_element": describe_element,
    "find_interactive_elements": find_interactive_elements,
    # ScenarioLib
    "list_scenarios": list_scenarios,
    "apply_scenario": apply_scenario,
    # ScriptGen
    "generate_script": generate_script,
}


def register_generation_tools() -> int:
    """将所有生成级工具注册到 pywinauto_wrapper.ALL_FUNCTIONS。"""
    count = 0
    for name, func in GENERATION_TOOLS.items():
        pw.ALL_FUNCTIONS[name] = func
        count += 1
    logger.info("Registered %d generation-level tools", count)
    return count


# Auto-register on import
register_generation_tools()
