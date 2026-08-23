"""FFmpeg discovery and lightweight media operations."""

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
        first_line = result.stdout.splitlines()
        return first_line[0] if first_line else None

    def concat(self, inputs: list[Path], output: Path) -> None:
        """Concatenate compatible media files using FFmpeg's concat demuxer."""
        if not self.executable:
            raise RuntimeError("FFmpeg was not found on this computer")
        if not inputs:
            raise ValueError("At least one input file is required")

        output.parent.mkdir(parents=True, exist_ok=True)
        list_file = output.parent / ".offline_media_concat.txt"
        try:
            list_file.write_text(
                "\n".join(f"file '{path.resolve().as_posix().replace(chr(39), chr(39) + chr(39))}'" for path in inputs),
                encoding="utf-8",
            )
            subprocess.run(
                [self.executable, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)],
                check=True,
            )
        finally:
            list_file.unlink(missing_ok=True)
