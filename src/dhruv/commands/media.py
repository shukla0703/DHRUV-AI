from __future__ import annotations

import os
import webbrowser

from src.dhruv.commands.base import Command


class OpenYouTubeCommand(Command):
    def matches(self, user_input: str) -> bool:
        return ("open" in user_input or "start" in user_input) and "youtube" in user_input

    def execute(self, user_input: str) -> str:
        webbrowser.open("https://www.youtube.com")
        return "Opening YouTube."


class OpenCameraCommand(Command):
    def matches(self, user_input: str) -> bool:
        return (
            ("open" in user_input or "start" in user_input)
            and any(word in user_input for word in ("camera", "webcam"))
        )

    def execute(self, user_input: str) -> str:
        try:
            os.startfile("microsoft.windows.camera:")  # type: ignore[attr-defined]
            return "Opening the Windows Camera app."
        except OSError:
            return "I could not open the Camera app on this system."
