"""安全降级演练 — 验证 4 种故障场景系统不崩溃。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from harness.fallback import safe_run_node, is_all_degraded, emergency_hold


def drill_api_failure():
    """场景 1：tushare API 全部返回错误。"""
    def bad_node(state):
        raise ConnectionError("tushare API 连接失败")
    result = safe_run_node(bad_node, {"ts_code": "test"}, "fundamental_score")
    ok = result.get("fundamental_score", {}).get("_degraded", False)
    print(f"  场景 1 API 失败: {'PASS' if ok else 'FAIL'}")
    return ok


def drill_llm_failure():
    """场景 2：Kimi LLM 超时。"""
    def timeout_node(state):
        raise TimeoutError("Kimi API 超时")
    result = safe_run_node(timeout_node, {"ts_code": "test"}, "macro_themes")
    ok = result.get("macro_themes", {}).get("_degraded", False)
    print(f"  场景 2 LLM 失败: {'PASS' if ok else 'FAIL'}")
    return ok


def drill_sandbox_crash():
    """场景 3：DuckDB 连接失败。"""
    def crash_node(state):
        raise RuntimeError("DuckDB 连接断开")
    result = safe_run_node(crash_node, {"ts_code": "test"}, "risk_assessment")
    ok = result.get("risk_assessment", {}).get("_degraded", False)
    print(f"  场景 3 Sandbox 崩溃: {'PASS' if ok else 'FAIL'}")
    return ok


def drill_total_failure():
    """场景 4：所有 agent 降级 -> emergency_hold。"""
    state = {
        "fundamental_score": {"score": 50, "_degraded": True},
        "technical_score": {"score": 50, "_degraded": True},
        "macro_themes": {"score": 50, "_degraded": True},
        "event_analysis": {"score": 50, "_degraded": True},
    }
    all_bad = is_all_degraded(state)
    if all_bad:
        hold = emergency_hold()
        ok = hold.get("supervisor_signal", {}).get("direction") == "hold"
    else:
        ok = False
    print(f"  场景 4 全链路失败: {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    print("=== 安全降级演练 ===\n")
    results = [drill_api_failure(), drill_llm_failure(), drill_sandbox_crash(), drill_total_failure()]
    passed = sum(results)
    total = len(results)
    print(f"\n结果: {passed}/{total} PASS")
    if passed == total:
        print("[ALL PASS]")
    else:
        print("[SOME FAILED]")


if __name__ == "__main__":
    main()
