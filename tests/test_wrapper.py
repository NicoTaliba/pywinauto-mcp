"""
PyWinAuto MCP — Comprehensive Test Suite

Run with: python -m pytest tests/ -v
Or directly: python tests/test_wrapper.py
"""

import sys
import os
import time
import importlib
import unittest

# Add scripts to path
_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import pywinauto_wrapper as pw

# Import generation engine to register generation-level tools
import generation_engine  # noqa: F401


class TestVersionAndCapabilities(unittest.TestCase):
    """Test version info and capabilities."""

    def test_version_exists(self):
        self.assertTrue(hasattr(pw, "VERSION"))
        self.assertEqual(pw.VERSION, "2.0.0")

    def test_health_check(self):
        result = pw.health_check()
        self.assertEqual(result["status"], "healthy")
        self.assertTrue(result["all_ok"])
        self.assertIn("python", result["checks"])
        self.assertIn("pywinauto", result["checks"])
        self.assertIn("platform", result["checks"])

    def test_get_capabilities(self):
        caps = pw.get_capabilities()
        self.assertEqual(caps["version"], "2.0.0")
        self.assertEqual(caps["total_tools"], len(pw.ALL_FUNCTIONS))
        self.assertEqual(caps["total_workflows"], 105)
        self.assertEqual(caps["executable_workflows"], 35)
        self.assertIn("uia", caps["backends"])
        self.assertIn("win32", caps["backends"])
        self.assertGreater(len(caps["features"]), 10)


class TestInputValidation(unittest.TestCase):
    """Test input validation helpers."""

    def test_validate_backend_valid(self):
        self.assertEqual(pw._validate_backend("uia"), "uia")
        self.assertEqual(pw._validate_backend("win32"), "win32")

    def test_validate_backend_invalid(self):
        with self.assertRaises(ValueError):
            pw._validate_backend("invalid")

    def test_validate_mouse_button_valid(self):
        self.assertEqual(pw._validate_mouse_button("left"), "left")
        self.assertEqual(pw._validate_mouse_button("right"), "right")
        self.assertEqual(pw._validate_mouse_button("middle"), "middle")

    def test_validate_mouse_button_invalid(self):
        with self.assertRaises(ValueError):
            pw._validate_mouse_button("invalid")

    def test_validate_scroll_direction(self):
        self.assertEqual(pw._validate_scroll_direction("up"), "up")
        self.assertEqual(pw._validate_scroll_direction("down"), "down")
        with self.assertRaises(ValueError):
            pw._validate_scroll_direction("sideways")

    def test_validate_nonempty(self):
        self.assertEqual(pw._validate_nonempty("hello", "test"), "hello")
        with self.assertRaises(ValueError):
            pw._validate_nonempty("", "test")
        with self.assertRaises(ValueError):
            pw._validate_nonempty("   ", "test")

    def test_validate_positive(self):
        self.assertEqual(pw._validate_positive(5.0, "test"), 5.0)
        with self.assertRaises(ValueError):
            pw._validate_positive(0, "test")
        with self.assertRaises(ValueError):
            pw._validate_positive(-1, "test")

    def test_validate_timeout(self):
        self.assertIsNone(pw._validate_timeout(None))
        self.assertEqual(pw._validate_timeout(10.0), 10.0)
        with self.assertRaises(ValueError):
            pw._validate_timeout(0)

    def test_validate_workflow_id(self):
        self.assertEqual(pw._validate_workflow_id("WF001"), "WF001")
        self.assertEqual(pw._validate_workflow_id("WF100"), "WF100")
        with self.assertRaises(ValueError):
            pw._validate_workflow_id("BAD")
        with self.assertRaises(ValueError):
            pw._validate_workflow_id("WF0")
        with self.assertRaises(ValueError):
            pw._validate_workflow_id("wf001")


