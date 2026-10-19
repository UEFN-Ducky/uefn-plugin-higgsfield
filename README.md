# Higgsfield

Open-source [UEFN-Ducky](https://github.com/UEFN-Ducky/UEFN-Ducky) Store plugin for the [Higgsfield](https://higgsfield.ai) API: 83 image and video models (Soul, Seedance, Kling, Wan, Hailuo, MiniMax, PixVerse, LTX, Happy Horse, Genjutsu, Cinema Studio, Recraft, Ideogram, Qwen, Grok, Z-Image, Marketing and Ads Studio) from agents and workflows.

Desktop plugin id `higgsfield`. Install or update from **Settings → Store** in the app — do not install from a zip by hand.

## What it does

- **Agent tools** (`higgsfield_*` on the shared `uefn-ducky` MCP): text to image, edit image, text / image / reference to video, edit and extend video, motion transfer, restyle, object swap, any model by id with its own settings, Soul ID characters, plus models, model info, price estimate, status, cancel, download, upload, presets, Soul styles and import to UEFN.
- **Workflow nodes** (the **Higgsfield** group): Text to Image, Edit Image, Text to Video, Image to Video, Reference to Video, Edit Video, Motion Transfer, Restyle Video, Object Swap, Any Model, Estimate and Soul ID Character. Each node lists the models that fit it; files carry their Higgsfield link, so a chain never re-uploads.
- **Backends for the built-in nodes**: seven Higgsfield picture models in Text to Image, and Higgsfield in Edit Image.
- **Ready-made workflows**: prompt → picture → video, prompt to video, island screenshot → cinematic shot, island thumbnail art, a character in a video's moves, edit a picture.
- **Settings → Higgsfield**: the API key (KEY_ID:KEY_SECRET) with Test, and default picture and video models.

The model list and every model's inputs come from Higgsfield's docs (`backend/models.json`); requests are checked against them before anything is sent. Paid jobs never run on their own: tools refuse until `confirm_spend=true` and quote Higgsfield's own estimate (agents ask you first), and nodes need **Spend credits** on.

Higgsfield's hosted MCP (`mcp.higgsfield.ai`) signs in through the browser and uses plan credits; this plugin uses the API key from console.higgsfield.ai and its pay-as-you-go balance instead.

## Build

```bash
py scripts/build_zip.py
py scripts/release.py --publish --changelog "…"   # commit + push, zip, upload, publish to the Store
```

## Test

```bash
py -m pytest -q --import-mode=importlib backend/test_higgsfield.py
```

No network and no credits: the self-check fakes Higgsfield's API.

## Secrets

Never commit keys. The app stores `higgsfield_api_key` locally (encrypted), not in this package.

## License

MIT. Copyright (c) 2026 Mindful Path Company, LLC. See [LICENSE](LICENSE). Higgsfield is a trademark of its owners; this plugin is not affiliated with Higgsfield AI. Model names belong to their makers.
