# OfflineMedia Portable Colab Runbook

This is the first real-generation path for OfflineMedia.

## 1. Clone

```bash
git clone -b claude/scan-repo-chatgpt-review-6nljgh https://github.com/CAption11/offlinemedia.git
cd offlinemedia
```

## 2. Prepare the runtime

```bash
python portable/colab_setup.py
```

## 3. Run diagnostics

```bash
python portable/diagnostics.py
```

A real GPU smoke test should not proceed until an NVIDIA runtime is available.

## 4. ComfyUI

Install/start ComfyUI in the Colab runtime and make it available at:

`http://127.0.0.1:8188`

The exact installation commands and custom nodes will be added after the first workflow/model combination is verified. Do not guess them from an old workflow.

## 5. Workflow/model

Place the verified OfflineMedia workflow under `workflows/` and install its exact model/custom-node requirements.

Model weights must not be committed to Git.

## 6. Real text-to-video smoke test

```bash
python portable/smoke_test.py \
  --type text_to_video \
  --prompt "A small red ball rolling across a wooden table, natural lighting" \
  --width 320 \
  --height 240 \
  --frames 17 \
  --fps 8
```

The underlying shared test fails if ComfyUI is unavailable, generation fails, or no output is produced.

## 7. Image-to-video

After text-to-video is proven, add the verified image-to-video workflow and run the same shared backend with an input image.

## Evidence rule

Do not mark a generation milestone complete based on configuration alone. A milestone is complete only when a real model produces an output MP4 and the output is validated.