class TestErrorClassification(unittest.TestCase):
    """Test error classification and suggestions."""

    def test_element_not_found(self):
        result = pw.classify_error("Could not find window with title")
        self.assertEqual(result["category"], "element_not_found")
        self.assertGreater(len(result["suggestions"]), 0)

    def test_timeout(self):
        result = pw.classify_error("Operation timed out after 10s")
        self.assertEqual(result["category"], "timeout")

    def test_element_disabled(self):
        result = pw.classify_error("element is not enabled")
        self.assertEqual(result["category"], "element_disabled")

    def test_element_not_visible(self):
        result = pw.classify_error("element is not visible")
        self.assertEqual(result["category"], "element_not_visible")

    def test_permission_denied(self):
        result = pw.classify_error("Permission denied")
        self.assertEqual(result["category"], "permission_denied")

    def test_unknown_error(self):
        result = pw.classify_error("Some random error")
        self.assertEqual(result["category"], "unknown")


class TestSessionManagement(unittest.TestCase):
    """Test session management (thread-safe, TTL)."""

    def setUp(self):
        pw.close_all_sessions()

    def tearDown(self):
        pw.close_all_sessions()

    def test_list_sessions_empty(self):
        result = pw.list_sessions()
        self.assertEqual(result["app_count"], 0)
        self.assertEqual(result["wrapper_count"], 0)

    def test_close_all_sessions(self):
        # Manually register a fake session
        pw._app_sessions["test_app"] = {"app": None, "created": pw.datetime.now(), "last_used": pw.datetime.now()}
        result = pw.close_all_sessions()
        self.assertEqual(result["app_count"], 1)
        self.assertEqual(pw.list_sessions()["app_count"], 0)

    def test_cleanup_stale_sessions(self):
        # Register a stale session
        old_time = pw.datetime.now() - pw.timedelta(hours=3)
        pw._app_sessions["stale_app"] = {"app": None, "created": old_time, "last_used": old_time}
        result = pw.cleanup_stale_sessions()
        self.assertIn("stale_app", result["removed_apps"])
        self.assertNotIn("stale_app", pw._app_sessions)


class TestRetryMechanism(unittest.TestCase):
    """Test retry and timeout helpers."""

    def test_retry_success_first_attempt(self):
        call_count = [0]
        def succeed():
            call_count[0] += 1
            return "ok"
        result = pw._with_retry(succeed, retries=3)
        self.assertEqual(result, "ok")
        self.assertEqual(call_count[0], 1)

    def test_retry_success_after_failures(self):
        call_count = [0]
        def fail_then_succeed():
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("temporary failure")
            return "ok"
        result = pw._with_retry(fail_then_succeed, retries=3, delay=0.01)
        self.assertEqual(result, "ok")
        self.assertEqual(call_count[0], 3)

    def test_retry_exhausted(self):
        def always_fail():
            raise RuntimeError("permanent failure")
        with self.assertRaises(pw.RetryExhaustedError):
            pw._with_retry(always_fail, retries=2, delay=0.01)

    def test_timeout_success(self):
        def quick():
            return "fast"
        result = pw._with_timeout(quick, timeout=5)
        self.assertEqual(result, "fast")

    def test_timeout_triggered(self):
        def slow():
            time.sleep(10)
            return "slow"
        with self.assertRaises(pw.OperationTimeoutError):
            pw._with_timeout(slow, timeout=0.5)


class TestWorkflowRegistry(unittest.TestCase):
    """Test workflow registry and listing."""

    def test_workflow_count(self):
        self.assertEqual(len(pw.WORKFLOWS), 105)

    def test_workflow_categories(self):
        from collections import Counter
        cats = Counter(wf["category"] for wf in pw.WORKFLOWS.values())
        self.assertEqual(len(cats), 21)
        for count in cats.values():
            self.assertEqual(count, 5)

    def test_workflow_list_all(self):
        result = pw.workflow_list()
        self.assertEqual(result["count"], 105)

    def test_workflow_list_by_category(self):
        result = pw.workflow_list(category="浏览器自动化")
        self.assertEqual(result["count"], 5)

    def test_workflow_list_executable_only(self):
        result = pw.workflow_list(executable_only=True)
        self.assertEqual(result["count"], 35)

    def test_workflow_get_valid(self):
        wf = pw.workflow_get("WF001")
        self.assertEqual(wf["id"], "WF001")
        self.assertTrue(wf["executable"])

    def test_workflow_get_invalid(self):
        with self.assertRaises(ValueError):
            pw.workflow_get("WF999")


