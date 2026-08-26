"""Stitch multiple short video clips into one long video using FFmpeg.

Wan2GP generates clips of ~5-10 seconds each. This module chains them into a
single output file — the foundation for 15-minute long-form video generation.

Continuity strategy: the last frame of each clip becomes the input image for
the next generation (image-to-video), so the scene doesn't jump between clips.
This is handled at generation time; this module only handles the stitching.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class FFmpegNotFound(RuntimeError):
    """Raised when ffprobe/ffmpeg is not installed."""


def _require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FFmpegNotFound(
            "ffmpeg is not installed. In Colab run: !apt-get install -y ffmpeg"
        )
    return ffmpeg


def _require_ffprobe() -> str:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise FFmpegNotFound(
            "ffprobe is not installed. In Colab run: !apt-get install -y ffmpeg"
        )
    return ffprobe


# ---------------------------------------------------------------------------
# Clip inspection
# ---------------------------------------------------------------------------

def clip_duration(path: Path) -> float:
    """Return the duration of a video clip in seconds."""
    ffprobe = _require_ffprobe()
    result = subprocess.run(
        [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def extract_last_frame(clip: Path, output: Path) -> Path:
    """Extract the very last frame of a clip as a PNG image.

    Used to seed the next clip for visual continuity — hand the returned image
    to Wan2GP's image-to-video mode as the starting frame.
    """
    ffmpeg = _require_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    # sseof -1 seeks 1 second before end, vframes 1 takes the last frame seen.
    subprocess.run(
        [
            ffmpeg, "-y",
            "-sseof", "-1",
            "-i", str(clip),
            "-vframes", "1",
            "-q:v", "2",
            str(output),
        ],
        check=True, capture_output=True,
    )
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(f"Failed to extract last frame from {clip}")
    return output


# ---------------------------------------------------------------------------
# Stitching
# ---------------------------------------------------------------------------

def stitch(
    clips: list[Path],
    output: Path,
    *,
    fps: int | None = None,
    reencode: bool = False,
) -> Path:
    """Concatenate clips into a single video file.

    Args:
        clips:    Ordered list of clip paths to join.
        output:   Destination file (e.g. /content/final_video.mp4).
        fps:      Output frame rate. If None, inherited from the first clip.
        reencode: Force re-encoding (slower but handles mixed codecs/resolutions).
                  Default False uses the fast copy muxer (no quality loss).

    Returns the output path.
    """
    if not clips:
        raise ValueError("No clips provided to stitch.")
    for clip in clips:
        if not clip.is_file():
            raise FileNotFoundError(f"Clip not found: {clip}")

    ffmpeg = _require_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as flist:
        for clip in clips:
            # FFmpeg concat demuxer requires escaped paths.
            safe = str(clip.resolve()).replace("'", r"'\''")
            flist.write(f"file '{safe}'\n")
        flist_path = Path(flist.name)

    try:
        if reencode or fps is not None:
            cmd = _reencode_cmd(ffmpeg, flist_path, output, fps)
        else:
            cmd = _copy_cmd(ffmpeg, flist_path, output)

        print(f"Stitching {len(clips)} clips → {output} ...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg stitching failed:\n{result.stderr[-2000:]}"
            )
    finally:
        flist_path.unlink(missing_ok=True)

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(f"Stitch produced no output at {output}")

    dur = clip_duration(output)
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"  ✅ Stitched video: {output.name}  ({dur:.1f}s, {size_mb:.1f} MB)")
    return output


def _copy_cmd(ffmpeg: str, flist: Path, output: Path) -> list[str]:
    return [
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(flist),
        "-c", "copy",
        str(output),
    ]


def _reencode_cmd(ffmpeg: str, flist: Path, output: Path, fps: int | None) -> list[str]:
    cmd = [
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(flist),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
    ]
    if fps is not None:
        cmd += ["-r", str(fps)]
    cmd.append(str(output))
    return cmd


# ---------------------------------------------------------------------------
# Convenience: stitch a whole directory of clips
# ---------------------------------------------------------------------------

def stitch_directory(
    clips_dir: Path,
    output: Path,
    *,
    pattern: str = "*.mp4",
    sort_by: str = "name",
    fps: int | None = None,
    reencode: bool = False,
) -> Path:
    """Find all clips in a directory, sort them, and stitch into one video.

    Args:
        clips_dir: Directory containing generated clip files.
        output:    Destination file.
        pattern:   Glob pattern for clip files (default '*.mp4').
        sort_by:   'name' (alphabetical, good for numbered clips) or 'mtime'.
        fps:       Output frame rate override.
        reencode:  Force re-encoding.
    """
    clips = list(clips_dir.glob(pattern))
    if not clips:
        raise FileNotFoundError(f"No files matching '{pattern}' in {clips_dir}")

    if sort_by == "mtime":
        clips.sort(key=lambda p: p.stat().st_mtime)
    else:
        clips.sort(key=lambda p: p.name)

    print(f"Found {len(clips)} clips in {clips_dir}:")
    for clip in clips:
        print(f"  {clip.name}")

    return stitch(clips, output, fps=fps, reencode=reencode)


# ---------------------------------------------------------------------------
# Long-video helper: estimate total length
# ---------------------------------------------------------------------------

def estimate_duration(clips: list[Path]) -> float:
    """Sum the durations of a list of clips (in seconds)."""
    total = 0.0
    for clip in clips:
        try:
            total += clip_duration(clip)
        except Exception:
            pass
    return total
