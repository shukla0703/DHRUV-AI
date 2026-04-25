from __future__ import annotations

import re
from typing import Optional

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover
    sr = None


class Listener:
    def __init__(self) -> None:
        self.enabled = sr is not None
        self.recognizer = sr.Recognizer() if sr else None
        if self.recognizer is not None:
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            self.recognizer.phrase_threshold = 0.2

    def listen(
        self,
        timeout: int = 5,
        phrase_time_limit: int = 8,
        adjust_for_noise: bool = True,
        ambient_duration: float = 0.8,
    ) -> Optional[str]:
        if not self.enabled:
            return None

        assert self.recognizer is not None
        try:
            with sr.Microphone() as source:
                if adjust_for_noise:
                    self.recognizer.adjust_for_ambient_noise(
                        source,
                        duration=ambient_duration,
                    )
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
        except OSError:
            return None
        except sr.WaitTimeoutError:
            return ""

        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            return None

    @staticmethod
    def contains_wake_word(transcript: str, wake_word: str) -> bool:
        words = re.findall(r"[a-zA-Z']+", transcript.lower())
        target = wake_word.lower().strip()
        for word in words:
            if word == target:
                return True
            # Accept close matches from speech recognition, e.g. "assistance" for "assistant".
            if _similarity(word, target) >= 0.78:
                return True
        return False


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    matches = sum(1 for a, b in zip(left, right) if a == b)
    longest = max(len(left), len(right))
    return matches / longest
