# Wan 2.1 starter workflows

OfflineMedia can consume the official ComfyUI Wan 2.1 visual workflow JSON files. The application converts the visual workflow to ComfyUI API format at runtime using `/object_info`.

For the lightweight text-to-video path, the official ComfyUI example uses the Wan 2.1 1.3B diffusion model together with the Wan VAE and UMT5 text encoder. The official example workflow is:

- `text_to_video_wan.json`
- `image_to_video_wan_example.json`

Download the current versions from the ComfyUI Examples repository and place them in the OfflineMedia local workflow directory as:

- `text_to_video.json`
- `image_to_video.json`

The model files are not included in this repository. Install them in the ComfyUI model directories used by your local installation.

## Important hardware note

The Wan 2.1 1.3B model is the lightweight option, but video generation is still computationally expensive. Integrated graphics may be extremely slow or unsupported depending on the ComfyUI/PyTorch backend. The application therefore detects the local ComfyUI server rather than pretending hardware capabilities exist.
