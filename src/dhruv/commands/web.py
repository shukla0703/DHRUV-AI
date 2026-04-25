from __future__ import annotations

import re
import urllib.parse
import webbrowser

from src.dhruv.commands.base import Command


COMMON_SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "canva": "https://www.canva.com",
}


class OpenWebsiteCommand(Command):
    def matches(self, user_input: str) -> bool:
        return user_input.startswith("open ") or user_input.startswith("launch ")

    def execute(self, user_input: str) -> str:
        target = user_input
        if target.startswith("open "):
            target = target.removeprefix("open ").strip()
        elif target.startswith("launch "):
            target = target.removeprefix("launch ").strip()

        url = resolve_website_url(target)
        if not url:
            encoded = urllib.parse.quote_plus(target)
            webbrowser.open(f"https://www.google.com/search?q={encoded}")
            return f"I could not confirm a direct website for {target}, so I searched the web for it."

        webbrowser.open(url)
        return f"Opening {url}."


class WebSearchCommand(Command):
    def matches(self, user_input: str) -> bool:
        return user_input.startswith("search ") or user_input.startswith("look up ")

    def execute(self, user_input: str) -> str:
        query = user_input
        if query.startswith("search "):
            query = query.removeprefix("search ").strip()
        elif query.startswith("look up "):
            query = query.removeprefix("look up ").strip()
        if not query:
            return "Tell me what you want to search for."
        encoded = urllib.parse.quote_plus(query)
        webbrowser.open(f"https://www.google.com/search?q={encoded}")
        return f"Searching the web for {query}."


def resolve_website_url(target: str) -> str | None:
    cleaned = target.strip().lower()
    if not cleaned:
        return None

    if cleaned in COMMON_SITES:
        return COMMON_SITES[cleaned]

    candidate = cleaned.replace(" ", "")
    if candidate.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(candidate)
        if parsed.netloc:
            return candidate
        return None

    candidate = candidate.removeprefix("www.")
    if _looks_like_domain(candidate):
        return f"https://{candidate}"

    if re.fullmatch(r"[a-z0-9-]+", candidate):
        return f"https://www.{candidate}.com"

    return None


def _looks_like_domain(value: str) -> bool:
    if "." not in value:
        return False
    if " " in value or "/" in value:
        return False
    pattern = r"^[a-z0-9-]+(\.[a-z0-9-]+)+$"
    return re.fullmatch(pattern, value) is not None
