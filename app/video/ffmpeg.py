"""FFmpeg discovery and local media operations."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class FFmpeg:
    """Wrapper around a local ffmpeg executable."""

    def __init__(self, executable: str | Path | None = None) -> None:
        self.executable = str(executable) if executable else shutil.which("ffmpeg")

    @property
    def available(self) -> bool:
        return bool(self.executable)

    def version(self) -> str | None:
        if not self.executable:
            return None
        result = subprocess.run(
            [self.executable, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.splitlines()[0] if result.stdout.splitlines() else None

    def concat(self, inputs: list[Path], output: Path) -> None:
        if not self.executable:
            raise RuntimeError("FFmpeg was not found on this computer")
        if not inputs:
            raise ValueError("At least one input file is required")
        output.parent.mkdir(parents=True, exist_ok=True)
        list_file = output.parent / ".offline_media_concat.txt"
        try:
            lines = []
            for path in inputs:
                escaped = path.resolve().as_posix().replace("'", "'\\''")
                lines.append(f"file '{escaped}'")
            list_file.write_text("\n".join(lines), encoding="utf-8")
            subprocess.run(
                [self.executable, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)],
                check=True,
            )
        finally:
            list_file.unlink(missing_ok=True)

    def images_to_video(self, inputs: list[Path], output: Path, fps: int = 2, seconds_per_image: float = 2.0) -> None:
        """Create a simple slideshow from images using FFmpeg's concat filter."""
        if not self.executable:
            raise RuntimeError("FFmpeg was not found on this computer")
        if not inputs:
            raise ValueError("At least one image is required")
        if fps <= 0 or seconds_per_image <= 0:
            raise ValueError("fps and seconds_per_image must be positive")

        output.parent.mkdir(parents=True, exist_ok=True)
        list_file = output.parent / ".offline_media_images.txt"
        try:
            duration = f"{seconds_per_image:.3f}"
            lines = []
            for path in inputs:
                escaped = path.resolve().as_posix().replace("'", "'\\''")
                lines.extend([f"file '{escaped}'", f"duration {duration}"])
            escaped_last = inputs[-1].resolve().as_posix().replace("'", "'\\''")
            lines.append(f"file '{escaped_last}'")
            list_file.write_text("\n".join(lines), encoding="utf-8")
            subprocess.run(
                [
                    self.executable, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                    "-vf", f"fps={fps},format=yuv420p", "-movflags", "+faststart", str(output),
                ],
                check=True,
            )
        finally:
            list_file.unlink(missing_ok=True)
