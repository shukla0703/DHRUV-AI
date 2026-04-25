from __future__ import annotations

from datetime import datetime
import math
import time

from PyQt5.QtCore import QDateTime, QPointF, QRectF, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.dhruv.assistant import Assistant
from src.dhruv.config import settings
from src.dhruv.services.memory import MemoryStore
from src.dhruv.services.speech import Listener
from src.dhruv.theme import APP_NAME, APP_TAGLINE, LOGO_PATH, TOKENS


AETHER_STYLESHEET = """
QMainWindow {
    background: %(bg_base)s;
}
QWidget {
    background: transparent;
    color: %(text_primary)s;
    font-family: "Segoe UI";
}
QFrame#panel {
    background-color: %(bg_panel)s;
    border: 1px solid %(accent_line)s;
    border-radius: 24px;
}
QFrame#softPanel {
    background-color: %(bg_panel_soft)s;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
}
QFrame#heroPanel {
    background-color: %(bg_hero)s;
    border: 1px solid rgba(47, 208, 255, 0.26);
    border-radius: 30px;
}
QFrame#metricCard {
    background-color: rgba(10, 22, 42, 228);
    border: 1px solid rgba(47, 208, 255, 0.16);
    border-radius: 22px;
}
QLabel#heroTitle {
    color: %(accent_white)s;
    font-size: 42px;
    font-weight: 700;
    letter-spacing: 3px;
}
QLabel#heroSubTitle {
    color: %(text_muted)s;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
}
QLabel#sectionTitle {
    color: %(accent_cyan)s;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}
QLabel#clockBadge {
    color: %(accent_white)s;
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(47, 208, 255, 0.18);
    border-radius: 14px;
    padding: 10px 14px;
    font-size: 14px;
    font-weight: 600;
}
QTextEdit {
    background-color: rgba(6, 12, 24, 230);
    border: 1px solid rgba(47, 208, 255, 0.12);
    border-radius: 20px;
    padding: 14px;
    color: %(text_primary)s;
    font-size: 13px;
    selection-background-color: %(accent_blue)s;
}
QLineEdit {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(47, 208, 255, 0.16);
    border-radius: 18px;
    padding: 14px 16px;
    color: %(accent_white)s;
    font-size: 15px;
}
QLineEdit:focus {
    border: 1px solid rgba(47, 208, 255, 0.5);
}
QPushButton {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(47, 208, 255, 0.14);
    border-radius: 16px;
    color: %(accent_white)s;
    font-size: 13px;
    font-weight: 700;
    padding: 12px 18px;
}
QPushButton:hover {
    background-color: rgba(47, 208, 255, 0.12);
}
QPushButton:pressed {
    background-color: rgba(22, 132, 255, 0.24);
}
QPushButton#accentButton {
    background-color: %(button_primary)s;
    border: 1px solid rgba(246, 251, 255, 0.20);
}
QPushButton#secondaryAccentButton {
    background-color: %(button_secondary)s;
    border: 1px solid rgba(47, 208, 255, 0.16);
}
QPushButton#dangerButton {
    background-color: %(button_danger)s;
    border: 1px solid rgba(255, 178, 190, 45);
}
QCheckBox {
    color: %(text_primary)s;
    spacing: 10px;
    font-size: 13px;
    font-weight: 600;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 1px solid rgba(47, 208, 255, 0.22);
    background-color: rgba(255, 255, 255, 0.09);
}
QCheckBox::indicator:checked {
    background-color: %(accent_cyan)s;
    border-color: rgba(246, 251, 255, 0.32);
}
""" % TOKENS


class VoiceWorker(QThread):
    heard = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, assistant: Assistant) -> None:
        super().__init__()
        self.assistant = assistant

    def run(self) -> None:
        spoken = self.assistant.listen_once()
        if spoken is None:
            self.failed.emit("Microphone listening is unavailable right now.")
            return
        if not spoken:
            self.failed.emit("I did not catch that. Please try again.")
            return
        self.heard.emit(spoken)


