"""Main OfflineMedia desktop window."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.generation import GenerationRequest, GenerationType
from app.core.hardware import describe
from app.core.model_manager import ModelManager
from app.core.paths import ensure_directories
from app.engines.manager import EngineManager
from app.video.ffmpeg import FFmpeg


class GenerationWorker(QObject):
    """Runs a generation request away from the Qt GUI thread."""

    finished = Signal(object)

    def __init__(self, engine: EngineManager, request: GenerationRequest) -> None:
        super().__init__()
        self.engine = engine
        self.request = request

    @Slot()
    def run(self) -> None:
        self.finished.emit(self.engine.generate(self.request))


class MainWindow(QMainWindow):
    """Primary OfflineMedia desktop application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OfflineMedia")
        self.resize(1280, 820)
        self.setMinimumSize(1050, 680)
        self.paths = ensure_directories()
        self.engines = EngineManager()
        self.models = ModelManager(self.paths["models"])
        self.ffmpeg = FFmpeg()
        self._pages: dict[str, QWidget] = {}
        self._generation_thread: QThread | None = None
        self._generation_worker: GenerationWorker | None = None
        self._build_ui()
        self._refresh_status()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(235)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 24, 20, 20)
        side.setSpacing(8)

        brand = QLabel("OfflineMedia")
        brand.setObjectName("brand")
        subtitle = QLabel("LOCAL VIDEO STUDIO")
        subtitle.setObjectName("subtitle")
        side.addWidget(brand)
        side.addWidget(subtitle)
        side.addSpacing(24)

        for key, label in (
            ("home", "Home"),
            ("text", "Text → Video"),
            ("image", "Image → Video"),
            ("sequence", "Image Sequence"),
            ("models", "Models"),
            ("projects", "Projects"),
        ):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page=key: self._show_page(page))
            side.addWidget(button)

        side.addStretch()
        settings = QPushButton("Settings")
        settings.clicked.connect(lambda: self._show_page("settings"))
        side.addWidget(settings)

        self.stack = QStackedWidget()
        self._add_page("home", self._home_page())
        self._add_page("text", self._generator_page(GenerationType.TEXT_TO_VIDEO, "Text → Video", False))
        self._add_page("image", self._generator_page(GenerationType.IMAGE_TO_VIDEO, "Image → Video", True))
        self._add_page("sequence", self._sequence_page())
        self._add_page("models", self._models_page())
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
        if key == "models":
            self._refresh_models()

    def _home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        title = QLabel("Create")
        title.setObjectName("page_title")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(18)
        cards = [
            ("Text → Video", "Generate a local AI video from a prompt.", "text"),
            ("Image → Video", "Animate a still image with a local model.", "image"),
            ("Image Sequence", "Turn multiple images into a video.", "sequence"),
        ]
        for index, (name, description, target) in enumerate(cards):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            heading = QLabel(name)
            heading.setObjectName("card_title")
            desc = QLabel(description)
            desc.setWordWrap(True)
            open_button = QPushButton("Open")
            open_button.clicked.connect(lambda checked=False, page=target: self._show_page(page))
            card_layout.addWidget(heading)
            card_layout.addWidget(desc)
            card_layout.addStretch()
            card_layout.addWidget(open_button)
            grid.addWidget(card, 0, index)
        layout.addLayout(grid)
        layout.addStretch()
        self.status_label = QLabel()
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)
        return page

    def _generator_page(self, generation_type: GenerationType, title_text: str, image_mode: bool) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)

        title = QLabel(title_text)
        title.setObjectName("page_title")
        layout.addWidget(title)

        image_path = None
        if image_mode:
            row = QHBoxLayout()
            image_path = QLineEdit()
            image_path.setPlaceholderText("Select an input image…")
            browse = QPushButton("Browse")
            browse.clicked.connect(lambda: self._choose_image(image_path))
            row.addWidget(image_path, 1)
            row.addWidget(browse)
            layout.addLayout(row)

        prompt = QPlainTextEdit()
        prompt.setPlaceholderText("Describe the video you want to generate…")
        prompt.setMinimumHeight(170)
        layout.addWidget(prompt)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Width"))
        width = self._spin(256, 2048, 512, 64)
        controls.addWidget(width)
        controls.addWidget(QLabel("Height"))
        height = self._spin(256, 2048, 512, 64)
        controls.addWidget(height)
        controls.addWidget(QLabel("Frames"))
        frames = self._spin(8, 200, 49, 1)
        controls.addWidget(frames)
        controls.addWidget(QLabel("FPS"))
        fps = self._spin(1, 60, 8, 1)
        controls.addWidget(fps)
        controls.addStretch()
        layout.addLayout(controls)

        model = QComboBox()
        model.addItem("Workflow-selected model")
        model.setToolTip("Model selection is controlled by the installed ComfyUI workflow for now.")
        layout.addWidget(model)

        status = QLabel("Ready")
        status.setObjectName("generation_status")
        generate = QPushButton("Generate Video")
        generate.setObjectName("primary")
        generate.clicked.connect(
            lambda: self._start_generation(
                generation_type,
                prompt,
                width,
                height,
                frames,
                fps,
                image_path,
                status,
            )
        )
        layout.addWidget(status)
        layout.addWidget(generate)
        layout.addStretch()
        return page

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int, step: int) -> QSpinBox:
        box = QSpinBox()
        box.setRange(minimum, maximum)
        box.setSingleStep(step)
        box.setValue(value)
        return box

    def _choose_image(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if path:
            target.setText(path)

    def _start_generation(
        self,
        generation_type: GenerationType,
        prompt: QPlainTextEdit,
        width: QSpinBox,
        height: QSpinBox,
        frames: QSpinBox,
        fps: QSpinBox,
        image_path: QLineEdit | None,
        status: QLabel,
    ) -> None:
        text = prompt.toPlainText().strip()
        if not text:
            status.setText("Enter a prompt first.")
            return
        if not self.engines.any_available():
            status.setText("ComfyUI is not running. Start the local ComfyUI server first.")
            return

        inputs: list[Path] = []
        if image_path is not None:
            path = Path(image_path.text().strip())
            if not path.is_file():
                status.setText("Select a valid input image.")
                return
            inputs.append(path)

        request = GenerationRequest(
            generation_type=generation_type,
            prompt=text,
            input_images=inputs,
            width=width.value(),
            height=height.value(),
            frames=frames.value(),
            fps=fps.value(),
            output_dir=self.paths["outputs"],
        )
        status.setText("Queued… generating locally. The UI will remain responsive.")
        self._generation_thread = QThread(self)
        self._generation_worker = GenerationWorker(self.engines, request)
        self._generation_worker.moveToThread(self._generation_thread)
        self._generation_thread.started.connect(self._generation_worker.run)
        self._generation_worker.finished.connect(lambda result: self._generation_finished(result, status))
        self._generation_worker.finished.connect(self._generation_thread.quit)
        self._generation_thread.finished.connect(self._generation_thread.deleteLater)
        self._generation_thread.finished.connect(self._generation_worker.deleteLater)
        self._generation_thread.start()

    def _generation_finished(self, result, status: QLabel) -> None:
        if result.success:
            if result.output_files:
                output = result.output_files[0]
                status.setText(f"Finished: {output}")
                self._open_path(output.parent)
            else:
                status.setText(f"Finished. Job: {result.job_id}")
        else:
            status.setText(f"Generation failed: {result.error}")
        self._generation_worker = None
        self._generation_thread = None

    def _sequence_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        title = QLabel("Image Sequence")
        title.setObjectName("page_title")
        layout.addWidget(title)
        self.sequence_paths: list[str] = []
        self.sequence_label = QLabel("No images selected")
        layout.addWidget(self.sequence_label)
        choose = QPushButton("Choose Images")
        choose.clicked.connect(self._choose_sequence)
        layout.addWidget(choose)
        layout.addStretch()
        return page

    def _choose_sequence(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select images", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        self.sequence_paths = paths
        self.sequence_label.setText(f"{len(paths)} images selected") if paths else self.sequence_label.setText("No images selected")

    def _models_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        title = QLabel("Local Models")
        title.setObjectName("page_title")
        layout.addWidget(title)
        self.models_label = QLabel()
        self.models_label.setWordWrap(True)
        layout.addWidget(self.models_label)
        refresh = QPushButton("Rescan Models")
        refresh.clicked.connect(self._refresh_models)
        layout.addWidget(refresh)
        layout.addStretch()
        self._refresh_models()
        return page

    def _refresh_models(self) -> None:
        if not hasattr(self, "models_label"):
            return
        models = self.models.scan()
        if not models:
            self.models_label.setText(f"No local model files found.\n\nModel directory:\n{self.paths['models']}")
            return
        lines = [f"{model.name}  •  {ModelManager.format_size(model.size_bytes)}  •  {model.category}" for model in models]
        self.models_label.setText("\n".join(lines))

    def _projects_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        title = QLabel("Projects")
        title.setObjectName("page_title")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"Outputs: {self.paths['outputs']}"))
        open_button = QPushButton("Open Output Folder")
        open_button.clicked.connect(lambda: self._open_path(self.paths["outputs"]))
        layout.addWidget(open_button)
        layout.addStretch()
        return page

    def _settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        title = QLabel("Settings")
        title.setObjectName("page_title")
        layout.addWidget(title)
        for key, value in describe().items():
            layout.addWidget(QLabel(f"{key.upper()}: {value}"))
        layout.addWidget(QLabel(f"ComfyUI: {self.engines.comfyui.base_url}"))
        layout.addWidget(QLabel(f"FFmpeg: {'available' if self.ffmpeg.available else 'not found'}"))
        layout.addWidget(QLabel(f"Workflow directory: {self.paths['workflows']}"))
        layout.addStretch()
        return page

    def _refresh_status(self) -> None:
        comfy = "connected" if self.engines.any_available() else "not connected"
        ffmpeg = "available" if self.ffmpeg.available else "not installed"
        self.status_label.setText(f"ComfyUI: {comfy}  •  FFmpeg: {ffmpeg}")

    @staticmethod
    def _open_path(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            subprocess.Popen(["explorer", str(path)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

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
            QPlainTextEdit, QLineEdit, QSpinBox, QComboBox { background: #191d24; color: #e6e9ef; border: 1px solid #303641; border-radius: 8px; padding: 8px; }
            #status, #generation_status { color: #707784; padding-top: 12px; }
            """
        )