class TestConditionEvaluation(unittest.TestCase):
    """Test workflow condition evaluation."""

    def setUp(self):
        self.context = {
            "status": "ready",
            "count": 5,
            "enabled": True,
            "name": "test",
            "health": {"status": "healthy", "all_ok": True},
        }

    def test_equality(self):
        self.assertTrue(pw._evaluate_condition('$status$ == "ready"', self.context))
        self.assertFalse(pw._evaluate_condition('$status$ == "done"', self.context))

    def test_inequality(self):
        self.assertTrue(pw._evaluate_condition('$status$ != "done"', self.context))

    def test_numeric_comparison(self):
        self.assertTrue(pw._evaluate_condition("$count$ > 3", self.context))
        self.assertTrue(pw._evaluate_condition("$count$ < 10", self.context))
        self.assertTrue(pw._evaluate_condition("$count$ >= 5", self.context))
        self.assertTrue(pw._evaluate_condition("$count$ <= 5", self.context))
        self.assertFalse(pw._evaluate_condition("$count$ > 10", self.context))

    def test_truthy(self):
        self.assertTrue(pw._evaluate_condition("$enabled$", self.context))

    def test_not(self):
        self.assertFalse(pw._evaluate_condition("not $enabled$", self.context))

    def test_and(self):
        self.assertTrue(pw._evaluate_condition('$status$ == "ready" and $count$ > 3', self.context))
        self.assertFalse(pw._evaluate_condition('$status$ == "done" and $count$ > 3', self.context))

    def test_or(self):
        self.assertTrue(pw._evaluate_condition('$status$ == "done" or $count$ > 3', self.context))

    def test_dotted_path(self):
        self.assertTrue(pw._evaluate_condition('$health.status$ == "healthy"', self.context))
        self.assertTrue(pw._evaluate_condition("$health.all_ok$", self.context))

    def test_literal_boolean(self):
        self.assertTrue(pw._evaluate_condition("true", self.context))
        self.assertFalse(pw._evaluate_condition("false", self.context))


class TestWorkflowValidation(unittest.TestCase):
    """Test workflow step validation."""

    def test_valid_steps(self):
        steps = [
            {"tool": "health_check", "params": {}},
            {"tool": "get_capabilities", "params": {}, "retries": 2},
        ]
        result = pw.workflow_validate_steps(steps)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)

    def test_unknown_tool(self):
        steps = [{"tool": "nonexistent", "params": {}}]
        result = pw.workflow_validate_steps(steps)
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)

    def test_missing_tool(self):
        steps = [{"params": {}}]
        result = pw.workflow_validate_steps(steps)
        self.assertFalse(result["valid"])

    def test_invalid_retries_type(self):
        steps = [{"tool": "health_check", "retries": "not_a_number"}]
        result = pw.workflow_validate_steps(steps)
        self.assertFalse(result["valid"])


