---
description: "Set up Higgsfield in UEFN Ducky: install and enable the plugin, paste and test the KEY_ID:KEY_SECRET API key, pick default models, how billing works"
metadata:
  label: "Setup"
---

# Higgsfield setup

1. Store → Install **Higgsfield** → Enable.
2. At https://console.higgsfield.ai → API keys, create a key. It has a key ID and a secret.
3. Settings → **Higgsfield** → paste them as `KEY_ID:KEY_SECRET` → **Test** (checks the key and shows what a Soul 2 picture costs).
4. Optional: **Defaults** — the picture model and the text-to-video model tools and nodes use when none is picked.
5. Opt in the `higgsfield_*` tools for the chat. Workflows show the **Higgsfield** node group.

Billing: pay as you go from the API balance in the console (credits expire a year after purchase). Each request is priced by model and settings — `higgsfield_estimate` or a tool call without `confirm_spend` shows it. Failed, NSFW-flagged and canceled-while-queued requests are refunded. Concurrency is limited per account; the plugin waits and retries when it is full.

Higgsfield's hosted MCP (mcp.higgsfield.ai, browser sign-in, plan credits) is a separate product; this plugin uses the API key.
