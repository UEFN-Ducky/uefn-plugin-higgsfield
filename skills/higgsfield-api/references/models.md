---
description: "Every Higgsfield model by workflow with its endpoint id, required inputs, duration/resolution/aspect choices — pick the model for higgsfield_* tools and nodes"
metadata:
  label: "Models"
---

# Higgsfield models

From docs.higgsfield.ai (83 generation models). Full inputs and notes: `higgsfield_model_info(model)`. Required inputs in **bold**.

## Text to image (15)

| Model id | Name | Inputs | Seconds | Resolution |
|---|---|---|---|---|
| `alibaba/qwen-image-3/text-to-image` | Qwen Image 3 — Text to image | **prompt** |  | 1k/2k |
| `higgsfield-ai/soul/cinema` | SOUL Cinema — Text to image | **prompt** |  | 720p/1080p |
| `higgsfield-ai/soul/standard` | SOUL — Text to image | **prompt**, image_reference_url |  | 720p/1080p |
| `higgsfield-ai/soul/v2/standard` | SOUL V2 — Text to image | **prompt** |  | 720p/1080p |
| `higgsfield/ads-studio/v1.0` | Ads Studio — Generate ads | **prompt**, image_urls |  |  |
| `ideogram/v4.0` | Ideogram 4.0 — Generate | **prompt**, image_url |  |  |
| `marketing-studio/image` | Marketing Studio Image — 2.0 Alpha | **prompt**, preset_id, image_urls |  | 1k/2k/4k |
| `marketing-studio/image/flare` | Marketing Studio Image — 2.5 Flare | **prompt**, preset_id, image_urls |  | 1k/2k/4k |
| `marketing-studio/image/sunburst` | Marketing Studio Image — 2.5 Sunburst | **prompt**, preset_id, image_urls |  | 1k/2k/4k |
| `recraft/v4.1/pro/text-to-image` | Recraft V4.1 Pro — Text to image | **prompt** |  | 2k |
| `recraft/v4.1/text-to-image` | Recraft V4.1 — Text to image | **prompt** |  | 1k |
| `recraft/v4.1/utility/pro/text-to-image` | Recraft V4.1 Utility Pro — Text to image | **prompt** |  | 2k |
| `recraft/v4.1/utility/text-to-image` | Recraft V4.1 Utility — Text to image | **prompt** |  | 1k |
| `xai/grok-imagine-image-2.0` | Grok Image 2.0 — Generate and edit | **prompt**, image_urls |  | 1k/2k |
| `z-image/turbo` | Z-Image Turbo — Generate | **prompt** |  | 1k/2k |

## Image edit (1)

| Model id | Name | Inputs | Seconds | Resolution |
|---|---|---|---|---|
| `alibaba/qwen-image-3/edit` | Qwen Image 3 — Edit images | **prompt**, **image_urls** |  | 1k/2k |

## Text to video (19)

| Model id | Name | Inputs | Seconds | Resolution |
|---|---|---|---|---|
| `alibaba/happy-horse/text-to-video` | Happy Horse 1.0 — Text to video | **prompt** | 3-15 | 720p/1080p |
| `alibaba/happy-horse/v1.1/text-to-video` | HappyHorse 1.1 — Text to video | **prompt** | 3-15 | 720p/1080p |
| `alibaba/wan-3.0-prime/text-to-video` | Wan 3.0 Prime — Text to video | **prompt** | 2-30 | 480p/720p/1080p |
| `alibaba/wan-3.0/text-to-video` | Wan 3.0 — Text to video | **prompt** | 2-30 | 480p/720p/1080p |
| `bytedance/seedance-2.0/text-to-video` | Seedance 2.0 — Text to video | **prompt** | 4-15 | 480p/720p/1080p/4k |
| `bytedance/seedance-2.5/text-to-video` | Seedance 2.5 — Text to video | **prompt** | 4-30 | 480p/720p/1080p |
| `kling-video/v2.5-turbo/pro/text-to-video` | Kling 2.5 Turbo — Pro text to video | **prompt** | 5/10 |  |
| `kling-video/v2.6/pro/text-to-video` | Kling 2.6 — Pro text to video | **prompt** | 5/10 |  |
| `kling-video/v3.0-turbo/text-to-video` | Kling 3.0 — Turbo · Text to video | **prompt** | 3-15 | 720p/1080p |
| `kling-video/v3.0/4k/text-to-video` | Kling 3.0 — 4K · Text to video | prompt | 3-15 |  |
| `kling-video/v3.0/pro/text-to-video` | Kling 3.0 — Pro · Text to video | prompt | 3-15 |  |
| `kling-video/v3.0/std/text-to-video` | Kling 3.0 — Standard · Text to video | prompt | 3-15 |  |
| `lightricks/ltx-2.5/text-to-video/fast` | LTX-2.5 — Text to video fast | **prompt** | 6/8/10 | 720p/1080p/2k/4k |
| `lightricks/ltx-2.5/text-to-video/pro` | LTX-2.5 — Text to video pro | **prompt** | 6/8/10 | 720p/1080p |
| `minimax/h3/text-to-video` | MiniMax H3 — Text to video | **prompt** | 5-15 | 2K |
| `minimax/hailuo-2.3/standard/text-to-video` | Hailuo 2.3 — Standard text to video | **prompt** | 6/10 |  |
| `pixverse/v6/text-to-video` | PixVerse V6 — Text to video | **prompt** | 1-15 | 360p/540p/720p/1080p |
| `wan/v2.6/text-to-video` | Wan 2.6 — Text to video | **prompt**, audio_url | 5/10/15 | 720p/1080p |
| `wan/v2.7/text-to-video` | Wan 2.7 — Text to video | **prompt**, audio_url | 2-15 | 720p/1080p |

## Image to video (incl. first/last frame) (22)

| Model id | Name | Inputs | Seconds | Resolution |
|---|---|---|---|---|
| `alibaba/happy-horse/image-to-video` | Happy Horse 1.0 — Image to video | prompt, **image_url** | 2-15 | 720p/1080p |
| `alibaba/happy-horse/v1.1/image-to-video` | HappyHorse 1.1 — Image to video | prompt, **image_url** | 2-15 | 720p/1080p |
| `alibaba/wan-3.0-prime/image-to-video` | Wan 3.0 Prime — Image to video | **prompt**, **image_url**, end_image_url | 2-30 | 480p/720p/1080p |
| `alibaba/wan-3.0/image-to-video` | Wan 3.0 — Image to video | **prompt**, **image_url**, end_image_url | 2-30 | 480p/720p/1080p |
| `bytedance/seedance-2.0/image-to-video` | Seedance 2.0 — Image to video | prompt, **image_url**, end_image_url | 4-15 | 480p/720p/1080p/4k |
| `bytedance/seedance-2.5/image-to-video` | Seedance 2.5 — Image to video | prompt, **image_url**, end_image_url | 4-30 | 480p/720p/1080p |
| `kling-video/o3/first-last-frame` | Kling O3 — First last frame | prompt, last_frame_url, first_frame_url | 3-15 |  |
| `kling-video/omni/first-last-frame` | Kling Omni — First last frame | **prompt**, last_frame_url, **first_frame_url** | 5/10 |  |
| `kling-video/v2.5-turbo/pro/image-to-video` | Kling 2.5 Turbo — Pro image to video | **prompt**, **image_url** | 5/10 |  |
| `kling-video/v2.5-turbo/standard/image-to-video` | Kling 2.5 Turbo — Standard image to video | **prompt**, **image_url** | 5/10 |  |
| `kling-video/v2.6/pro/image-to-video` | Kling 2.6 — Pro image to video | **prompt**, **image_url** | 5/10 |  |
| `kling-video/v3.0-turbo/image-to-video` | Kling 3.0 — Turbo · Image to video | **prompt**, **image_url** | 3-15 | 720p/1080p |
| `kling-video/v3.0/4k/image-to-video` | Kling 3.0 — 4K · Image to video | prompt, **image_url**, last_image_url | 3-15 |  |
| `kling-video/v3.0/pro/image-to-video` | Kling 3.0 — Pro · Image to video | prompt, **image_url**, last_image_url | 3-15 |  |
| `kling-video/v3.0/std/image-to-video` | Kling 3.0 — Standard · Image to video | prompt, **image_url**, last_image_url | 3-15 |  |
| `lightricks/ltx-2.5/image-to-video/fast` | LTX-2.5 — Image to video fast | **prompt**, **image_url**, end_image_url | 6/8/10 | 720p/1080p/2k/4k |
| `lightricks/ltx-2.5/image-to-video/pro` | LTX-2.5 — Image to video pro | **prompt**, **image_url**, end_image_url | 6/8/10 | 720p/1080p |
| `minimax/h3/image-to-video` | MiniMax H3 — Image to video | **prompt**, **image_url**, end_image_url | 5-15 | 2K |
| `minimax/hailuo-2.3/standard/image-to-video` | Hailuo 2.3 — Standard image to video | **prompt**, **image_url** | 6/10 |  |
| `pixverse/v6/image-to-video` | PixVerse V6 — Image to video | **prompt**, **image_url**, end_image_url | 1-15 | 360p/540p/720p/1080p |
| `wan/v2.6/image-to-video` | Wan 2.6 — Image to video | **prompt**, audio_url, **image_url** | 5/10/15 | 480p/720p/1080p |
| `wan/v2.7/image-to-video` | Wan 2.7 — Image to video | prompt, audio_url, **image_url**, end_image_url | 2-15 | 720p/1080p |

## Reference to video (15)

