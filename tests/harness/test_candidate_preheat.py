from unittest.mock import patch, MagicMock
import pytest
from harness import candidate_preheat


@patch("harness.candidate_preheat._preheat_one_stock")
def test_preheat_candidates_returns_summary(mock_one):
    mock_one.side_effect = [
        {"ts_code": "300054.SZ", "announcement_count": 12, "report_count": 5, "industry_report_count": 8, "elapsed_sec": 45.2},
        {"ts_code": "002428.SZ", "announcement_count": 8, "report_count": 3, "industry_report_count": 6, "elapsed_sec": 30.1},
    ]
    candidates = [
        {"ts_code": "300054.SZ", "stock_name": "鼎龙股份"},
        {"ts_code": "002428.SZ", "stock_name": "云南锗业"},
    ]
    result = candidate_preheat.preheat_candidates(candidates, output_dir="data/")
    assert len(result["preheated"]) == 2
    assert result["preheated"][0]["announcement_count"] == 12
    assert result["failed"] == []


@patch("harness.candidate_preheat._preheat_one_stock")
def test_single_stock_failure_does_not_block_batch(mock_one):
    mock_one.side_effect = [RuntimeError("PDF 下载失败"), {"ts_code": "002428.SZ", "announcement_count": 8}]
    result = candidate_preheat.preheat_candidates(
        [{"ts_code": "300054.SZ", "stock_name": "A"}, {"ts_code": "002428.SZ", "stock_name": "B"}],
        output_dir="data/",
    )
    assert len(result["failed"]) == 1
    assert result["failed"][0]["ts_code"] == "300054.SZ"
    assert len(result["preheated"]) == 1


def test_announcement_limit_caps_at_30(tmp_path):
    """超过 30 份公告时应该按优先级裁剪到 30。"""
    raw = [{"title": f"公告 {i}", "ann_date": "20260515", "ann_type": "其他" if i > 5 else "业绩预告"} for i in range(50)]
    filtered = candidate_preheat._select_announcements(raw, max_count=30)
    assert len(filtered) == 30
    # 业绩预告等"重大"类应优先保留
    high_priority = [a for a in filtered if a.get("ann_type") in {"业绩预告", "业绩快报", "重大投资"}]
    assert len(high_priority) >= 5
