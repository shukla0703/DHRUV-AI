from __future__ import annotations
import threading
import subprocess

try:
    import pyttsx3
except ImportError:  # pragma: no cover
    pyttsx3 = None


class Speaker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._speaking = False
        self.use_powershell_fallback = False
        if not pyttsx3:
            self.engine = None
            self.use_powershell_fallback = True
            return
        try:
            self.engine = pyttsx3.init()
        except Exception:  # pragma: no cover
            self.engine = None
            self.use_powershell_fallback = True

    def say(self, message: str) -> None:
        print(f"DHRUV AI: {message}")
        with self._lock:
            self._speaking = True
            try:
                if self.engine:
                    self.engine.say(message)
                    self.engine.runAndWait()
                    return
                if self.use_powershell_fallback:
                    self._speak_with_powershell(message)
            finally:
                self._speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def _speak_with_powershell(self, message: str) -> None:
        escaped = message.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speaker.Speak('{escaped}')"
        )
        try:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass
