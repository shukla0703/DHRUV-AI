from __future__ import annotations

from datetime import datetime

import pyjokes
import requests

from src.dhruv.commands.base import Command


class TimeCommand(Command):
    def matches(self, user_input: str) -> bool:
        return "time" in user_input or "clock" in user_input

    def execute(self, user_input: str) -> str:
        return f"The current time is {datetime.now().strftime('%I:%M %p')}."


class DateCommand(Command):
    def matches(self, user_input: str) -> bool:
        return any(word in user_input for word in ("day", "date", "today"))

    def execute(self, user_input: str) -> str:
        return f"Today is {datetime.now().strftime('%A, %d %B %Y')}."


class JokeCommand(Command):
    def matches(self, user_input: str) -> bool:
        return "joke" in user_input or "funny" in user_input

    def execute(self, user_input: str) -> str:
        return pyjokes.get_joke()


class IpAddressCommand(Command):
    def matches(self, user_input: str) -> bool:
        return (
            "ip address" in user_input
            or user_input == "ip"
            or ("ip" in user_input and "address" in user_input)
        )

    def execute(self, user_input: str) -> str:
        try:
            response = requests.get("https://api.ipify.org", timeout=10)
            response.raise_for_status()
            return f"Your public IP address is {response.text}."
        except requests.RequestException:
            return "I could not fetch the IP address right now."
