"""Main OfflineMedia desktop window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from app.core.hardware import describe
from app.core.paths import ensure_directories
from app.engines.comfyui_client import ComfyUIClient
from app.video.ffmpeg import FFmpeg


class MainWindow(QMainWindow):
    """Primary application shell with the first generation controls."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OfflineMedia")
        self.resize(1280, 800)
        self.setMinimumSize(1000, 650)
        self.paths = ensure_directories()
        self.comfy = ComfyUIClient()
        self.ffmpeg = FFmpeg()
        self._pages: dict[str, QWidget] = {}
        self._build_ui()
        self._refresh_status()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(20, 24, 20, 20)
        side_layout.setSpacing(8)

        title = QLabel("OfflineMedia", objectName="brand")
        subtitle = QLabel("LOCAL VIDEO STUDIO", objectName="subtitle")
        side_layout.addWidget(title)
        side_layout.addWidget(subtitle)
        side_layout.addSpacing(24)

        for key, label in (
            ("home", "Home"),
            ("text", "Text → Video"),
            ("image", "Image → Video"),
            ("sequence", "Image Sequence"),
            ("projects", "Projects"),
        ):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page=key: self._show_page(page))
            side_layout.addWidget(button)

        side_layout.addStretch()
        settings = QPushButton("Settings")
        settings.clicked.connect(lambda: self._show_page("settings"))
        side_layout.addWidget(settings)

        self.stack = QStackedWidget()
        self._add_page("home", self._home_page())
        self._add_page("text", self._generator_page("Text → Video", image_mode=False))
        self._add_page("image", self._generator_page("Image → Video", image_mode=True))
        self._add_page("sequence", self._sequence_page())
        self._add_page("projects", self._projects_page())
        self._add_page("settings", self._settings_page())

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self._apply_style()

    def _add_page(self, key: str, widget: QWidget) -> None:
        self._pages[key] = widget
        self.stack.addWidget(widget)

    def _show_page(self, key: str) -> None:
        self.stack.setCurrentWidget(self._pages[key])

    def _home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        title = QLabel("Create", objectName="page_title")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(18)
        cards = [
            ("Text → Video", "Generate a local AI video from a prompt.", "text"),
            ("Image → Video", "Animate a still image with a local model.", "image"),
            ("Image Sequence", "Build a video from multiple images.", "sequence"),
        ]
        for index, (name, description, target) in enumerate(cards):
            card = QFrame(objectName="card")
            card_layout = QVBoxLayout(card)
            card_title = QLabel(name, objectName="card_title")
            desc = QLabel(description)
            desc.setWordWrap(True)
            open_button = QPushButton("Open")
            open_button.clicked.connect(lambda checked=False, page=target: self._show_page(page))
            card_layout.addWidget(card_title)
            card_layout.addWidget(desc)
            card_layout.addStretch()
            card_layout.addWidget(open_button)
            grid.addWidget(card, 0, index)
        layout.addLayout(grid)
        layout.addStretch()
        self.status_label = QLabel("Checking local engines…", objectName="status")
        layout.addWidget(self.status_label)
        return page

    def _generator_page(self, title_text: str, image_mode: bool) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.addWidget(QLabel(title_text, objectName="page_title"))

        if image_mode:
            row = QHBoxLayout()
            self.image_path = QLineEdit()
            self.image_path.setPlaceholderText("Select an input image…")
            browse = QPushButton("Browse")
            browse.clicked.connect(self._choose_image)
            row.addWidget(self.image_path)
            row.addWidget(browse)
            layout.addLayout(row)

        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("Describe the video you want to generate…")
        self.prompt.setMinimumHeight(160)
        layout.addWidget(self.prompt)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Width"))
        width = QSpinBox()
        width.setRange(256, 2048)
        width.setSingleStep(64)
        width.setValue(512)
        controls.addWidget(width)
        controls.addWidget(QLabel("Height"))
        height = QSpinBox()
        height.setRange(256, 2048)
        height.setSingleStep(64)
        height.setValue(512)
        controls.addWidget(height)
        controls.addWidget(QLabel("Frames"))
        frames = QSpinBox()
        frames.setRange(8, 200)
        frames.setValue(49)
        controls.addWidget(frames)
        controls.addStretch()
        layout.addLayout(controls)

        self.generate_status = QLabel("Ready")
        generate = QPushButton("Generate Video")
        generate.setObjectName("primary")
        generate.clicked.connect(lambda: self._generation_requested(title_text))
        layout.addWidget(self.generate_status)
        layout.addWidget(generate)
        layout.addStretch()
        return page

    def _sequence_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.addWidget(QLabel("Image Sequence", objectName="page_title"))
        self.sequence_label = QLabel("No images selected")
        layout.addWidget(self.sequence_label)
        choose = QPushButton("Choose Images")
        choose.clicked.connect(self._choose_sequence)
        layout.addWidget(choose)
        layout.addStretch()
        return page

    def _projects_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.addWidget(QLabel("Projects", objectName="page_title"))
        layout.addWidget(QLabel(f"Project storage: {self.paths['projects']}"))
        layout.addStretch()
        return page

    def _settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.addWidget(QLabel("Settings", objectName="page_title"))
        info = describe()
        for key, value in info.items():
            layout.addWidget(QLabel(f"{key.upper()}: {value}"))
        layout.addWidget(QLabel(f"ComfyUI: {self.comfy.base_url}"))
        layout.addWidget(QLabel(f"FFmpeg: {'available' if self.ffmpeg.available else 'not found'}"))
        layout.addStretch()
        return page

    def _choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self.image_path.setText(path)

    def _choose_sequence(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select images", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        self.sequence_label.setText(f"{len(paths)} images selected" if paths else "No images selected")

    def _generation_requested(self, mode: str) -> None:
        prompt = self.prompt.toPlainText().strip()
        if not prompt:
            self.generate_status.setText("Enter a prompt first.")
            return
        if not self.comfy.is_available():
            self.generate_status.setText("ComfyUI is not running. Generation will be enabled after the local engine is connected.")
            return
        self.generate_status.setText(f"{mode} request accepted. Workflow integration is next.")

    def _refresh_status(self) -> None:
        comfy = "connected" if self.comfy.is_available() else "not connected"
        ffmpeg = "available" if self.ffmpeg.available else "not installed"
        self.status_label.setText(f"ComfyUI: {comfy}  •  FFmpeg: {ffmpeg}")

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #111318; }
            #sidebar { background: #171a20; border-right: 1px solid #282c35; }
            #brand { color: #f2f4f8; font-size: 24px; font-weight: 700; }
            #subtitle { color: #747b88; font-size: 10px; letter-spacing: 2px; }
            QPushButton { background: #1d2129; color: #dfe3ea; border: 1px solid #2b303a; border-radius: 8px; padding: 11px; text-align: left; }
            QPushButton:hover { background: #252a34; }
            #primary { background: #3a6ff7; color: white; text-align: center; font-weight: 700; }
            #primary:hover { background: #4a7cff; }
            #page_title { color: #f2f4f8; font-size: 30px; font-weight: 700; }
            #card { background: #191d24; border: 1px solid #292e38; border-radius: 12px; min-height: 170px; }
            #card_title { color: #f2f4f8; font-size: 17px; font-weight: 600; }
            QLabel { color: #aab1bd; font-size: 13px; }
            QPlainTextEdit, QLineEdit, QSpinBox { background: #191d24; color: #e6e9ef; border: 1px solid #303641; border-radius: 8px; padding: 8px; }
            #status { color: #707784; padding-top: 12px; }
            """
        )
