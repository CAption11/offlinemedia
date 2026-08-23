"""Basic local hardware detection used for UI recommendations."""

from __future__ import annotations

import os
import platform


def describe() -> dict[str, str]:
    return {
        "os": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "ram_gb": f"{os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / (1024**3):.1f}" if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names else "unknown",
    }
