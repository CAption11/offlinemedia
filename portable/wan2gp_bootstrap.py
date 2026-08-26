"""Install and launch Wan2GP in a Google Colab GPU runtime.

Wan2GP (https://github.com/deepbeepmeep/Wan2GP) wraps Wan 2.1/2.2 models with
a Gradio UI and built-in video-extension support. This module handles the full
setup sequence so a notebook cell can call bootstrap() and get a running server.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

DEFAULT_WAN2GP_DIR = Path("/content/Wan2GP")
DEFAULT_DATA_DIR = Path("/content/Wan2GP-data")
DEFAULT_PORT = 7860

# Wan2GP model profile numbers (wgp.py --profile N)
# Profile 5 = Wan 2.1 T2V 1.3B  (fits 15 GB T4 — free Colab tier)
# Profile 1 = Wan 2.1 T2V 14B   (needs 40+ GB — A100 / Pro tier)
PROFILE_T4_FREE = 5       # Wan 2.1 1.3B, 480p — safe on free T4
PROFILE_A100_PRO = 1      # Wan 2.1 14B, 720p — needs Colab Pro A100


# ---------------------------------------------------------------------------
# Hardware check
# ---------------------------------------------------------------------------

def require_gpu() -> str:
    """Fail fast when no NVIDIA GPU is visible; return GPU name on success."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, check=True,
        )
        name = result.stdout.strip().splitlines()[0]
        print(f"GPU detected: {name}")
        return name
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(
            "No NVIDIA GPU found. In Colab: Runtime → Change runtime type → GPU"
        ) from exc


def _vram_gb() -> float:
    """Return total VRAM in GB, or 0 on failure."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True,
        )
        return int(result.stdout.strip().splitlines()[0]) / 1024
    except Exception:
        return 0.0


def recommend_profile() -> int:
    """Pick a Wan2GP profile based on available VRAM."""
    vram = _vram_gb()
    if vram >= 35:
        print(f"VRAM: {vram:.0f} GB → using 14B model (profile {PROFILE_A100_PRO})")
        return PROFILE_A100_PRO
    print(f"VRAM: {vram:.0f} GB → using 1.3B model (profile {PROFILE_T4_FREE})")
    return PROFILE_T4_FREE


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

def install_wan2gp(wan2gp_dir: Path = DEFAULT_WAN2GP_DIR) -> None:
    """Clone Wan2GP if absent, pull updates if present."""
    if wan2gp_dir.exists():
        print(f"Wan2GP already at {wan2gp_dir}; pulling updates...")
        subprocess.run(["git", "pull", "--ff-only"], cwd=wan2gp_dir, check=True)
    else:
        print(f"Cloning Wan2GP into {wan2gp_dir}...")
        subprocess.run(
            ["git", "clone", "https://github.com/deepbeepmeep/Wan2GP", str(wan2gp_dir)],
            check=True,
        )

    _install_system_deps()
    _install_python_deps(wan2gp_dir)
    _fix_matplotlib_backend(wan2gp_dir)
    print("Wan2GP installation complete.")


def _install_system_deps() -> None:
    packages = ["ffmpeg", "libglib2.0-0", "libgl1", "libportaudio2"]
    missing = [p for p in packages if not _dpkg_installed(p)]
    if not missing:
        return
    print(f"Installing system packages: {', '.join(missing)}")
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    subprocess.run(["sudo", "apt-get", "update", "-qq"], check=True, env=env)
    subprocess.run(
        ["sudo", "apt-get", "install", "-y", "-qq", *missing],
        check=True, env=env,
    )


def _dpkg_installed(pkg: str) -> bool:
    return subprocess.run(["dpkg", "-s", pkg], capture_output=True).returncode == 0


def _install_python_deps(wan2gp_dir: Path) -> None:
    req = wan2gp_dir / "requirements.txt"
    if not req.exists():
        print("No requirements.txt found in Wan2GP; skipping Python deps.")
        return
    print("Installing Python dependencies (this takes a few minutes)...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
        check=True,
    )


def _fix_matplotlib_backend(wan2gp_dir: Path) -> None:
    """Replace TkAgg with headless Agg so Colab doesn't need a display."""
    target = wan2gp_dir / "preprocessing/matanyone/tools/interact_tools.py"
    if not target.exists():
        return
    text = target.read_text()
    if "matplotlib.use('Agg')" in text:
        return
    if "matplotlib.use('TkAgg')" in text:
        target.write_text(text.replace("matplotlib.use('TkAgg')", "matplotlib.use('Agg')", 1))
        print("Fixed matplotlib backend (TkAgg → Agg).")


# ---------------------------------------------------------------------------
# Configure data directories
# ---------------------------------------------------------------------------

