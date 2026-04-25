from __future__ import annotations

import os
import platform
import subprocess

import psutil

from src.dhruv.commands.base import Command


class SystemStatusCommand(Command):
    def matches(self, user_input: str) -> bool:
        keywords = (
            "system status",
            "system condition",
            "system health",
            "cpu",
            "ram",
            "memory",
            "battery",
        )
        return any(keyword in user_input for keyword in keywords)

    def execute(self, user_input: str) -> str:
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        cpu_name = _cpu_name()
        battery_text = (
            f"Battery is at {battery.percent}% and plugged in is {battery.power_plugged}."
            if battery
            else "Battery data is not available on this machine."
        )
        return (
            f"System: {platform.system()} {platform.release()}. "
            f"CPU type is {cpu_name}. "
            f"CPU usage is {cpu}%. "
            f"Memory usage is {memory.percent}%. "
            f"{battery_text}"
        )


class OpenExplorerCommand(Command):
    def matches(self, user_input: str) -> bool:
        return (
            ("open" in user_input or "start" in user_input)
            and ("explorer" in user_input or "file explorer" in user_input or "files" in user_input)
        )

    def execute(self, user_input: str) -> str:
        try:
            subprocess.Popen(["explorer.exe"])
            return "Opening File Explorer."
        except OSError:
            return "I could not open File Explorer on this system."


def _cpu_name() -> str:
    processor = platform.processor().strip()
    if processor:
        return processor
    env_processor = os.getenv("PROCESSOR_IDENTIFIER", "").strip()
    if env_processor:
        return env_processor
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
            capture_output=True,
            text=True,
            check=False,
        )
        value = result.stdout.strip()
        if value:
            return value
    except OSError:
        pass
    return "Unknown processor"
