---
description: "The Higgsfield workflow nodes (Text to Image, Edit Image, Text/Image/Reference to Video, Edit Video, Motion Transfer, Restyle, Object Swap, Any Model, Estimate, Soul ID Character), their pins, the built-in node backends and the templates"
metadata:
  label: "Workflow nodes"
---

# Higgsfield workflow nodes

All in the **Higgsfield** group. Value nodes: they run when something needs their output. Paid nodes run only with **Spend credits** on, and when they stop they say Higgsfield's estimate for their settings. Every generator has Model (the models that fit that node), and most have Seconds, Aspect ratio, Resolution and More settings (JSON of the model's own fields).

| Node | In | Out |
|---|---|---|
| `higgsfield.text_to_image` Text to Image | prompt, refs | image, images, files, request_id |
| `higgsfield.edit_image` Edit Image | image, prompt, refs | image, images, files, request_id |
| `higgsfield.text_to_video` Text to Video | prompt, negative, duration | video, files, request_id |
| `higgsfield.image_to_video` Image to Video | image, prompt, end_image, duration | video, files, request_id |
| `higgsfield.reference_to_video` Reference to Video | prompt, images, video, audio, duration | video, files, request_id |
| `higgsfield.edit_video` Edit Video | video, prompt, refs | video, files, request_id |
| `higgsfield.motion_transfer` Motion Transfer | video (moves), image (character), prompt | video, files, request_id |
| `higgsfield.restyle_video` Restyle Video | video, refs (characters), prompt; Style preset id in details | video, files, request_id |
| `higgsfield.object_swap` Object Swap | video, images, prompt | video, files, request_id |
| `higgsfield.generate` Any Model | prompt, image, images, video, audio; Model id + Settings JSON | image, images, video, audio, files |
| `higgsfield.estimate` Estimate (free) | prompt; Model id + Settings JSON | credits, usd |
| `higgsfield.create_character` Soul ID Character | images (photos), name | reference_id, info |

Results keep their Higgsfield link (≥7 days), so wiring one Higgsfield node into the next reuses the link. Pictures from any node (Tripo, Meshy, Text to Image, Input Image) work as inputs; local files are uploaded (JPG/PNG/WebP/GIF, WAV, MP4).

## Built-in nodes on Higgsfield

Text to Image lists Higgsfield · Soul 2, Soul Cinema, Z-Image Turbo, Recraft V4.1, Ideogram 4, Qwen Image 3 and Grok Imagine Image 2. Edit Image (on apps that read plugin backends) lists Higgsfield · Qwen Image 3 Edit and Grok Imagine Image 2.

## Templates (New workflow → "Higgsfield: …")

- Video: prompt → picture → video · prompt to video · island screenshot → cinematic shot · put a character into a video's moves
- Images: island thumbnail art · edit a picture

Building one with tools: `create_workflow_from_template`, or `save_workflow` with these node types and data wires (`kind: "data"`, `source_pin`/`target_pin` as above).
