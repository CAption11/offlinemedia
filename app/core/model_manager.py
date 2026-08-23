"""Discovery of local model files without downloading anything."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


MODEL_EXTENSIONS = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx"}


@dataclass(frozen=True, slots=True)
class LocalModel:
    name: str
    path: Path
    size_bytes: int
    category: str


class ModelManager:
    """Scans the user's local model directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def scan(self) -> list[LocalModel]:
        models: list[LocalModel] = []
        for path in self.root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in MODEL_EXTENSIONS:
                continue
            category = self._category(path)
            models.append(LocalModel(path.name, path, path.stat().st_size, category))
        return sorted(models, key=lambda item: item.name.lower())

    @staticmethod
    def _category(path: Path) -> str:
        parts = {part.lower() for part in path.parts}
        if "diffusion_models" in parts or "unet" in parts:
            return "video/diffusion"
        if "text_encoders" in parts or "text_encoder" in parts:
            return "text encoder"
        if "vae" in parts:
            return "VAE"
        if path.suffix.lower() == ".gguf":
            return "GGUF"
        return "model"

    @staticmethod
    def format_size(size_bytes: int) -> str:
        value = float(size_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} TB"
