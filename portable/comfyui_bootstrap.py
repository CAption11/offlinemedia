"""Install, provision and start ComfyUI for the Portable Colab runtime.

`colab_setup.py` prepares the Python environment but deliberately stops short
of ComfyUI and model weights. This module is that missing step, kept as shared
code so every Portable notebook drives the same bootstrap instead of carrying
its own copy of the commands.

Nothing here claims a generation succeeded. It only gets ComfyUI to the point
where the shared OfflineMedia engine can talk to it.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMFY_DIR = Path("/content/ComfyUI")
COMFYUI_REPO = "https://github.com/comfyanonymous/ComfyUI.git"

# The assets used by the current official ComfyUI Wan 2.1 text-to-video example.
WAN_T2V_REPO = "Comfy-Org/Wan_2.1_ComfyUI_repackaged"
WAN_T2V_ASSETS = {
    "split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors": (
        "models/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors"
    ),
    "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors": (
        "models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    ),
    "split_files/vae/wan_2.1_vae.safetensors": "models/vae/wan_2.1_vae.safetensors",
}


def _run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    return subprocess.run(command, check=True, text=True, **kwargs)  # type: ignore[arg-type]


def require_gpu() -> None:
    """Fail fast when the runtime has no NVIDIA GPU."""
    if shutil.which("nvidia-smi") is None:
        raise RuntimeError(
            "No NVIDIA GPU runtime detected. "
            "In Colab select Runtime > Change runtime type > GPU."
        )
    subprocess.run(["nvidia-smi"], check=False)


def install_comfyui(comfy_dir: Path = DEFAULT_COMFY_DIR) -> Path:
    """Clone ComfyUI and install its requirements."""
    if not comfy_dir.exists():
        _run(["git", "clone", COMFYUI_REPO, str(comfy_dir)])
    else:
        print("ComfyUI already present:", comfy_dir)
    _run([sys.executable, "-m", "pip", "install", "-q", "-r", str(comfy_dir / "requirements.txt")])
    return comfy_dir


def download_wan_t2v_assets(comfy_dir: Path = DEFAULT_COMFY_DIR) -> list[Path]:
    """Download the official Wan 2.1 text-to-video assets into ComfyUI."""
    from huggingface_hub import hf_hub_download

    installed: list[Path] = []
    for remote, relative in WAN_T2V_ASSETS.items():
        local = comfy_dir / relative
        local.parent.mkdir(parents=True, exist_ok=True)
        if local.exists():
            print("Already present:", local)
        else:
            print("Downloading", remote)
            shutil.copy2(hf_hub_download(WAN_T2V_REPO, remote), local)
        installed.append(local)
    return installed


def is_ready(host: str = "127.0.0.1", port: int = 8188) -> bool:
    """Return True when ComfyUI answers on /system_stats."""
    try:
        with urllib.request.urlopen(
            f"http://{host}:{port}/system_stats", timeout=2
        ) as response:
            return bool(response.status == 200)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        return False


def start_comfyui(
    comfy_dir: Path = DEFAULT_COMFY_DIR,
    *,
    host: str = "127.0.0.1",
    port: int = 8188,
    log_path: Path = Path("/content/comfyui.log"),
    timeout_seconds: int = 240,
) -> Optional[subprocess.Popen[bytes]]:
    """Start ComfyUI, or reuse an already healthy instance.

    Colab users commonly re-run cells without restarting the runtime. If a
    healthy ComfyUI is already listening, reuse it instead of trying to start
    a second server on the same port.
    """
    if is_ready(host, port):
        print(f"ComfyUI already running and ready on {host}:{port}; reusing it.")
        return None
    log_file = log_path.open("wb")
    process = subprocess.Popen(
        [sys.executable, str(comfy_dir / "main.py"), "--listen", host, "--port", str(port)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if is_ready(host, port):
            print(f"ComfyUI is ready on {host}:{port}")
            return process
        if process.poll() is not None:
            raise RuntimeError(
                "ComfyUI exited during startup:\n"
                + log_path.read_text(errors="replace")[-6000:]
            )
        time.sleep(2)
    process.terminate()
    raise RuntimeError(
        f"ComfyUI did not become ready within {timeout_seconds}s:\n"
        + log_path.read_text(errors="replace")[-6000:]
    )


def sync_official_workflows(output_dir: Path = ROOT / "workflows" / "official") -> Path:
    """Fetch the current official Wan workflows next to the repository."""
    from portable.sync_official_workflows import sync

    sync(output_dir)
    return output_dir


def bootstrap(
    comfy_dir: Path = DEFAULT_COMFY_DIR,
    *,
    host: str = "127.0.0.1",
    port: int = 8188,
    download_assets: bool = True,
) -> Optional[subprocess.Popen[bytes]]:
    """Run the full bootstrap and return the new process, if one was started."""
    require_gpu()
    install_comfyui(comfy_dir)
    if download_assets:
        download_wan_t2v_assets(comfy_dir)
    sync_official_workflows()
    return start_comfyui(comfy_dir, host=host, port=port)


if __name__ == "__main__":
    bootstrap()
    print("ComfyUI bootstrap complete. Leave this process running.")
