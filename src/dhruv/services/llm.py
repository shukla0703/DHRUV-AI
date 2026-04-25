from __future__ import annotations

from collections import deque
import os
import subprocess
from typing import Optional

import requests
import wikipedia

from src.dhruv.commands.info import DateCommand, IpAddressCommand, JokeCommand, TimeCommand
from src.dhruv.commands.media import OpenCameraCommand, OpenYouTubeCommand
from src.dhruv.commands.system import OpenExplorerCommand, SystemStatusCommand
from src.dhruv.commands.web import COMMON_SITES, OpenWebsiteCommand, WebSearchCommand, resolve_website_url
from src.dhruv.config import settings
from src.dhruv.services.memory import MemoryStore

try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.tools import StructuredTool
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    AIMessage = None
    AgentExecutor = None
    BaseMessage = None
    ChatOpenAI = None
    ChatPromptTemplate = None
    HumanMessage = None
    MessagesPlaceholder = None
    StructuredTool = None
    SystemMessage = None
    create_tool_calling_agent = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


class AIResponder:
    def __init__(self) -> None:
        self.provider = settings.llm_provider.lower().strip()
        self.model = settings.llm_model.strip()
        self.memory: deque[tuple[str, str]] = deque(maxlen=max(settings.memory_turns, 1))
        self.memory_store = MemoryStore()
        self.chat_model = self._build_langchain_model()
        self.agent = self._build_agent()
        self.client = self._build_openai_client()

    @property
    def enabled(self) -> bool:
        return (
            self.agent is not None or self.chat_model is not None or self.client is not None
        ) and bool(self.model)

    def reply(self, user_input: str) -> Optional[str]:
        if not self.enabled:
            return None

        agent_response = self._reply_with_agent(user_input)
        if agent_response:
            self._remember(user_input, agent_response)
            return agent_response

        langchain_response = self._reply_with_langchain(user_input)
        if langchain_response:
            self._remember(user_input, langchain_response)
            return langchain_response

        openai_response = self._reply_with_openai(user_input)
        if openai_response:
            self._remember(user_input, openai_response)
        return openai_response

    def _reply_with_agent(self, user_input: str) -> Optional[str]:
        if self.agent is None:
            return None

        try:
            response = self.agent.invoke(
                {
                    "input": user_input,
                    "chat_history": self._history_messages(),
                }
            )
        except Exception:
            return None

        output = response.get("output", "")
        if isinstance(output, str) and output.strip():
            return output.strip()
        return None

    def _reply_with_langchain(self, user_input: str) -> Optional[str]:
        if self.chat_model is None or SystemMessage is None or HumanMessage is None:
            return None

        try:
            response = self.chat_model.invoke(self._chat_messages(user_input))
        except Exception:
            return None

        return self._extract_langchain_text(response)

    def _reply_with_openai(self, user_input: str) -> Optional[str]:
        if self.client is None:
            return None

        try:
            response = self.client.responses.create(
                model=self.model,
                input=self._openai_input(user_input),
            )
        except Exception:
            return None

        return self._extract_openai_text(response)

    def _chat_messages(self, user_input: str) -> list[BaseMessage]:
        assert SystemMessage is not None
        assert HumanMessage is not None
        return [
            SystemMessage(content=self._system_prompt()),
            *self._history_messages(),
            HumanMessage(content=user_input),
        ]

    def _openai_input(self, user_input: str) -> list[dict[str, object]]:
        items: list[dict[str, object]] = [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": self._system_prompt()}],
            }
        ]
        for previous_user, previous_assistant in self.memory:
            items.append(
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": previous_user}],
                }
            )
            items.append(
                {
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": previous_assistant}],
                }
            )
        items.append(
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_input}],
            }
        )
        return items

    def _history_messages(self) -> list[BaseMessage]:
        if HumanMessage is None or AIMessage is None:
            return []
        history: list[BaseMessage] = []
        for previous_user, previous_assistant in self.memory:
            history.append(HumanMessage(content=previous_user))
            history.append(AIMessage(content=previous_assistant))
        return history

    def _remember(self, user_input: str, response_text: str) -> None:
        self.memory.append((user_input, response_text))
        self.memory_store.save("assistant_reply", user_input, response_text)

    def _build_langchain_model(self) -> ChatOpenAI | None:
        if self.provider != "openai":
            return None
        if ChatOpenAI is None or not settings.openai_api_key or not self.model:
            return None
        return ChatOpenAI(
            model=self.model,
            api_key=settings.openai_api_key,
            temperature=0.2,
        )

    def _build_agent(self) -> AgentExecutor | None:
        if (
            self.chat_model is None
            or AgentExecutor is None
            or ChatPromptTemplate is None
            or MessagesPlaceholder is None
            or StructuredTool is None
            or create_tool_calling_agent is None
        ):
            return None

        tools = self._build_tools()
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._agent_system_prompt()),
                MessagesPlaceholder("chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ],
        )
        agent = create_tool_calling_agent(self.chat_model, tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            handle_parsing_errors=True,
        )

    def _build_openai_client(self) -> OpenAI | None:
        if self.provider != "openai":
            return None
        if OpenAI is None or not settings.openai_api_key:
            return None
        return OpenAI(api_key=settings.openai_api_key)

    def _build_tools(self) -> list[StructuredTool]:
        assert StructuredTool is not None
        return [
            StructuredTool.from_function(
                func=self._get_time,
                name="get_current_time",
                description="Get the current local time.",
            ),
            StructuredTool.from_function(
                func=self._get_date,
                name="get_current_date",
                description="Get today's date and day of week.",
            ),
            StructuredTool.from_function(
                func=self._tell_joke,
                name="tell_programming_joke",
                description="Tell a short programming joke.",
            ),
            StructuredTool.from_function(
                func=self._get_ip_address,
                name="get_public_ip_address",
                description="Fetch the current public IP address.",
            ),
            StructuredTool.from_function(
                func=self._get_system_status,
                name="get_system_status",
                description="Read CPU, memory, battery, and operating system status from the device.",
            ),
            StructuredTool.from_function(
                func=self._open_camera,
                name="open_camera_app",
                description="Open the Windows Camera app.",
            ),
            StructuredTool.from_function(
                func=self._open_explorer,
                name="open_file_explorer",
                description="Open Windows File Explorer.",
            ),
            StructuredTool.from_function(
                func=self._open_youtube,
                name="open_youtube",
                description="Open YouTube in the default browser.",
            ),
            StructuredTool.from_function(
                func=self._open_website,
                name="open_known_website",
                description=(
                    "Open any website in the default browser using a full URL, bare domain, "
                    "or a simple site name. "
                    f"Examples include: {', '.join(sorted(COMMON_SITES))}, reddit.com, huggingface, or https://example.com."
                ),
            ),
            StructuredTool.from_function(
                func=self._search_web,
                name="search_web",
                description="Search the web for a user-provided query in the browser.",
            ),
            StructuredTool.from_function(
                func=self._lookup_wikipedia,
                name="lookup_wikipedia_summary",
                description="Get a short encyclopedia summary for a topic using Wikipedia.",
            ),
            StructuredTool.from_function(
                func=self._get_top_headlines,
                name="get_top_headlines",
                description="Fetch recent news headlines by topic or general headlines using NewsAPI.",
            ),
            StructuredTool.from_function(
                func=self._open_desktop_app,
                name="open_desktop_application",
                description=(
                    "Open a supported Windows desktop application by name. "
                    "Supported names: notepad, calculator, paint, settings, cmd."
                ),
            ),
            StructuredTool.from_function(
                func=self._recall_recent_memory,
                name="recall_recent_memory",
                description=(
            "Read recent DHRUV AI memory entries such as saved searches, opened websites, "
                    "system checks, and assistant replies."
                ),
            ),
        ]

    @staticmethod
    def _system_prompt() -> str:
        return (
            f"You are {settings.assistant_name}, a concise Windows desktop AI assistant. "
            "Use recent conversation context when it helps answer follow-up questions. "
            "If the user asks for an action you cannot do safely from chat, explain the limitation briefly "
            "and offer the next best step."
        )

    @staticmethod
    def _agent_system_prompt() -> str:
        return (
            f"You are {settings.assistant_name}, a Windows desktop assistant with tool access. "
            "Use tools when the user asks for device actions, web actions, encyclopedia lookups, or live details. "
            "Use recent conversation context for follow-up questions. "
            "If a suitable tool exists, prefer using it instead of describing what you would do. "
            "Keep final answers concise and confirm completed actions clearly."
        )

    @staticmethod
    def _extract_langchain_text(response: object) -> Optional[str]:
        content = getattr(response, "content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    if text:
                        parts.append(text)
            text = "\n".join(part.strip() for part in parts if part.strip())
            if text:
                return text
        return None

    @staticmethod
    def _extract_openai_text(response: object) -> Optional[str]:
        output_text = getattr(response, "output_text", "")
        if output_text:
            return output_text.strip()
        return None

    @staticmethod
    def _get_time() -> str:
        return TimeCommand().execute("time")

    @staticmethod
    def _get_date() -> str:
        return DateCommand().execute("date")

    @staticmethod
    def _tell_joke() -> str:
        return JokeCommand().execute("joke")

    @staticmethod
    def _get_ip_address() -> str:
        return IpAddressCommand().execute("ip address")

    @staticmethod
    def _get_system_status() -> str:
        return SystemStatusCommand().execute("system status")

    @staticmethod
    def _open_camera() -> str:
        return OpenCameraCommand().execute("open camera")

    @staticmethod
    def _open_explorer() -> str:
        return OpenExplorerCommand().execute("open explorer")

    @staticmethod
    def _open_youtube() -> str:
        return OpenYouTubeCommand().execute("open youtube")

    @staticmethod
    def _open_website(site_name: str) -> str:
        cleaned = site_name.lower().strip()
        if not cleaned:
            return "Tell me which website you want to open."
        resolved = resolve_website_url(cleaned)
        if resolved is None:
            return WebSearchCommand().execute(f"search {cleaned}")
        return OpenWebsiteCommand().execute(f"open {cleaned}")

    @staticmethod
    def _search_web(query: str) -> str:
        cleaned = query.strip()
        if not cleaned:
            return "Tell me what you want to search for."
        return WebSearchCommand().execute(f"search {cleaned}")

    @staticmethod
    def _lookup_wikipedia(topic: str) -> str:
        cleaned = topic.strip()
        if not cleaned:
            return "Tell me which topic you want summarized."
        try:
            return wikipedia.summary(cleaned, sentences=2, auto_suggest=False)
        except wikipedia.DisambiguationError as exc:
            options = ", ".join(exc.options[:5])
            return f"That topic is ambiguous. Try one of these: {options}."
        except wikipedia.PageError:
            return "I could not find a Wikipedia page for that topic."
        except Exception:
            return "Wikipedia lookup is unavailable right now."

    @staticmethod
    def _get_top_headlines(topic: str = "") -> str:
        if not settings.news_api_key:
            return "NEWS_API_KEY is not configured yet."

        params = {
            "apiKey": settings.news_api_key,
            "language": "en",
            "pageSize": 3,
        }
        cleaned = topic.strip()
        if cleaned:
            params["q"] = cleaned
            endpoint = "https://newsapi.org/v2/everything"
        else:
            params["country"] = "us"
            endpoint = "https://newsapi.org/v2/top-headlines"

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException:
            return "I could not fetch the news right now."

        articles = payload.get("articles", [])[:3]
        if not articles:
            return "I could not find any headlines for that request."

        headlines = []
        for article in articles:
            title = article.get("title", "Untitled")
            source = article.get("source", {}).get("name", "Unknown source")
            headlines.append(f"{title} ({source})")
        return "Top headlines: " + " | ".join(headlines)

    @staticmethod
    def _open_desktop_app(app_name: str) -> str:
        cleaned = app_name.lower().strip()
        if not cleaned:
            return "Tell me which app you want to open."

        app_commands = {
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "paint": ["mspaint.exe"],
            "cmd": ["cmd.exe"],
        }
        uri_commands = {
            "settings": "ms-settings:",
        }

        if cleaned in app_commands:
            try:
                subprocess.Popen(app_commands[cleaned])
                return f"Opening {cleaned}."
            except OSError:
                return f"I could not open {cleaned} on this system."

        if cleaned in uri_commands:
            try:
                os.startfile(uri_commands[cleaned])  # type: ignore[attr-defined]
                return f"Opening {cleaned}."
            except OSError:
                return f"I could not open {cleaned} on this system."

        supported = ", ".join(sorted([*app_commands.keys(), *uri_commands.keys()]))
        return f"I can open these desktop apps so far: {supported}."

    def _recall_recent_memory(self, category: str = "") -> str:
        cleaned = category.strip() or None
        records = self.memory_store.recent(category=cleaned, limit=5)
        if not records:
            return "I do not have any saved memory for that yet."
        parts = [
            f"{item.get('timestamp', '')}: [{item.get('category', 'memory')}] "
            f"{item.get('query', '')} -> {item.get('detail', '')}"
            for item in records
        ]
        return "Recent memory: " + " | ".join(parts)