| Model id | Name | Inputs | Seconds | Resolution |
|---|---|---|---|---|
| `alibaba/happy-horse/reference-to-video` | Happy Horse 1.0 — Reference to video | **prompt**, **image_urls** | 2-15 | 720p/1080p |
| `alibaba/happy-horse/v1.1/reference-to-video` | HappyHorse 1.1 — Reference to video | **prompt**, **image_urls** | 2-15 | 720p/1080p |
| `alibaba/wan-3.0-prime/reference-to-video` | Wan 3.0 Prime — Reference to video | **prompt**, audio_urls, image_urls, video_urls | 2-30 | 480p/720p/1080p |
| `alibaba/wan-3.0/reference-to-video` | Wan 3.0 — Reference to video | **prompt**, audio_urls, image_urls, video_urls | 2-30 | 480p/720p/1080p |
| `bytedance/seedance-2.0/reference-to-video` | Seedance 2.0 — Reference to video | prompt, audio_urls, image_urls, video_urls | 4-15 | 480p/720p/1080p/4k |
| `bytedance/seedance-2.5/reference-to-video` | Seedance 2.5 — Reference to video | prompt, audio_urls, image_urls, video_urls | 4-30 | 480p/720p/1080p |
| `higgsfield/cinema-studio/4.0` | Cinema Studio 4.0 — Generate | **prompt**, audio_urls, image_urls, video_urls | 4-30 | 480p/720p |
| `kling-video/o3/image-reference` | Kling O3 — Image reference | prompt, image_urls, last_frame_url, first_frame_url | 3-15 |  |
| `kling-video/o3/video-reference` | Kling O3 — Video reference | **prompt**, image_urls, **video_urls** | 3-10 |  |
| `kling-video/omni/image-reference` | Kling Omni — Image reference | **prompt**, image_urls | 3-10 |  |
| `kling-video/omni/video-reference` | Kling Omni — Video reference | **prompt**, image_urls, **video_urls** | 3-10 |  |
| `minimax/h3/reference-to-video` | MiniMax H3 — Reference to video | **prompt**, audio_urls, image_urls, video_urls | 5-15 | 2K |
| `wan/v2.6/reference-to-video` | Wan 2.6 — Reference to video | **prompt**, **video_urls** | 5/10 | 720p/1080p |
| `wan/v2.7/reference-to-video` | Wan 2.7 — Reference to video | **prompt**, image_urls, video_urls | 2-10 | 720p/1080p |
| `xai/grok-imagine-video/v1.5/reference-to-video` | Grok Imagine Video 1.5 — Reference to video | **prompt**, audio_url, image_url, image_urls | 1-15 | 480p/720p/1080p |

## Video edit / extend (4)

| Model id | Name | Inputs | Seconds | Resolution |
|---|---|---|---|---|
| `bytedance/seedance-2.5/video-edit` | Seedance 2.5 — Video edit | **prompt**, **video_url**, audio_urls, image_urls, video_urls |  | 480p/720p/1080p |
| `bytedance/seedance-2.5/video-extend` | Seedance 2.5 — Video extend | **prompt**, **video_url**, audio_urls, image_urls, video_urls | 4-30 | 480p/720p/1080p |
| `kling-video/o3/video-edit` | Kling O3 — Video edit | **prompt**, image_urls, **video_urls** |  |  |
| `kling-video/omni/video-edit` | Kling Omni — Video edit | **prompt**, image_urls, **video_urls** |  |  |

## Motion transfer / control (5)

| Model id | Name | Inputs | Seconds | Resolution |
|---|---|---|---|---|
| `higgsfield/genjutsu/motion-transfer/v1.0` | Genjutsu — Motion transfer | prompt, **video_url**, **image_urls** |  | 720p/480p/1080p |
| `kling-video/motion-control/pro` | Kling 2.6 Motion Control — Pro | prompt, **image_url**, **video_url** |  |  |
| `kling-video/motion-control/std` | Kling 2.6 Motion Control — Standard | prompt, **image_url**, **video_url** |  |  |
| `kling-video/v3/motion-control/pro` | Kling 3.0 Motion Control — Pro | prompt, **image_url**, **video_url** |  |  |
| `kling-video/v3/motion-control/std` | Kling 3.0 Motion Control — Standard | prompt, **image_url**, **video_url** |  |  |

## Restyle (1)

| Model id | Name | Inputs | Seconds | Resolution |
|---|---|---|---|---|
| `higgsfield/genjutsu/restyle/v1.0` | Genjutsu — Restyle | prompt, **preset_id**, **video_url**, image_urls |  | 480p/720p/1080p |

## Object swap (1)

| Model id | Name | Inputs | Seconds | Resolution |
|---|---|---|---|---|
| `higgsfield/genjutsu/object-swap/v1.0` | Genjutsu — Object swap | prompt, **video_url**, **image_urls** |  | 720p/480p/1080p |

Soul ID characters: `higgsfield_create_character` (POST /v1/custom-references) → use the id as `custom_reference_id` on Soul, Soul 2 or Soul Cinema.
