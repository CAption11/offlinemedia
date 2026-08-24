# OfflineMedia Portable

Portable is the Google Colab / GPU development runtime for OfflineMedia.

It is intentionally separate from **Mainload**, the eventual downloadable Windows application.

## Purpose

Portable is used to:

1. Prepare a Colab GPU runtime.
2. Install the OfflineMedia portable dependencies.
3. Detect the available NVIDIA GPU.
4. Install and start ComfyUI.
5. Validate the exact workflow and model combination.
6. Run real text-to-video and image-to-video smoke tests.
7. Validate and retrieve generated MP4 output.

Portable is not a mock and does not claim generation success without a real ComfyUI/model run.

## Current state

The existing repository already contains a basic `scripts/colab_setup.py` and `scripts/test_generation.py`. The Portable section is being built around those existing components rather than replacing them.

The first milestone is a real Colab text-to-video smoke test using a verified lightweight workflow/model.

## Colab flow

```text
Clone repository
      |
      v
Prepare Portable runtime
      |
      v
Detect NVIDIA GPU
      |
      v
Install/start ComfyUI
      |
      v
Install exact workflow + model requirements
      |
      v
Run diagnostics
      |
      v
Run OfflineMedia text-to-video smoke test
      |
      v
Validate MP4
      |
      v
Run image-to-video smoke test
```

## Important

Model weights are not stored in GitHub. Workflows and deterministic model manifests belong in the repository; multi-GB weights belong in the Colab runtime or an explicitly configured external/model storage location.

Do not hardcode a model URL until the workflow/model combination has been verified.
