# OfflineMedia workflows

OfflineMedia uses ComfyUI **API-format** workflow JSON files.

Place these files in the user's local workflow directory shown in the app's Settings:

- `text_to_video.json`
- `image_to_video.json`
- `image_sequence.json`

## Binding format

The application can patch workflow inputs through a `bindings` mapping. The mapping is kept outside the ComfyUI graph so the workflow itself remains a normal API-format graph.

Example configuration:

```json
{
  "bindings": {
    "prompt": {"node": "6", "input": "text"},
    "negative_prompt": {"node": "7", "input": "text"},
    "seed": {"node": "3", "input": "seed"},
    "width": {"node": "4", "input": "width"},
    "height": {"node": "4", "input": "height"},
    "frames": {"node": "12", "input": "length"},
    "image": {"node": "10", "input": "image"}
  }
}
```

The exact node IDs and input names depend on the model workflow. Do not guess them. Export the workflow from ComfyUI in API format and map the actual nodes used by that workflow.

Model files are deliberately not committed to Git. They can be many gigabytes and belong in the local ComfyUI/model installation.
