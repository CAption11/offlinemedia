# OfflineMedia

OfflineMedia is a Windows-first, offline media generation workstation.

## Goals

- Text-to-video generation
- Image-to-video generation
- Multiple-image-to-video workflows
- Local model management
- Local video processing with FFmpeg
- Project/history management
- No cloud dependency after models and runtimes are installed

## Architecture

```text
Windows UI
   |
   v
Application / Generation Manager
   |
   +--> AI Engine Adapter
   |       +--> ComfyUI
   |       +--> Future local engines
   |
   +--> Video Processing
           +--> FFmpeg
```

The initial release is intentionally an application scaffold. AI model workflows will be added incrementally after the desktop shell and engine interfaces are stable.

## Development

Python 3.11+ is recommended.

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the application:

```powershell
python -m app
```

## Project layout

```text
app/
  __main__.py
  ui/
  core/
  engines/
  video/
  storage/
  config/
assets/
models/
workflows/
projects/
tests/
scripts/
```

## Status

**Phase 0: project foundation**

- [x] Repository initialized
- [x] Application package scaffold
- [x] Desktop shell
- [x] Engine abstraction
- [x] Project storage abstraction
- [ ] ComfyUI integration
- [ ] Image-to-video workflow
- [ ] Text-to-video workflow
- [ ] FFmpeg pipeline
- [ ] Model manager
- [ ] Windows packaging
