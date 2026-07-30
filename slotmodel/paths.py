from __future__ import annotations

from pathlib import Path


# repository/slotmodel/paths.py
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent

# Project-level configuration directories
CONFIG_DIR = PROJECT_ROOT / "config"

REELS_CONFIG_DIR = CONFIG_DIR / "reels"
REELS_CONFIG_PATH = REELS_CONFIG_DIR / "reels.json"