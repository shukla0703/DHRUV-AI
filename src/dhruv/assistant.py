from __future__ import annotations

from src.dhruv.command_registry import CommandRegistry
from src.dhruv.config import settings
from src.dhruv.services.speech import Listener
from src.dhruv.services.tts import Speaker


class Assistant:
    def __init__(self) -> None:
        self.speaker = Speaker()
        self.listener = Listener()
        self.registry = CommandRegistry(self.speaker)

    def greeting(self) -> str:
        return f"{settings.assistant_name} is ready."

    def process_command(self, user_input: str) -> str:
        normalized = user_input.lower().strip()
        if normalized in {"exit", "quit", "bye"}:
            return "Goodbye."
        return self.registry.handle(user_input)

    def listen_once(
        self,
        timeout: int = 5,
        phrase_time_limit: int = 8,
        adjust_for_noise: bool = True,
    ) -> str | None:
        spoken_input = self.listener.listen(
            timeout=timeout,
            phrase_time_limit=phrase_time_limit,
            adjust_for_noise=adjust_for_noise,
        )
        if spoken_input is None:
            return None
        return spoken_input.strip()

    def run(self) -> None:
        self.speaker.say(self.greeting())
        print("Modes: type your command, or press Enter to let DHRUV AI listen once.")
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                spoken_input = self.listen_once()
                if spoken_input is None:
                    self.speaker.say(
                        "Microphone listening is unavailable right now. Type your command instead."
                    )
                    continue
                if not spoken_input:
                    self.speaker.say("I did not catch that. Please try again.")
                    continue
                user_input = spoken_input.strip()
                print(f"Heard: {user_input}")
            if not user_input:
                continue
            response = self.process_command(user_input)
            self.speaker.say(response)
            if user_input.lower() in {"exit", "quit", "bye"}:
                break
