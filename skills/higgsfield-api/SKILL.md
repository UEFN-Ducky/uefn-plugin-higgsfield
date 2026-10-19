---
name: higgsfield-api
description: "Higgsfield via UEFN-Ducky MCP — 83 image and video models (Soul, Seedance, Kling, Wan, Hailuo, PixVerse, LTX, Genjutsu, Cinema Studio, Recraft, Ideogram…): pictures, edits, text/image/reference to video, video edit/extend, motion transfer, restyle, object swap, Soul ID characters. Tools higgsfield_* and Higgsfield workflow nodes; async with a priced spend lock."
license: MIT
metadata:
  label: Higgsfield
  version: 1
  author: UEFN-Ducky
  copyright: Copyright 2026 Mindful Path Company, LLC
  allow_redistribute: true
  managed_by: uefn-ducky
  source_plugin_id: higgsfield
---

# Higgsfield — generate via MCP

You call **`higgsfield_*` tools** on the shared `uefn-ducky` MCP (Higgsfield API, `api.higgsfield.ai`). The key lives in **Settings → Higgsfield** as `KEY_ID:KEY_SECRET` (encrypted; Test checks it). Never curl the API, read a `.env`, or connect Higgsfield's own MCP for this.

## HARD RULES — CREDITS (non-negotiable)

Paid tools **refuse** unless `confirm_spend=true`. The refusal quotes Higgsfield's own estimate for those exact settings (credits and USD). Free: models, model_info, estimate, status, cancel, download, upload, presets, soul_styles, character_status, import.

1. Call the tool once without `confirm_spend` (or `higgsfield_estimate`) to get the price.
2. Call **`ducky_ask_user`** with a yes/no question naming the job, the model and that price. Never ask only in chat text.
3. Only on a clear yes: call again with `confirm_spend=true`.
4. One yes covers the job(s) in that question — never chain more paid jobs without a new yes. Failed and NSFW-flagged requests are refunded.

## Core pattern

Every model shares one async lifecycle. Tools default to `wait=true`: they upload local files, submit, poll and download into the plugin's folder, returning `request_id`, `downloaded`, `video_url` / `image_urls`. With `wait=false` you get a `request_id`; then `higgsfield_status(request_id, poll=true)` and `higgsfield_download`. Results stay downloadable for at least 7 days. Videos take minutes.

Inputs (`image`, `video`, `images`…) take local paths (JPG/PNG/WebP/GIF, WAV, MP4 — uploaded), https links or data: URIs. A model's own extra settings go in `extra` as JSON (e.g. `{"style_id": "…", "custom_reference_id": "…", "generate_audio": false}`); requests are checked against the model's real schema first, so unknown fields and bad choices fail before spending.

## Tools

| Tool | When | Default model |
|------|------|---------------|
| `higgsfield_text_to_image` | Picture from a prompt (+ reference pictures on models that take them) | Soul 2 |
| `higgsfield_edit_image` | Change a picture by prompt | Qwen Image 3 Edit |
| `higgsfield_text_to_video` | Video from a prompt | Seedance 2.5 |
| `higgsfield_image_to_video` | Animate a picture (end_image for first/last frame models) | Seedance 2.5 |
| `higgsfield_reference_to_video` | Keep characters/products/style from pictures, videos, sound | Seedance 2.5 |
| `higgsfield_edit_video` | Edit by prompt, or `extend=true` to continue | Seedance 2.5 |
| `higgsfield_motion_transfer` | A picture's character performs a video's moves | Genjutsu Motion Transfer |
| `higgsfield_restyle_video` | Video in a Genjutsu style preset (`higgsfield_presets('restyle')`) | Genjutsu Restyle |
| `higgsfield_object_swap` | Swap an object in a video | Genjutsu Object Swap |
| `higgsfield_generate` | ANY model by id + JSON params | — |
| `higgsfield_create_character` | Train a Soul ID from 1-100 photos → `custom_reference_id` | — |
| `higgsfield_models` / `higgsfield_model_info` | Find models by workflow; full inputs + notes | free |
| `higgsfield_estimate` | Price for a model + settings | free |
| `higgsfield_presets` / `higgsfield_soul_styles` | preset_id / style_id values | free |
| `higgsfield_status` / `higgsfield_cancel` / `higgsfield_download` / `higgsfield_upload` | Requests and files | free |
| `higgsfield_import_to_uefn` | Land a picture, sound or video in the Content Browser | free |

Pick a model with `model="<endpoint id>"` (from `higgsfield_models(workflow=…)`) or an unambiguous name ("kling 3 pro", "wan 3 prime"). `duration` snaps to the nearest length the model offers.

## UEFN uses

- Island trailers and Discover videos: screenshot → `higgsfield_image_to_video` (slow cinematic camera move), or `higgsfield_reference_to_video` with gameplay frames. Hand the clips to **island-media-kit** to cut a trailer.
- Thumbnails and key art: `higgsfield_text_to_image` at 16:9, then check Discover's rules before submitting.
- In-game screens, posters and billboards: pictures → `higgsfield_import_to_uefn` → material on a mesh (**materials** skill).

## Workflows

The **Higgsfield** node group does all of this without an agent (see reference `workflows`). Nodes only spend with **Spend credits** on; when you build a workflow for someone, leave it off and tell them which switch to turn on.

## Don'ts

- Don't spend without a fresh `ducky_ask_user` yes; don't invent approval.
- Don't guess a model's fields — read `higgsfield_model_info`.
- Don't upload MOV/MP3/WebM: uploads take JPG, PNG, WebP, GIF, WAV, MP4 only.
- Don't poll in a tight loop; `higgsfield_status(poll=true)` backs off for you.

## Reference files

Load with MCP `skill_read_subskill("higgsfield-api", "<id>")`.

- `models` — every model by workflow with its main inputs
- `workflows` — the Higgsfield workflow nodes and templates
- `setup` — key, Test, defaults, billing