class WakeWordWorker(QThread):
    status = pyqtSignal(str)
    heard = pyqtSignal(str)
    command = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, assistant: Assistant) -> None:
        super().__init__()
        self.assistant = assistant
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        wake_word = settings.wake_word.lower().strip()
        self.status.emit(f"Wake word mode armed for '{wake_word}'")
        first_pass = True
        session_active_until = 0.0
        while self._running:
            self._wait_for_speech_output()
            spoken = self.assistant.listen_once(
                timeout=3,
                phrase_time_limit=5,
                adjust_for_noise=first_pass,
            )
            first_pass = False
            if not self._running:
                break
            if spoken is None:
                self.failed.emit("Wake-word listening is unavailable right now.")
                break
            if not spoken:
                continue

            normalized = spoken.lower()
            self.heard.emit(spoken)
            if time.time() < session_active_until:
                if normalized in {"stop listening", "go idle", "cancel"}:
                    session_active_until = 0.0
                    self.status.emit("Continuous conversation window closed.")
                    continue
                self.command.emit(normalized)
                session_active_until = time.time() + 12
                continue

            if not Listener.contains_wake_word(normalized, wake_word):
                continue

            trailing = normalized.split(wake_word, 1)[1].strip(" ,.!?")
            if trailing:
                self.command.emit(trailing)
                session_active_until = time.time() + 12
                continue

            self.status.emit(f"Wake word detected. Awaiting command after '{wake_word}'.")
            self._wait_for_speech_output()
            follow_up = self.assistant.listen_once(
                timeout=5,
                phrase_time_limit=7,
                adjust_for_noise=False,
            )
            if not self._running:
                break
            if follow_up is None:
                self.failed.emit("Microphone stopped responding while waiting for a command.")
                break
            if not follow_up:
                self.status.emit("Wake word detected, but no command followed.")
                continue
            self.command.emit(follow_up)
            session_active_until = time.time() + 12

    def _wait_for_speech_output(self) -> None:
        while self._running and self.assistant.speaker.is_speaking:
            time.sleep(0.1)


class HaloWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.angle = 0
        self.energy = 35
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)
        self.setMinimumSize(300, 300)

    def set_energy(self, value: int) -> None:
        self.energy = max(0, min(100, value))
        self.update()

    def _tick(self) -> None:
        self.angle = (self.angle + 2) % 360
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        center = self.rect().center()
        glow = QLinearGradient(0, 0, self.width(), self.height())
        glow.setColorAt(0.0, QColor(22, 132, 255, 44))
        glow.setColorAt(0.5, QColor(47, 208, 255, 30))
        glow.setColorAt(1.0, QColor(246, 251, 255, 24))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, 118, 118)

        rings = [
            (122, QColor(246, 251, 255, 90), 2),
            (98, QColor(47, 208, 255, 72), 2),
            (74, QColor(22, 132, 255, 52), 1),
            (52, QColor(246, 251, 255, 110), 2),
        ]
        for radius, color, width in rings:
            painter.setPen(QPen(color, width))
            painter.drawEllipse(center, radius, radius)

        painter.save()
        painter.translate(center)
        painter.rotate(self.angle)
        painter.setPen(QPen(QColor(246, 251, 255, 150), 3))
        painter.drawArc(-116, -116, 232, 232, 20 * 16, 72 * 16)
        painter.setPen(QPen(QColor(47, 208, 255, 150), 2))
        painter.drawArc(-92, -92, 184, 184, 190 * 16, 62 * 16)
        painter.setPen(QPen(QColor(22, 132, 255, 150), 2))
        painter.drawArc(-68, -68, 136, 136, 90 * 16, 88 * 16)
        painter.restore()

        core_radius = 26 + self.energy // 4
        painter.setBrush(QColor(246, 251, 255, 120))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, core_radius, core_radius)

        painter.setPen(QPen(QColor(246, 251, 255), 1))
        painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, settings.assistant_name.upper())