class TestCustomWorkflowExecution(unittest.TestCase):
    """Test custom workflow execution with non-GUI tools."""

    def test_simple_workflow(self):
        result = pw.workflow_execute_custom([
            {"tool": "health_check", "params": {}, "output_key": "health"},
            {"tool": "get_capabilities", "params": {}, "output_key": "caps"},
        ], name="test")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["succeeded"], 2)
        self.assertEqual(result["errors"], 0)

    def test_workflow_with_condition_skip(self):
        result = pw.workflow_execute_custom([
            {"tool": "health_check", "params": {}, "output_key": "health"},
            {"tool": "get_capabilities", "params": {},
             "condition": '$health.status$ == "degraded"'},  # should skip
        ], name="cond_test")
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["succeeded"], 1)

    def test_workflow_with_condition_run(self):
        result = pw.workflow_execute_custom([
            {"tool": "health_check", "params": {}, "output_key": "health"},
            {"tool": "get_capabilities", "params": {},
             "condition": '$health.status$ == "healthy"'},  # should run
        ], name="cond_test2")
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["succeeded"], 2)

    def test_workflow_ignore_error(self):
        result = pw.workflow_execute_custom([
            {"tool": "health_check", "params": {}},
            {"tool": "classify_error", "params": {"error_message": "test"},
             "ignore_error": True},
        ], name="ignore_test")
        # classify_error should succeed, but even if it failed, ignore_error=True
        self.assertIn(result["status"], ["success", "partial"])

    def test_empty_workflow(self):
        result = pw.workflow_execute_custom([], name="empty")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["steps_completed"], 0)


class TestCallStats(unittest.TestCase):
    """Test call statistics tracking infrastructure."""

    def test_record_call(self):
        # Manually record calls (this is what the MCP server layer does)
        pw._record_call("health_check", success=True, duration=0.01)
        pw._record_call("health_check", success=False, duration=0.02)
        stats = pw.get_call_stats()
        self.assertGreaterEqual(stats["total_calls"], 2)
        self.assertGreaterEqual(stats["errors"], 1)
        self.assertIn("health_check", stats["by_tool"])

    def test_reset_call_stats(self):
        pw._record_call("test_tool", success=True, duration=0.01)
        stats = pw.get_call_stats(reset=True)
        self.assertGreater(stats["total_calls"], 0)
        # After reset, next call should be the only one
        pw._record_call("test_tool2", success=True, duration=0.01)
        stats2 = pw.get_call_stats()
        self.assertEqual(stats2["total_calls"], 1)
        self.assertIn("test_tool2", stats2["by_tool"])


class TestAllFunctionsRegistered(unittest.TestCase):
    """Verify all expected functions are in ALL_FUNCTIONS."""

    EXPECTED_CATEGORIES = {
        "session": ["list_sessions", "close_session", "close_all_sessions"],
        "app": ["app_start", "app_connect", "app_kill", "app_top_window", "app_window"],
        "window": ["window_find", "window_exists", "window_wait", "window_dump_tree"],
        "control": ["control_click", "control_set_focus", "control_get_text", "control_close"],
        "keyboard": ["keyboard_send_keys", "keyboard_key_press", "keyboard_key_release"],
        "mouse": ["mouse_click", "mouse_move", "mouse_drag", "mouse_scroll"],
        "clipboard": ["clipboard_get_data", "clipboard_set_data", "clipboard_empty"],
        "timings": ["timings_get", "timings_set", "timings_defaults", "timings_slow", "timings_fast"],
        "sysinfo": ["sysinfo_is_x64_python", "sysinfo_is_x64_os", "sysinfo_os_arch", "sysinfo_python_bitness"],
        "find": ["find_windows", "find_elements", "enumerate_windows"],
        "taskbar": ["taskbar_click_on_button", "taskbar_get_start_button"],
        "desktop": ["desktop_windows", "desktop_active_window", "desktop_window"],
        "menu": ["menu_get_items", "menu_click_item"],
        "specific": ["combobox_select", "tab_select", "tree_select", "slider_set_position"],
        "enhanced": ["health_check", "get_capabilities", "safe_click", "safe_type_text",
                      "inspect_element", "batch_execute", "snapshot_ui_state",
                      "cleanup_stale_sessions", "classify_error", "get_call_stats"],
        "workflow": ["workflow_list", "workflow_get", "workflow_execute",
                     "workflow_execute_custom", "workflow_validate_steps"],
    }

    def test_all_categories_present(self):
        for category, funcs in self.EXPECTED_CATEGORIES.items():
            for func in funcs:
                self.assertIn(func, pw.ALL_FUNCTIONS,
                              f"Missing function '{func}' in category '{category}'")

    def test_total_count(self):
        self.assertEqual(len(pw.ALL_FUNCTIONS), 162)


