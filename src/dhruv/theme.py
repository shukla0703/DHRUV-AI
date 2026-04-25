from __future__ import annotations

from pathlib import Path


APP_NAME = "DHRUV AI"
APP_TAGLINE = "Intelligence that guides. Action that delivers."
DEFAULT_WAKE_WORD = "dhruv"

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
LOGO_PATH = ASSETS_DIR / "dhruv-logo.png"

TOKENS = {
    "bg_base": "#030817",
    "bg_mid": "#071127",
    "bg_panel": "rgba(8, 18, 36, 220)",
    "bg_panel_soft": "rgba(13, 26, 47, 196)",
    "bg_hero": "rgba(10, 21, 44, 236)",
    "text_primary": "#f7fbff",
    "text_muted": "#b9c9dc",
    "text_warm": "#dce9ff",
    "accent_cyan": "#2fd0ff",
    "accent_blue": "#1684ff",
    "accent_white": "#f6fbff",
    "accent_line": "rgba(102, 197, 255, 0.22)",
    "accent_gold": "#9fdcff",
    "button_primary": "rgba(18, 132, 255, 210)",
    "button_secondary": "rgba(18, 54, 110, 170)",
    "button_danger": "rgba(80, 32, 54, 190)",
}