class RibbonWave(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.phase = 0
        self.activity = 24
        self.listening = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(55)
        self.setMinimumHeight(84)

    def set_mode(self, listening: bool) -> None:
        self.listening = listening
        self.activity = 74 if listening else 24
        self.update()

    def pulse(self, value: int) -> None:
        self.activity = max(self.activity, min(100, value))
        self.update()

    def _tick(self) -> None:
        self.phase = (self.phase + 7) % 360
        target = 74 if self.listening else 24
        if self.activity > target:
            self.activity -= 2
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        path = QPainterPath()
        width = self.width()
        height = self.height()
        base = height / 2
        amplitude = 10 + (self.activity / 100) * 24
        path.moveTo(0, base)
        for x in range(0, width + 1, 8):
            wave = math.sin((x / 36) + math.radians(self.phase))
            offset = wave * amplitude
            path.lineTo(x, base + offset)

        painter.setPen(QPen(QColor(246, 251, 255, 200), 3))
        painter.drawPath(path)

        secondary = QPainterPath()
        secondary.moveTo(0, base)
        for x in range(0, width + 1, 8):
            wave = math.sin((x / 28) + math.radians(self.phase + 120))
            offset = wave * (amplitude * 0.65)
            secondary.lineTo(x, base + offset)
        painter.setPen(QPen(QColor(47, 208, 255, 140), 2))
        painter.drawPath(secondary)


class VaultBackground(QWidget):
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(3, 8, 23))
        gradient.setColorAt(0.32, QColor(5, 13, 35))
        gradient.setColorAt(0.72, QColor(7, 17, 42))
        gradient.setColorAt(1.0, QColor(2, 6, 18))
        painter.fillRect(self.rect(), gradient)

        painter.setPen(QPen(QColor(246, 251, 255, 9), 1))
        for y in range(0, self.height(), 24):
            painter.drawLine(0, y, self.width(), y)

        painter.setPen(QPen(QColor(47, 208, 255, 18), 1))
        for x in range(0, self.width(), 28):
            painter.drawLine(x, 0, x, self.height())

        painter.setBrush(QColor(22, 132, 255, 22))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(self.width() * 0.12, self.height() * 0.18), 180, 180)
        painter.setBrush(QColor(246, 251, 255, 16))
        painter.drawEllipse(QPointF(self.width() * 0.88, self.height() * 0.22), 150, 150)


class MetricCard(QFrame):
    def __init__(self, title: str, value: str, detail: str, accent: str) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {accent};"
        )
        self.detail_label = QLabel(detail)
        self.detail_label.setStyleSheet("font-size: 12px; color: #d0dcea;")

        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)

    def set_value(self, value: str, detail: str) -> None:
        self.value_label.setText(value)
        self.detail_label.setText(detail)


