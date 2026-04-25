from __future__ import annotations
import re

from src.dhruv.commands.base import Command
from src.dhruv.commands.info import DateCommand, IpAddressCommand, JokeCommand, TimeCommand
from src.dhruv.commands.media import OpenCameraCommand, OpenYouTubeCommand
from src.dhruv.commands.system import OpenExplorerCommand, SystemStatusCommand
from src.dhruv.commands.web import OpenWebsiteCommand, WebSearchCommand, resolve_website_url
from src.dhruv.services.llm import AIResponder
from src.dhruv.services.memory import MemoryStore
from src.dhruv.services.tts import Speaker


class CommandRegistry:
    def __init__(self, speaker: Speaker) -> None:
        self.speaker = speaker
        self.ai_responder = AIResponder()
        self.memory_store = MemoryStore()
        self.commands: list[Command] = [
            TimeCommand(),
            DateCommand(),
            JokeCommand(),
            IpAddressCommand(),
            SystemStatusCommand(),
            OpenCameraCommand(),
            OpenExplorerCommand(),
            OpenYouTubeCommand(),
            OpenWebsiteCommand(),
            WebSearchCommand(),
        ]

    def handle(self, user_input: str) -> str:
        raw_input = user_input.strip()
        normalized = self._normalize(raw_input)
        for command in self.commands:
            if command.matches(normalized):
                response = command.execute(normalized)
                self._record_command(command, raw_input, normalized, response)
                return response
        ai_response = self.ai_responder.reply(raw_input)
        if ai_response:
            return ai_response
        return (
            "I do not know that command yet. "
                "Add an OPENAI_API_KEY to use the AI fallback, or create a new command module in src/dhruv/commands."
        )

    @staticmethod
    def _normalize(user_input: str) -> str:
        text = user_input.lower().strip()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\b(please|could you|can you|would you|tell me|show me|hey|the|a|an)\b", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _record_command(
        self,
        command: Command,
        raw_input: str,
        normalized: str,
        response: str,
    ) -> None:
        if isinstance(command, WebSearchCommand):
            query = self._trim_prefix(raw_input, ("search ", "look up "))
            self.memory_store.save("web_search", query or raw_input, response)
            return

        if isinstance(command, OpenWebsiteCommand):
            target = self._trim_prefix(raw_input, ("open ", "launch "))
            resolved = resolve_website_url(target) or "search_fallback"
            self.memory_store.save("website_open", target or raw_input, resolved)
            return

        if isinstance(command, SystemStatusCommand):
            self.memory_store.save("system_status", raw_input, response)

    @staticmethod
    def _trim_prefix(value: str, prefixes: tuple[str, ...]) -> str:
        lowered = value.strip().lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                return value.strip()[len(prefix) :].strip()
        return value.strip()
