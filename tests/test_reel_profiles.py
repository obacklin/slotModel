from __future__ import annotations

import json
from pathlib import Path

from slotmodel.reel_profiles import discover_reel_profiles


def _write_json(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ok": True}), encoding="utf-8")


def test_discovers_default_and_candidate_reports(tmp_path: Path) -> None:
    default_path = tmp_path / "reels.json"
    candidates = tmp_path / "candidates"
    _write_json(default_path)
    _write_json(candidates / "high_vol.json")
    _write_json(candidates / "high_vol_report.json")
    _write_json(candidates / "low_vol.json")

    profiles = discover_reel_profiles(
        candidates_dir=candidates,
        default_reels_path=default_path,
    )

    assert [profile.name for profile in profiles] == [
        "default",
        "high_vol",
        "low_vol",
    ]
    assert profiles[1].label == "High Volatility"
    assert profiles[1].has_report
    assert profiles[2].label == "Low Volatility"
    assert not profiles[2].has_report


def test_report_json_is_not_exposed_as_a_reel_profile(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates"
    _write_json(candidates / "high_vol_report.json")
    _write_json(candidates / "high_vol.json")

    profiles = discover_reel_profiles(
        candidates_dir=candidates,
        default_reels_path=tmp_path / "missing.json",
    )

    assert [profile.name for profile in profiles] == ["high_vol"]
