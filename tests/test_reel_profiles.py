from __future__ import annotations

import json
from pathlib import Path

from slotmodel.runtime_tools import discover_reel_profiles


def _write_json(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ok": True}), encoding="utf-8")


def test_discovers_candidate_reports(tmp_path: Path) -> None:

    candidates = tmp_path / "candidates"

    _write_json(candidates / "high_vol.json")
    _write_json(candidates / "high_vol_report.json")
    _write_json(candidates / "low_vol.json")

    profiles = discover_reel_profiles(
        candidates_dir=candidates,
    )

    assert [profile.name for profile in profiles] == [
        "high_vol",
        "low_vol",
    ]
    assert profiles[0].label == "High Volatility"
    assert profiles[0].has_report

    assert profiles[1].label == "Low Volatility"
    assert not profiles[1].has_report


def test_report_json_is_not_exposed_as_a_reel_profile(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates"
    _write_json(candidates / "high_vol_report.json")
    _write_json(candidates / "high_vol.json")

    profiles = discover_reel_profiles(
        candidates_dir=candidates,
    )

    assert [profile.name for profile in profiles] == ["high_vol"]