class TestGenerationEngine(unittest.TestCase):
    """Test generation-level (v3.0) capabilities."""

    @classmethod
    def setUpClass(cls):
        cls.ge = importlib.import_module("generation_engine")

    def test_generation_tools_registered(self):
        gen_tools = ["generate_workflow", "generate_and_execute", "smart_find",
                      "adaptive_execute", "analyze_ui", "describe_element",
                      "find_interactive_elements", "list_scenarios",
                      "apply_scenario", "generate_script"]
        for tool in gen_tools:
            self.assertIn(tool, pw.ALL_FUNCTIONS, f"Missing generation tool: {tool}")

    def test_generate_workflow_basic(self):
        result = self.ge.generate_workflow("启动记事本，输入Hello，然后保存")
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["step_count"], 0)
        self.assertTrue(result["validation"]["valid"])
        self.assertGreater(len(result["reasoning"]), 0)

    def test_generate_workflow_launch_app(self):
        result = self.ge.generate_workflow("启动计算器")
        self.assertEqual(result["status"], "success")
        tools_used = [r.get("tool") for r in result["reasoning"] if r.get("tool")]
        self.assertIn("app_start", tools_used)

    def test_generate_workflow_click(self):
        result = self.ge.generate_workflow("点击确定按钮")
        self.assertEqual(result["status"], "success")
        # Should detect click action
        actions = [r.get("action") for r in result["reasoning"]]
        self.assertTrue(any("点击" in a for a in actions))

    def test_generate_workflow_empty(self):
        result = self.ge.generate_workflow("")
        self.assertEqual(result["status"], "error")

    def test_smart_find_invalid_backend(self):
        with self.assertRaises(ValueError):
            self.ge.smart_find("test", backend="invalid")

    def test_list_scenarios(self):
        result = self.ge.list_scenarios()
        self.assertGreaterEqual(result["count"], 10)
        self.assertEqual(len(result["scenarios"]), result["count"])

    def test_list_scenarios_by_category(self):
        result = self.ge.list_scenarios(category="文本编辑")
        self.assertGreaterEqual(result["count"], 1)
        for s in result["scenarios"]:
            self.assertEqual(s["category"], "文本编辑")

    def test_apply_scenario_valid(self):
        result = self.ge.apply_scenario("notepad_basic", params={"text": "Test"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["scenario_id"], "notepad_basic")
        self.assertGreater(result["step_count"], 0)
        self.assertTrue(result["validation"]["valid"])

    def test_apply_scenario_invalid(self):
        result = self.ge.apply_scenario("nonexistent_scenario")
        self.assertEqual(result["status"], "error")

    def test_generate_script_from_workflow(self):
        result = self.ge.generate_script(workflow_id="WF001", script_name="test_script")
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["lines_of_code"], 0)
        self.assertIn("import", result["script"])
        self.assertIn("def test_script", result["script"])
        self.assertIn("if __name__", result["script"])

    def test_generate_script_from_steps(self):
        steps = [
            {"tool": "app_start", "params": {"cmd_line": "notepad.exe"}, "output_key": "app_id"},
            {"tool": "keyboard_send_keys", "params": {"keys": "^s"}},
        ]
        result = self.ge.generate_script(steps=steps, script_name="custom")
        self.assertEqual(result["status"], "success")
        self.assertIn("notepad.exe", result["script"])

    def test_analyze_ui_no_wrapper(self):
        result = self.ge.analyze_ui(depth=1)
        self.assertEqual(result["status"], "success")
        self.assertIn("summary", result)
        self.assertIn("description", result)
        self.assertGreater(result["summary"]["total_elements"], 0)

    def test_describe_element_invalid(self):
        result = self.ge.describe_element("nonexistent_wrapper")
        self.assertEqual(result["status"], "error")

    def test_fuzzy_match_score(self):
        self.assertEqual(self.ge._fuzzy_match_score("确定", "确定"), 1.0)
        self.assertGreater(self.ge._fuzzy_match_score("确定按钮", "确定"), 0.5)
        self.assertEqual(self.ge._fuzzy_match_score("", "test"), 0.0)

    def test_detect_control_type(self):
        self.assertEqual(self.ge._detect_control_type("点击确定按钮"), "Button")
        self.assertEqual(self.ge._detect_control_type("在输入框中填写"), "Edit")
        self.assertIsNone(self.ge._detect_control_type("做一些事情"))

    def test_recovery_strategies_exist(self):
        self.assertIn("element_not_found", self.ge._RECOVERY_STRATEGIES)
        self.assertIn("timeout", self.ge._RECOVERY_STRATEGIES)
        self.assertGreater(len(self.ge._RECOVERY_STRATEGIES["element_not_found"]), 0)


