"""独立风控规则引擎 — 不依赖 LLM，纯规则判断。"""
from __future__ import annotations


def check_blacklist(ts_code: str, stock_info: dict) -> tuple[bool, str]:
    """检查是否在黑名单。返回 (is_blacklisted, reason)。

    黑名单条件：
    - name 含 "ST" 或 "*ST"
    - list_status != "L"（非正常上市）
    - 日均成交额 < 5000 万（avg_amount 字段，单位万元）
    """
    name = stock_info.get("name", "")
    if "ST" in name:
        return True, f"{ts_code} 含 ST 标记"
    status = stock_info.get("list_status", "L")
    if status != "L":
        return True, f"{ts_code} 非正常上市状态: {status}"
    avg_amount = stock_info.get("avg_amount", float("inf"))
    if avg_amount < 5000:
        return True, f"{ts_code} 日均成交额 {avg_amount} 万元 < 5000 万"
    return False, ""


def check_position_limit(position_type: str = "core") -> float:
    """返回单标的仓位上限百分比。核心仓 15%，卫星仓 3%。"""
    return 15.0 if position_type == "core" else 3.0


def check_stop_loss(
    entry_price: float, current_price: float, position_type: str = "core"
) -> tuple[bool, str]:
    """检查是否触发止损。

    核心仓：跌幅 > 10%
    卫星仓：单日跌幅 > 5% 或累计跌幅 > 10%
    """
    if entry_price <= 0:
        return False, ""
    drop_pct = (entry_price - current_price) / entry_price * 100
    if position_type == "core" and drop_pct > 10:
        return True, f"核心仓跌幅 {drop_pct:.1f}% > 10%"
    if position_type == "satellite" and drop_pct > 5:
        return True, f"卫星仓跌幅 {drop_pct:.1f}% > 5%"
    return False, ""


def check_portfolio_drawdown(weekly_return_pct: float) -> tuple[bool, str]:
    """检查组合周回撤是否触发暂停。周回撤 > 8% 暂停新开仓。"""
    if weekly_return_pct < -8:
        return True, f"周回撤 {weekly_return_pct:.1f}% > 8%，暂停新开仓"
    return False, ""
