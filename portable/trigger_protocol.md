# Portable Colab + GitHub Trigger Protocol

This is the generic trigger layer for OfflineMedia Portable. It deliberately
uses the active repository and branch rather than creating a second project.

## Architecture

```text
GitHub Actions
     |
     | manual workflow_dispatch
     v
portable/trigger.json
     |
     | GitHub API polling
     v
running Google Colab notebook
     |
     v
OfflineMedia generation code
     |
     v
ComfyUI + GPU
```

GitHub Actions is the durable trigger/queue. Google Colab is the execution
runtime. Colab is not treated as a permanent server because its sessions can
expire.

## Current branch

`claude/scan-repo-chatgpt-review-6nljgh`

## Workflow

GitHub Actions workflow:

`.github/workflows/portable-trigger.yml`

Open **GitHub → Actions → Portable Colab Trigger → Run workflow**.

The workflow accepts:

- `mode`: `text_to_video` or `image_to_video`
- `prompt`
- `width`
- `height`
- `frames`
- `fps`

It writes a JSON request to `portable/trigger.json`.

## Colab listener

The notebook/runtime can poll the queue with:

```python
import os
import sys
sys.path.insert(0, "/content/offlinemedia")
from portable.trigger_listener import wait_for_trigger

trigger = wait_for_trigger(
    repo="CAption11/offlinemedia",
    branch="claude/scan-repo-chatgpt-review-6nljgh",
    token=os.environ.get("GH_TOKEN"),
    poll_seconds=15,
)

print(trigger)
```

For a private repository, put a suitable GitHub token in a Colab Secret named
`GH_TOKEN`. Do not paste the token directly into the notebook or commit it to
GitHub.

## Important limitation

This does not magically start a sleeping Colab runtime. The Colab notebook
must already be running and polling. If the Colab session has terminated, the
queued request remains in GitHub until the notebook is started again.

This is intentional. The next stage can add a more direct external trigger if
we later decide we need a service that can wake a GPU runtime.

## The user's `videoAI.ipynb`

The user has a separate Colab notebook named `videoAI.ipynb`. Its current
shared link is:

`https://colab.research.google.com/drive/1nkkG0e6-QMzI9m6gA4vi_OIdBaATgtW0?usp=sharing`

The GitHub connector cannot edit the contents of that Drive-hosted notebook
directly. To make that exact notebook version-controlled, use Colab's
**File -> Save a copy in GitHub** and save it to this active branch, preferably
as:

`portable/videoAI.ipynb`

The trigger protocol can then be inserted into that notebook using the listener
cell above.