class TestSystemOperations(unittest.TestCase):
    """Test system operation functions (download / install / uninstall / process)."""

    def test_system_functions_registered(self):
        funcs = [
            "system_download_file", "system_run_command", "system_process_running",
            "system_file_exists", "system_get_installed_software", "system_find_software",
            "system_uninstall_software", "system_install_package", "system_download_and_install"
        ]
        for f in funcs:
            self.assertIn(f, pw.ALL_FUNCTIONS, f"{f} not registered in ALL_FUNCTIONS")

    def test_system_file_exists_true(self):
        result = pw.system_file_exists(r"C:\Windows\notepad.exe")
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["exists"])
        self.assertTrue(result["is_file"])

    def test_system_file_exists_false(self):
        result = pw.system_file_exists(r"C:\nonexistent\file_xyz123.exe")
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["exists"])

    def test_system_process_running_explorer(self):
        result = pw.system_process_running("explorer.exe")
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["running"])
        self.assertGreater(result["process_count"], 0)

    def test_system_process_running_nonexistent(self):
        result = pw.system_process_running("nonexistent_process_xyz.exe")
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["running"])

    def test_system_run_command_echo(self):
        result = pw.system_run_command("echo test_output", timeout=10)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["return_code"], 0)
        self.assertIn("test_output", result.get("stdout", ""))

    def test_system_run_command_timeout(self):
        result = pw.system_run_command("timeout /t 5", timeout=2)
        self.assertTrue(result.get("timed_out") or result["status"] == "error")

    def test_system_get_installed_software(self):
        result = pw.system_get_installed_software()
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["count"], 0)
        self.assertIsInstance(result["software"], list)

    def test_system_find_software_windows(self):
        # Windows should have some software installed
        result = pw.system_get_installed_software()
        if result["count"] > 0:
            first_name = result["software"][0]["name"]
            find_result = pw.system_find_software(first_name[:10])
            self.assertEqual(find_result["status"], "success")

    def test_system_find_software_nonexistent(self):
        result = pw.system_find_software("NonexistentSoftwareXYZ123")
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["found"])
        self.assertEqual(result["match_count"], 0)

    def test_wf101_to_wf105_registered(self):
        for wf_id in ["WF101", "WF102", "WF103", "WF104", "WF105"]:
            wf = pw.workflow_get(wf_id)
            self.assertIn("name", wf, f"{wf_id} not found")
            self.assertIn("软件安装与管理", wf.get("category", ""))

    def test_workflow_id_validation_wf105(self):
        self.assertEqual(pw._validate_workflow_id("WF105"), "WF105")

    def test_workflow_id_validation_invalid_high(self):
        with self.assertRaises(ValueError):
            pw._validate_workflow_id("WF106")


if __name__ == "__main__":
    import importlib
    unittest.main(verbosity=2)