def setup_data_dirs(
    data_dir: Path = DEFAULT_DATA_DIR,
    use_google_drive: bool = False,
    drive_path: str = "MyDrive/Wan2GP-data",
) -> Path:
    """Create and return the data root; optionally mount Google Drive."""
    if use_google_drive:
        mount_point = Path("/content/drive")
        if not mount_point.exists():
            from google.colab import drive  # type: ignore[import-untyped]
            drive.mount(str(mount_point), force_remount=False)
        data_dir = mount_point / drive_path
        print(f"Using Google Drive for persistent storage: {data_dir}")
    else:
        print(f"Using ephemeral local storage: {data_dir}")

    for sub in ("checkpoints", "loras", "outputs", "cache"):
        (data_dir / sub).mkdir(parents=True, exist_ok=True)
    return data_dir


# ---------------------------------------------------------------------------
# Start server
# ---------------------------------------------------------------------------

def is_ready(port: int = DEFAULT_PORT) -> bool:
    """Return True if the Wan2GP Gradio server is answering."""
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3)
        return True
    except Exception:
        return False


def start_wan2gp(
    wan2gp_dir: Path = DEFAULT_WAN2GP_DIR,
    data_dir: Path = DEFAULT_DATA_DIR,
    port: int = DEFAULT_PORT,
    profile: Optional[int] = None,
    share: bool = True,
    timeout_seconds: int = 300,
) -> Optional[subprocess.Popen]:
    """Start Wan2GP Gradio server, or reuse an already-running one.

    Returns the Popen object for the new process, or None when an existing
    healthy server was reused.
    """
    if is_ready(port):
        print(f"Wan2GP already running on port {port}; reusing.")
        return None

    if profile is None:
        profile = recommend_profile()

    cache_dir = data_dir / "cache"
    env = os.environ.copy()
    env.update({
        "WAN_CACHE_DIR": str(cache_dir),
        "HF_HOME": str(cache_dir / "huggingface"),
        "HUGGINGFACE_HUB_CACHE": str(cache_dir / "huggingface" / "hub"),
        "TORCH_HOME": str(cache_dir / "torch"),
        "XDG_CACHE_HOME": str(cache_dir / ".cache"),
    })

    cmd = [
        sys.executable, "-u", "wgp.py",
        "--listen",
        "--server-port", str(port),
        "--profile", str(profile),
    ]
    if share:
        cmd.append("--share")

    log_path = data_dir / "wan2gp.log"
    print(f"Starting Wan2GP (profile {profile}) on port {port}...")
    log_file = log_path.open("wb")
    process = subprocess.Popen(cmd, cwd=wan2gp_dir, env=env, stdout=log_file, stderr=log_file)

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        time.sleep(5)
        if process.poll() is not None:
            log_tail = log_path.read_text(errors="replace")[-2000:]
            raise RuntimeError(
                f"Wan2GP exited early (code {process.returncode}).\n\n{log_tail}"
            )
        if is_ready(port):
            print(f"Wan2GP is ready on port {port}.")
            _print_gradio_link(log_path)
            return process
        elapsed = int(time.monotonic() - deadline + timeout_seconds)
        print(f"  Waiting for Wan2GP... ({elapsed}s elapsed)")

    log_tail = log_path.read_text(errors="replace")[-2000:]
    raise RuntimeError(
        f"Wan2GP did not become ready within {timeout_seconds}s.\n\n{log_tail}"
    )


def _print_gradio_link(log_path: Path) -> None:
    """Scan the log for the public Gradio share link and print it."""
    try:
        for line in log_path.read_text(errors="replace").splitlines():
            if "gradio.live" in line or "Running on public URL" in line:
                print(f"\n  ✅ Gradio link: {line.strip()}\n")
                return
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Full bootstrap
# ---------------------------------------------------------------------------

def bootstrap(
    wan2gp_dir: Path = DEFAULT_WAN2GP_DIR,
    data_dir: Path = DEFAULT_DATA_DIR,
    port: int = DEFAULT_PORT,
    profile: Optional[int] = None,
    share: bool = True,
    use_google_drive: bool = False,
    drive_path: str = "MyDrive/Wan2GP-data",
) -> Optional[subprocess.Popen]:
    """Run the full Wan2GP bootstrap and return the server process (or None if reused)."""
    require_gpu()
    data_dir = setup_data_dirs(data_dir, use_google_drive=use_google_drive, drive_path=drive_path)
    install_wan2gp(wan2gp_dir)
    return start_wan2gp(
        wan2gp_dir=wan2gp_dir,
        data_dir=data_dir,
        port=port,
        profile=profile,
        share=share,
    )
