from __future__ import annotations

import argparse
from pathlib import Path
import os
import subprocess
import sys

from src.dhruv.assistant import Assistant
from src.dhruv.config import settings
from src.dhruv.theme import APP_NAME

try:
    from src.dhruv.gui import launch_gui
except ImportError:
    launch_gui = None


def ensure_project_venv() -> None:
    current_python = Path(sys.executable).resolve()
    project_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    if not project_python.exists():
        return
    if current_python == project_python.resolve():
        return

    env = os.environ.copy()
    env["AETHER_VENV_ACTIVE"] = "1"
    subprocess.Popen([str(project_python), str(Path(__file__).resolve()), *sys.argv[1:]], env=env)
    raise SystemExit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Launch the {APP_NAME} desktop assistant."
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in terminal mode instead of the GUI.",
    )
    parser.add_argument(
        "--startup",
        action="store_true",
        help="Launch in Windows startup mode and auto-arm wake listening.",
    )
    parser.add_argument(
        "--arm-wake",
        action="store_true",
        help="Start the GUI with wake-word mode armed immediately.",
    )
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="Start the GUI minimized.",
    )
    parser.add_argument(
        "--no-auto-arm",
        action="store_true",
        help="Disable .env-driven auto-arming for this launch.",
    )
    return parser.parse_args()


def main() -> None:
    if os.environ.get("AETHER_VENV_ACTIVE") != "1":
        ensure_project_venv()
    args = parse_args()
    assistant = Assistant()
    if args.cli or launch_gui is None:
        assistant.run()
        return

    startup_mode = args.startup
    arm_wake_mode = True
    if args.no_auto_arm:
        arm_wake_mode = args.arm_wake or startup_mode
    else:
        arm_wake_mode = (
            arm_wake_mode
            or startup_mode
            or args.arm_wake
            or settings.auto_arm_wake_mode
        )

    launch_gui(
        assistant,
        arm_wake_mode=arm_wake_mode,
        start_minimized=args.minimized or (startup_mode and settings.start_minimized),
    )


if __name__ == "__main__":
    main()
