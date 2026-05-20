"""把 data/week_{date}/*.json 整合成汇总 markdown 报告。

支持：
- 从 data/market_scan_{date}.json 读取候选池（替代 hardcode）
- Atomic write（先写 .tmp 再 os.replace）
- 异常时保留原文件不 truncate
- --dry-run 选项：只打印不写文件

设计：
- main()：load_candidates -> 逐只 load -> build_content -> atomic_write
- cli()：argparse + try/except 包裹 main()；dry-run 走 build_content + print，不调用 atomic_write
"""
from __future__ import annotations
import sys, json, os, argparse
from pathlib import Path
from datetime import datetime

OUT_DIR = Path("data/week_20260515")
REPORT_FILE = Path("data/week_20260515_deep_analysis.md")
SCAN_JSON = Path("data/market_scan_20260515.json")


def load(target: "Path | str") -> dict | list | None:
    """根据 target 类型分发的 JSON 加载入口：
    - `Path`：直接读该文件；不存在则抛 FileNotFoundError；解析失败返回 {"error": "..."}
    - `str`（ts_code）：读 OUT_DIR/{ts_code 替换点为下划线}.json；不存在返回 None；解析失败返回 {"error": "..."}

    设计动机：把 SCAN_JSON 与 per-stock JSON 收敛到同一个 I/O 入口，
    测试中 `patch.object(mod, "load")` 一处即可同时拦截两类读取，避免多点 mock。
    """
    if isinstance(target, Path):
        if not target.exists():
            raise FileNotFoundError(f"文件不存在: {target}")
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception as e:
            return {"error": f"解析失败: {e}"}
    f = OUT_DIR / f"{target.replace('.', '_')}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"解析失败: {e}"}


def load_candidates() -> list[tuple]:
    """从 SCAN_JSON 读 candidates；缺失则报错。返回 (ts_code, stock_name, trigger_reason, industry) 四元组列表。

    走 load() 而非直接读文件，这样测试中 patch load 即可同时拦截候选池与 per-stock 加载。
    """
    data = load(SCAN_JSON)
    if data is None:
        raise FileNotFoundError(f"扫描结果不存在: {SCAN_JSON}; 先跑 scripts/run_weekly_pipeline.py")
    if isinstance(data, dict) and "error" in data and "candidates" not in data:
        raise RuntimeError(f"扫描结果解析失败: {data['error']}")
    cands = data.get("candidates", [])
    return [
        (
            c["ts_code"],
            c.get("stock_name", ""),
            c.get("trigger_reason", ""),
            c.get("industry", ""),
        )
        for c in cands
    ]


def fmt_list(items, max_n=5):
    if not items:
        return "—"
    if isinstance(items, str):
        return items[:200]
    out = []
    for x in items[:max_n]:
        if isinstance(x, dict):
            out.append(str(x.get("challenge", x.get("evidence", x))))
        else:
            out.append(str(x))
    return "<br>".join(f"• {x[:200]}" for x in out)


def write_section(out, ts_code, name, signal, ind, data):
    out.append(f"\n## {ts_code} {name}（{ind}）")
    out.append(f"\n**触发信号**: {signal}")
    if not data:
        out.append("\n_未跑出结果_")
        return
    if "error" in data and "phase1" not in data:
        out.append(f"\n_分析失败：{data.get('error','')[:300]}_")
        return
    p1 = data.get("phase1", {})
    p2 = data.get("phase2", {})
    p3 = data.get("phase3", {})
    crit = data.get("critic", {})
    out.append(f"\n### 投资假设\n> {p1.get('hypothesis', p3.get('hypothesis','—'))}")
    out.append(f"\n### 核心结论\n| 字段 | 值 |\n|---|---|")
    out.append(f"| 假设成立 | {p3.get('hypothesis_valid','—')} |")
    out.append(f"| 仓位 | **{p3.get('position_type','—')}** |")
    out.append(f"| Critic 建议 | **{crit.get('recommendation','—')}** |")
    vers = p2.get("verifications", [])
    if vers:
        out.append(f"\n### Phase 2 验证\n| # | 问题 | 结论 |\n|---|---|---|")
        for i, v in enumerate(vers, 1):
            q = (v.get("question", "") or "")[:80].replace("|", "\\|")
            out.append(f"| {i} | {q} | **{v.get('verdict','—')}** |")


def build_content() -> str:
    """拼装报告 markdown 字符串。不写文件。"""
    candidates = load_candidates()
    out = [
        "---",
        "标题: 候选池深度分析",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "---",
        "",
        "# 候选池深度分析",
        "",
        "## 总览",
        "| # | 代码 | 名称 | 行业 | 触发信号 | 仓位 | Critic建议 |",
        "|---|---|---|---|---|---|---|",
    ]
    summaries = []
    for i, (ts, name, sig, ind) in enumerate(candidates, 1):
        data = load(ts)
        summaries.append((ts, name, sig, ind, data))
        if not data or ("error" in data and "phase1" not in data):
            out.append(f"| {i} | {ts} | {name} | {ind} | {sig} | — | — |")
            continue
        p3 = data.get("phase3", {})
        crit = data.get("critic", {})
        out.append(
            f"| {i} | {ts} | {name} | {ind} | {sig} | **{p3.get('position_type','—')}** | **{crit.get('recommendation','—')}** |"
        )
    for ts, name, sig, ind, data in summaries:
        write_section(out, ts, name, sig, ind, data)
    return "\n".join(out)


def atomic_write(target: Path, content: str) -> None:
    """先写 .tmp 再 os.replace，保证写入原子性。

    finally 中清理 .tmp：os.replace 成功后 tmp 已不存在（unlink missing_ok=True 是 no-op），
    只有 write_text 抛异常或 replace 失败的路径才会真正删除残留 tmp 文件。
    """
    assert len(content) > 50, f"内容过短可疑（{len(content)} 字符），拒绝写入避免 truncate"
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def main() -> str:
    """生产路径：build_content -> atomic_write。异常自然向上抛出，不在此 catch。"""
    content = build_content()
    atomic_write(REPORT_FILE, content)
    return content


def cli():
    ap = argparse.ArgumentParser(description="把 deep analysis JSON 整合为汇总 markdown 报告")
    ap.add_argument("--dry-run", action="store_true", help="只打印到 stdout，不写文件")
    args = ap.parse_args()
    try:
        if args.dry_run:
            content = build_content()
            print(content)
        else:
            main()
            print(f"已写入 {REPORT_FILE} ({REPORT_FILE.stat().st_size} bytes)")
    except Exception as e:
        print(f"[error] 报告生成失败: {e}; 不 truncate {REPORT_FILE}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
