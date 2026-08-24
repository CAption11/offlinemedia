# OfflineMedia Google Colab test

This is the development/test path for the project. The final Windows application remains offline and does not require Colab.

## 1. Clone

```python
!git clone https://github.com/CAption11/offlinemedia.git
%cd offlinemedia
```

## 2. Install the test runtime

```python
!pip install -q -r requirements-colab.txt
!python scripts/colab_setup.py
```

## 3. Check the runtime

```python
!python scripts/diagnostics.py
```

## 4. Start ComfyUI

Install/start a compatible ComfyUI build in the Colab runtime. Keep the server bound to `127.0.0.1:8188` unless you deliberately change the test command.

## 5. Install a workflow and model

Place the selected API-format workflow under `workflows/` using the filename expected by the generation type. Put model weights in the appropriate ComfyUI model directories. **Do not commit model weights to Git.**

## 6. Run a real smoke test

```python
!python scripts/test_generation.py \
  --type text_to_video \
  --prompt "A small red ball rolling across a wooden table, natural lighting" \
  --width 320 \
  --height 240 \
  --frames 17 \
  --fps 8
```

## 7. Inspect output

```python
from pathlib import Path
from IPython.display import Video, display

files = sorted(Path("projects/smoke_tests").rglob("*"))
print(files)

mp4 = next((p for p in files if p.suffix.lower() == ".mp4"), None)
if mp4:
    display(Video(str(mp4), embed=True))
```

The test script intentionally does not download model weights. This keeps the repository small and lets us test different models without changing application code.
