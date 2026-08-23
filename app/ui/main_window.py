"""Main OfflineMedia desktop window."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Primary application shell."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OfflineMedia")
        self.resize(1280, 800)
        self.setMinimumSize(1000, 650)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(20, 24, 20, 20)
        side_layout.setSpacing(8)

        title = QLabel("OfflineMedia")
        title.setObjectName("brand")
        side_layout.addWidget(title)

        subtitle = QLabel("LOCAL VIDEO STUDIO")
        subtitle.setObjectName("subtitle")
        side_layout.addWidget(subtitle)
        side_layout.addSpacing(24)

        for label in ("Text → Video", "Image → Video", "Image Sequence", "Projects"):
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            side_layout.addWidget(button)

        side_layout.addStretch()
        settings = QPushButton("Settings")
        settings.setCursor(Qt.PointingHandCursor)
        side_layout.addWidget(settings)

        content = QFrame()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 28, 32, 28)

        header = QLabel("Create")
        header.setObjectName("page_title")
        content_layout.addWidget(header)

        cards = QHBoxLayout()
        cards.setSpacing(18)
        for name, description in (
            ("Text → Video", "Generate a video from a text prompt."),
            ("Image → Video", "Animate a still image with local AI."),
            ("Image Sequence", "Turn multiple images into a story."),
        ):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_title = QLabel(name)
            card_title.setObjectName("card_title")
            card_description = QLabel(description)
            card_description.setWordWrap(True)
            card_layout.addWidget(card_title)
            card_layout.addWidget(card_description)
            card_layout.addStretch()
            cards.addWidget(card)
        content_layout.addLayout(cards)
        content_layout.addStretch()

        status = QLabel("Engine: not connected  •  Models: not installed")
        status.setObjectName("status")
        content_layout.addWidget(status)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)

        self.setStyleSheet(
            """
            QMainWindow { background: #111318; }
            #sidebar { background: #171a20; border-right: 1px solid #282c35; }
            #content { background: #111318; }
            #brand { color: #f2f4f8; font-size: 24px; font-weight: 700; }
            #subtitle { color: #747b88; font-size: 10px; letter-spacing: 2px; }
            QPushButton {
                background: #1d2129; color: #dfe3ea; border: 1px solid #2b303a;
                border-radius: 8px; padding: 11px; text-align: left;
            }
            QPushButton:hover { background: #252a34; }
            #page_title { color: #f2f4f8; font-size: 30px; font-weight: 700; }
            #card { background: #191d24; border: 1px solid #292e38; border-radius: 12px; min-height: 150px; }
            #card_title { color: #f2f4f8; font-size: 17px; font-weight: 600; }
            QLabel { color: #aab1bd; font-size: 13px; }
            #status { color: #707784; padding-top: 12px; }
            """
        )