class InfoStrip(QFrame):
    def __init__(self, title: str, value: str) -> None:
        super().__init__()
        self.setObjectName("softPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        header = QLabel(title)
        header.setObjectName("sectionTitle")
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("font-size: 14px; color: #eef4f7; font-weight: 600;")
        layout.addWidget(header)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class AetherWindow(QMainWindow):
    def __init__(
        self,
        assistant: Assistant,
        arm_wake_mode: bool = False,
        start_minimized: bool = False,
    ) -> None:
        super().__init__()
        self.assistant = assistant
        self.memory_store = MemoryStore()
        self.arm_wake_mode_on_launch = arm_wake_mode
        self.start_minimized = start_minimized
        self.voice_worker: VoiceWorker | None = None
        self.wake_word_worker: WakeWordWorker | None = None
        self.command_count = 0
        self.setWindowTitle(APP_NAME)
        self.resize(1360, 860)
        self.setMinimumSize(1160, 720)
        self.setStyleSheet(AETHER_STYLESHEET)
        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self._build_ui()
        self._wire_timers()
        self.add_log("SYSTEM", self.assistant.greeting())
        self.refresh_memory_panel()
        if self.arm_wake_mode_on_launch:
            QTimer.singleShot(0, self.start_wake_mode_from_launch)
        if self.start_minimized:
            QTimer.singleShot(250, self.showMinimized)
        self._sync_halo()

    def _build_ui(self) -> None:
        central = VaultBackground()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(24, 22, 24, 24)
        root.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(18)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(160, 160)
        self.logo_label.setAlignment(Qt.AlignCenter)
        if LOGO_PATH.exists():
            pixmap = QPixmap(str(LOGO_PATH)).scaled(
                160,
                160,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.logo_label.setPixmap(pixmap)
        title_col.addWidget(self.logo_label, alignment=Qt.AlignLeft)

        title = QLabel(APP_NAME)
        title.setObjectName("heroTitle")
        subtitle = QLabel(APP_TAGLINE.upper())
        subtitle.setObjectName("heroSubTitle")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        hero_layout.addLayout(title_col)
        hero_layout.addStretch()

        self.date_label = QLabel()
        self.date_label.setObjectName("clockBadge")
        self.time_label = QLabel()
        self.time_label.setObjectName("clockBadge")
        hero_layout.addWidget(self.date_label)
        hero_layout.addWidget(self.time_label)
        root.addWidget(hero)

        strips = QHBoxLayout()
        strips.setSpacing(14)
        initial_mode = "Wake Listening" if self.arm_wake_mode_on_launch else "Manual Control"
        self.mode_strip = InfoStrip("Mode", initial_mode)
        self.wake_strip = InfoStrip("Wake Word", settings.wake_word.upper())
        energy_text = "Focused" if self.arm_wake_mode_on_launch else "Ready"
        self.energy_strip = InfoStrip("Energy", energy_text)
        strips.addWidget(self.mode_strip)
        strips.addWidget(self.wake_strip)
        strips.addWidget(self.energy_strip)

        toggle_panel = QFrame()
        toggle_panel.setObjectName("softPanel")
        toggle_layout = QHBoxLayout(toggle_panel)
        toggle_layout.setContentsMargins(16, 12, 16, 12)
        toggle_layout.setSpacing(12)
        toggle_title = QLabel("Always-On Wake Mode")
        toggle_title.setObjectName("sectionTitle")
        self.always_on_toggle = QCheckBox("Enabled")
        self.always_on_toggle.stateChanged.connect(self.toggle_wake_word_mode)
        toggle_layout.addWidget(toggle_title)
        toggle_layout.addStretch()
        toggle_layout.addWidget(self.always_on_toggle)
        strips.addWidget(toggle_panel)
        root.addLayout(strips)

        metrics = QHBoxLayout()
        metrics.setSpacing(14)
        self.command_metric = MetricCard("Command Flow", "0", "Awaiting input", "#ffd9b3")
        self.mode_metric = MetricCard("Assist State", "Manual", "Typed or click", "#b0cff5")
        self.mic_metric = MetricCard("Mic Channel", "Idle", "Standing by", "#b7f0d7")
        metrics.addWidget(self.command_metric)
        metrics.addWidget(self.mode_metric)
        metrics.addWidget(self.mic_metric)
        root.addLayout(metrics)

        body = QGridLayout()
        body.setHorizontalSpacing(18)
        body.setVerticalSpacing(18)

        left_panel = self._build_left_panel()
        center_panel = self._build_center_panel()
        right_panel = self._build_right_panel()

        body.addWidget(left_panel, 0, 0)
        body.addWidget(center_panel, 0, 1)
        body.addWidget(right_panel, 0, 2)
        body.setColumnStretch(0, 2)
        body.setColumnStretch(1, 3)
        body.setColumnStretch(2, 2)
        root.addLayout(body, stretch=1)

        lower = QHBoxLayout()
        lower.setSpacing(18)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(240)
        self.log.setStyleSheet(
            "QTextEdit {"
            "background-color: rgba(8, 15, 24, 225);"
            "border: 1px solid rgba(47, 208, 255, 0.12);"
            "border-radius: 20px;"
            "padding: 14px;"
            "font-family: Consolas;"
            "font-size: 12px;"
            "color: #f7fbff;"
            "}"
        )
        lower.addWidget(self.log, stretch=3)

        lower.addWidget(self._build_console_panel(), stretch=2)
        root.addLayout(lower, stretch=1)

    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Guidance Grid")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        items = [
            "Command center UI built around the DHRUV star-mark and orbital motion language",
            "Voice and typed control in one guided desktop surface",
            "Wake word mode with continuous conversation windows",
            "Open any website, search the web, and launch common apps",
            "AI memory, system insights, and action-first responses",
        ]
        for item in items:
            label = QLabel(f"- {item}")
            label.setWordWrap(True)
            label.setStyleSheet("font-size: 13px; color: #d9e3eb; line-height: 1.45;")
            layout.addWidget(label)

        quick = QFrame()
        quick.setObjectName("softPanel")
        quick_layout = QVBoxLayout(quick)
        quick_layout.setContentsMargins(14, 12, 14, 12)
        quick_layout.setSpacing(8)
        header = QLabel("Try Saying")
        header.setObjectName("sectionTitle")
        quick_layout.addWidget(header)
        for example in (
            f"{settings.wake_word} open reddit.com",
            "open huggingface",
            "what cpu do i have",
            "recall my recent memory",
        ):
            line = QLabel(example)
            line.setStyleSheet("font-size: 12px; color: #f7fbff;")
            quick_layout.addWidget(line)
        layout.addWidget(quick)
        layout.addStretch()
        return panel

    def _build_center_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Star Core")
        title.setObjectName("sectionTitle")
        layout.addWidget(title, alignment=Qt.AlignHCenter)

        self.halo_widget = HaloWidget()
        layout.addWidget(self.halo_widget, alignment=Qt.AlignCenter)

        self.status_label = QLabel("Status: ready to guide and act")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "font-size: 15px; color: #f7fbff; font-weight: 600;"
        )
        layout.addWidget(self.status_label)

        self.waveform = RibbonWave()
        self.waveform.set_mode(self.arm_wake_mode_on_launch)
        layout.addWidget(self.waveform)

        self.wave_label = QLabel(
            "Voice ribbon standing by" if not self.arm_wake_mode_on_launch else "Wake ribbon active"
        )
        self.wave_label.setAlignment(Qt.AlignCenter)
        self.wave_label.setStyleSheet(
            "font-size: 12px; color: #b9c9dc; letter-spacing: 1px;"
        )
        layout.addWidget(self.wave_label)
        layout.addStretch()
        return panel

    def _build_right_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        header = QLabel("Memory Vault")
        header.setObjectName("sectionTitle")
        layout.addWidget(header)

        self.memory_panel = QTextEdit()
        self.memory_panel.setReadOnly(True)
        self.memory_panel.setMinimumHeight(250)
        layout.addWidget(self.memory_panel)

        status_box = QFrame()
        status_box.setObjectName("softPanel")
        status_layout = QVBoxLayout(status_box)
        status_layout.setContentsMargins(14, 12, 14, 12)
        status_layout.setSpacing(8)
        chip_title = QLabel("Brand Mode")
        chip_title.setObjectName("sectionTitle")
        chip_body = QLabel(
            "DHRUV AI uses a midnight-blue, cyan, and white orbital theme anchored to the provided star logo."
        )
        chip_body.setWordWrap(True)
        chip_body.setStyleSheet("font-size: 12px; color: #e7eef3; line-height: 1.4;")
        status_layout.addWidget(chip_title)
        status_layout.addWidget(chip_body)
        layout.addWidget(status_box)
        layout.addStretch()
        return panel

    def _build_console_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Mission Console")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Ask DHRUV AI to do something...")
        self.command_input.returnPressed.connect(self.submit_text_command)
        layout.addWidget(self.command_input)

        row = QHBoxLayout()
        self.listen_button = QPushButton("Listen")
        self.listen_button.setObjectName("accentButton")
        self.listen_button.clicked.connect(self.start_voice_capture)
        self.run_button = QPushButton("Run Command")
        self.run_button.setObjectName("secondaryAccentButton")
        self.run_button.clicked.connect(self.submit_text_command)
        self.arm_button = QPushButton(
            "Disarm Wake Mode" if self.arm_wake_mode_on_launch else "Arm Wake Mode"
        )
        self.arm_button.setObjectName("dangerButton")
        self.arm_button.clicked.connect(self.toggle_always_on_button)
        row.addWidget(self.listen_button)
        row.addWidget(self.run_button)
        row.addWidget(self.arm_button)
        layout.addLayout(row)

        quick_row = QGridLayout()
        actions = [
            ("Open Explorer", "open explorer"),
            ("System Status", "check system status"),
            ("Open Website", "open reddit.com"),
            ("Recall Memory", "recall recent memory"),
        ]
        for index, (label, command) in enumerate(actions):
            button = QPushButton(label)
            button.clicked.connect(lambda _, cmd=command: self.execute_command(cmd))
            quick_row.addWidget(button, index // 2, index % 2)
        layout.addLayout(quick_row)

        footer = QFrame()
        footer.setObjectName("softPanel")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 10, 12, 10)
        footer_title = QLabel("Wake Pattern")
        footer_title.setObjectName("sectionTitle")
        footer_body = QLabel(
            f"Say '{settings.wake_word}' followed by your request, for example '{settings.wake_word} open youtube'."
        )
        footer_body.setWordWrap(True)
        footer_body.setStyleSheet("font-size: 12px; color: #e7eef3; line-height: 1.45;")
        footer_layout.addWidget(footer_title)
        footer_layout.addWidget(footer_body)
        layout.addWidget(footer)
        layout.addStretch()
        return panel

    def _wire_timers(self) -> None:
        self.update_clock()
        clock = QTimer(self)
        clock.timeout.connect(self.update_clock)
        clock.start(1000)
        self.clock_timer = clock

        memory_refresh = QTimer(self)
        memory_refresh.timeout.connect(self.refresh_memory_panel)
        memory_refresh.start(6000)
        self.memory_timer = memory_refresh

    def update_clock(self) -> None:
        now = QDateTime.currentDateTime()
        self.date_label.setText(f"DATE  {now.toString('dd MMM yyyy')}")
        self.time_label.setText(f"TIME  {now.toString('hh:mm:ss AP')}")

    def refresh_memory_panel(self) -> None:
        records = self.memory_store.recent(limit=6)
        if not records:
            self.memory_panel.setPlainText("No saved memory yet. Searches, opened sites, and assistant replies will appear here.")
            return
        lines = []
        for item in reversed(records):
            stamp = item.get("timestamp", "")
            category = item.get("category", "memory").replace("_", " ").title()
            query = item.get("query", "")
            detail = item.get("detail", "")
            lines.append(f"[{stamp}] {category}\n{query}\n{detail}\n")
        self.memory_panel.setPlainText("\n".join(lines).strip())

    def add_log(self, speaker: str, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "SYSTEM": "#2fd0ff",
            "YOU": "#ffffff",
            "HEARD": "#c8f5ff",
            "WAKE": "#7fc9ff",
            settings.assistant_name.upper(): "#f7fbff",
            "AMBIENT": "#b9c9dc",
        }
        color = color_map.get(speaker, "#eef5f8")
        self.log.append(
            f'<span style="color:#7ca7d9;">[{stamp}]</span> '
            f'<span style="color:{color}; font-weight:700;">{speaker}</span> '
            f'<span style="color:#eef5f8;">{message}</span>'
        )

    def submit_text_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            self.status_label.setText("Status: waiting for your command")
            return
        self.command_input.clear()
        self.execute_command(command)

    def execute_command(self, command: str) -> None:
        self.command_count += 1
        self.add_log("YOU", command)
        self.status_label.setText(f"Status: executing '{command}'")
        self.waveform.pulse(92)
        self.wave_label.setText("Voice ribbon processing")
        self.energy_strip.set_value("Elevated")
        self.command_metric.set_value(str(self.command_count), "Processing request")
        self.mic_metric.set_value("Live", "Command processing")
        response = self.assistant.process_command(command)
        self.assistant.speaker.say(response)
        self.add_log(settings.assistant_name.upper(), response)
        self.status_label.setText(f"Status: {response}")
        self.energy_strip.set_value("Ready")
        self.wave_label.setText("Voice ribbon steady")
        self.command_metric.set_value(str(self.command_count), "Response delivered")
        self.mic_metric.set_value("Idle", "Awaiting input")
        self.refresh_memory_panel()
        self._sync_halo()

    def start_voice_capture(self) -> None:
        if self.voice_worker is not None and self.voice_worker.isRunning():
            return
        self.status_label.setText("Status: listening for one command")
        self.add_log("SYSTEM", "Voice capture started")
        self.mode_strip.set_value("Manual Voice")
        self.wave_label.setText("Voice ribbon live")
        self.waveform.set_mode(True)
        self.mode_metric.set_value("Voice", "Single capture")
        self.mic_metric.set_value("Open", "Listening now")
        self.listen_button.setEnabled(False)
        self.voice_worker = VoiceWorker(self.assistant)
        self.voice_worker.heard.connect(self.on_voice_heard)
        self.voice_worker.failed.connect(self.on_voice_failed)
        self.voice_worker.finished.connect(self._on_manual_voice_finished)
        self.voice_worker.start()

    def on_voice_heard(self, command: str) -> None:
        self.add_log("HEARD", command)
        self.waveform.pulse(100)
        self._sync_halo()
        self.execute_command(command)

    def on_voice_failed(self, message: str) -> None:
        self.add_log("SYSTEM", message)
        self.status_label.setText(f"Status: {message}")
        self.wave_label.setText("Voice ribbon quiet")
        self.mic_metric.set_value("Quiet", "Retry when ready")

    def _on_manual_voice_finished(self) -> None:
        self.listen_button.setEnabled(True)
        if self.wake_word_worker is not None and self.wake_word_worker.isRunning():
            self.mode_strip.set_value("Wake Listening")
            self.waveform.set_mode(True)
            self.mode_metric.set_value("Wake", "Persistent listening")
            self.mic_metric.set_value("Open", "Wake monitoring")
        else:
            self.mode_strip.set_value("Manual Control")
            self.waveform.set_mode(False)
            self.mode_metric.set_value("Manual", "Typed or click")
            self.mic_metric.set_value("Idle", "Awaiting input")
        self._sync_listen_controls()
        self._sync_halo()

    def toggle_always_on_button(self) -> None:
        self.always_on_toggle.setChecked(not self.always_on_toggle.isChecked())

    def start_wake_mode_from_launch(self) -> None:
        if self.wake_word_worker is not None and self.wake_word_worker.isRunning():
            return
        self.always_on_toggle.blockSignals(True)
        self.always_on_toggle.setChecked(True)
        self.always_on_toggle.blockSignals(False)
        self.start_wake_word_mode()

    def toggle_wake_word_mode(self, state: int) -> None:
        _ = state
        if self.always_on_toggle.isChecked():
            self.start_wake_word_mode()
        else:
            self.stop_wake_word_mode()

    def start_wake_word_mode(self) -> None:
        if self.wake_word_worker is not None and self.wake_word_worker.isRunning():
            return
        self.mode_strip.set_value("Wake Listening")
        self.status_label.setText(f"Status: listening for '{settings.wake_word}'")
        self.wave_label.setText("Wake ribbon active")
        self.waveform.set_mode(True)
        self.mode_metric.set_value("Wake", settings.wake_word.upper())
        self.mic_metric.set_value("Open", "Persistent listening")
        self.arm_button.setText("Disarm Wake Mode")
        self.energy_strip.set_value("Focused")
        self._sync_listen_controls()
        self.add_log("SYSTEM", f"Wake-word mode enabled for '{settings.wake_word}'")
        self.wake_word_worker = WakeWordWorker(self.assistant)
        self.wake_word_worker.status.connect(self.on_wake_status)
        self.wake_word_worker.heard.connect(self.on_wake_heard)
        self.wake_word_worker.command.connect(self.on_wake_command)
        self.wake_word_worker.failed.connect(self.on_wake_failed)
        self.wake_word_worker.finished.connect(self.on_wake_finished)
        self.wake_word_worker.start()
        self._sync_listen_controls()
        self._sync_halo()

    def stop_wake_word_mode(self) -> None:
        if self.wake_word_worker is not None:
            self.wake_word_worker.stop()
        self.mode_strip.set_value("Manual Control")
        self.status_label.setText("Status: wake mode offline")
        self.wave_label.setText("Voice ribbon steady")
        self.waveform.set_mode(False)
        self.mode_metric.set_value("Manual", "Typed or click")
        self.mic_metric.set_value("Idle", "Wake mode off")
        self.energy_strip.set_value("Ready")
        self.arm_button.setText("Arm Wake Mode")
        self._sync_listen_controls()
        self.add_log("SYSTEM", "Wake-word mode disabled")
        self._sync_halo()

    def on_wake_status(self, message: str) -> None:
        self.status_label.setText(f"Status: {message}")
        self.add_log("SYSTEM", message)
        self.waveform.pulse(66)
        self.command_metric.set_value(str(self.command_count), "Wake patrol")
        self._sync_halo()

    def on_wake_heard(self, transcript: str) -> None:
        self.add_log("AMBIENT", transcript)
        self.waveform.pulse(82)
        self._sync_halo()

    def on_wake_command(self, command: str) -> None:
        self.add_log("WAKE", command)
        self.status_label.setText(f"Status: wake command '{command}'")
        self.waveform.pulse(100)
        self.command_metric.set_value(str(self.command_count), "Wake detected")
        self._sync_halo()
        self.execute_command(command)

    def on_wake_failed(self, message: str) -> None:
        self.add_log("SYSTEM", message)
        self.status_label.setText(f"Status: {message}")
        self.always_on_toggle.blockSignals(True)
        self.always_on_toggle.setChecked(False)
        self.always_on_toggle.blockSignals(False)
        self.mode_strip.set_value("Manual Control")
        self.waveform.set_mode(False)
        self.mode_metric.set_value("Manual", "Typed or click")
        self.mic_metric.set_value("Fault", "Check microphone")
        self.arm_button.setText("Arm Wake Mode")
        self._sync_listen_controls()
        self._sync_halo()

    def on_wake_finished(self) -> None:
        if self.always_on_toggle.isChecked():
            return
        self.mode_strip.set_value("Manual Control")
        self.waveform.set_mode(False)
        self.arm_button.setText("Arm Wake Mode")
        self._sync_listen_controls()
        self._sync_halo()

    def _sync_halo(self) -> None:
        energy = 80 if self.waveform.listening else 36
        self.halo_widget.set_energy(energy)

    def _sync_listen_controls(self) -> None:
        wake_live = self.wake_word_worker is not None and self.wake_word_worker.isRunning()
        self.listen_button.setEnabled(not wake_live)
        self.listen_button.setText("Wake Mode Live" if wake_live else "Listen")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.wake_word_worker is not None:
            self.wake_word_worker.stop()
            self.wake_word_worker.wait(1000)
        if self.voice_worker is not None and self.voice_worker.isRunning():
            self.voice_worker.wait(1000)
        super().closeEvent(event)


def launch_gui(
    assistant: Assistant,
    arm_wake_mode: bool = False,
    start_minimized: bool = False,
) -> None:
    app = QApplication.instance() or QApplication([])
    window = AetherWindow(
        assistant,
        arm_wake_mode=arm_wake_mode,
        start_minimized=start_minimized,
    )
    window.show()
    app.exec_()
