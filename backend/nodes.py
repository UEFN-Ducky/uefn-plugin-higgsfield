"""Higgsfield workflow nodes (contributes.automations.nodes in plugin.json).

Value nodes: each runs when something needs what it makes. Paid nodes keep the spend lock
(they only run with "Spend credits" on) and say Higgsfield's own estimate when they stop.
Results travel as file refs that keep their Higgsfield link, so the next Higgsfield node reads
the link instead of uploading the file again.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from . import higgsfield as h
from .tools import download_root

PROVIDER = "Higgsfield"
_STATE: dict[str, Any] = {"api": None, "client": None}

Ctx = dict[str, Any]


def _client() -> h.HiggsfieldClient:
    factory = _STATE.get("client")
    return factory() if callable(factory) else h.HiggsfieldClient()


def _cfg(ctx: Ctx) -> dict[str, Any]:
    return ctx.get("config") if isinstance(ctx.get("config"), dict) else {}


def _inputs(ctx: Ctx) -> dict[str, Any]:
    return ctx.get("inputs") if isinstance(ctx.get("inputs"), dict) else {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value).strip()


def _list(value: Any) -> list[Any]:
    if value in (None, "", []):
        return []
    return value if isinstance(value, list) else [value]


def _media(value: Any, what: str) -> str:
    """A wired file: its Higgsfield link when a Higgsfield node made it, else the file on this PC."""
    ref = value[0] if isinstance(value, list) and value else value
    if isinstance(ref, dict):
        if ref.get("plugin_id") == h.PLUGIN_ID and h.is_url(str(ref.get("remote") or "")):
            return str(ref["remote"])
        path = str(ref.get("path") or ref.get("remote") or ref.get("url") or "")
    else:
        path = str(ref or "").strip()
    if path and not h.is_url(path) and not Path(path).is_file():
        raise ValueError(f"{what} {Path(path).name} isn't on this PC any more.")
    return path


def _folder(ctx: Ctx) -> Path:
    art = str(ctx.get("artifact_dir") or "").strip()
    return Path(art) / "higgsfield" if art else download_root(_STATE.get("api"))


def _link(path: str) -> str:
    api = _STATE.get("api")
    try:
        return str(api.media_url(path)) if api is not None and hasattr(api, "media_url") else ""
    except Exception:  # noqa: BLE001 — a link is only for the editor's preview
        return ""


def file_ref(path: str, parsed: dict[str, Any], remote: str = "") -> dict[str, Any]:
    ref: dict[str, Any] = {"kind": h.kind_of(path), "path": path, "name": Path(path).name, "provider": PROVIDER,
                           "plugin_id": h.PLUGIN_ID, "task_id": str(parsed.get("request_id") or "")}
    if remote:
        ref["remote"] = remote
    url = _link(path)
    if url:
        ref["url"] = url
    return ref


def outputs(parsed: dict[str, Any]) -> dict[str, Any]:
    """The finished request's files on the output pins: image(s), video, audio, all files."""
    paths = list(parsed.get("downloaded") or [])
    remotes = {"image": list(parsed.get("image_urls") or []), "video": [parsed.get("video_url")] if parsed.get("video_url") else []}
    refs: dict[str, list[dict[str, Any]]] = {"image": [], "video": [], "audio": []}
    files: list[dict[str, Any]] = []
    for path in paths:
        kind = h.kind_of(path)
        pool = remotes.get(kind, [])
        ref = file_ref(path, parsed, pool[len(refs[kind])] if kind in refs and len(refs[kind]) < len(pool) else "")
        if kind in refs:
            refs[kind].append(ref)
        files.append(ref)
    if not files:
        return {"ok": False, "error": "Higgsfield finished but sent no files back."}
    out: dict[str, Any] = {"ok": True, "files": files, "request_id": str(parsed.get("request_id") or "")}
    if refs["image"]:
        out["image"], out["images"] = refs["image"][0], refs["image"]
    if refs["video"]:
        out["video"] = refs["video"][0]
    if refs["audio"]:
        out["audio"] = refs["audio"][0]
    return out


def _guard(fn: Callable[[Ctx], dict[str, Any]]) -> Callable[[Ctx], dict[str, Any]]:
    def handler(ctx: Ctx) -> dict[str, Any]:
        try:
            return fn(ctx if isinstance(ctx, dict) else {})
        except (h.HiggsfieldError, ValueError, OSError) as exc:
            return {"ok": False, "error": str(exc)}
    handler.__name__ = fn.__name__
    handler.__doc__ = fn.__doc__
    return handler


def _spend(cfg: dict[str, Any], model: dict[str, Any], params: dict[str, Any], label: str) -> dict[str, Any] | None:
    if cfg.get("spend") is True:
        return None
    try:
        cost = h.cost_text(_client().estimate(model["id"], h.placeholder_params(model, params)))
    except h.HiggsfieldError as exc:
        cost = "Higgsfield credits (add your key in Settings → Higgsfield to see the price)" if "not set" in str(exc) else h.cost_text(None)
    return {"ok": False, "error": f"Higgsfield {label} with {model['title']} costs {cost} a run. "
                                  "Turn on Spend credits in this node's details to let it run."}


def _generate(ctx: Ctx, workflow: str, label: str, *, check: Callable[[dict[str, Any]], str] | None = None,
              fixed: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg, inp = _cfg(ctx), _inputs(ctx)
    name = str(cfg.get("model") or "").strip()
    model = h.find_model(name) if (name and workflow in ("", "image-edit")) else h.find_model(name, workflow)
    if check is not None:
        problem = check(model)
        if problem:
            return {"ok": False, "error": problem}
    duration = inp.get("duration") if inp.get("duration") not in (None, "") else cfg.get("duration")
    params = h.build_params(
        model,
        prompt=_text(inp.get("prompt")),
        negative_prompt=_text(inp.get("negative")),
        image=_media(inp.get("image"), "Image"),
        images=[_media(r, "Reference") for r in _list(inp.get("images") or inp.get("refs"))],
        end_image=_media(inp.get("end_image"), "End frame"),
        video=_media(inp.get("video"), "Video"),
        audio=_media(inp.get("audio"), "Sound"),
        duration=duration,
        aspect_ratio=str(cfg.get("aspect_ratio") or ""),
        resolution=str(cfg.get("resolution") or ""),
        extra={**h.parse_extra(cfg.get("extra") or cfg.get("params")), **(fixed or {})},
    )
    h.validate(model, params)
    blocked = _spend(cfg, model, params, label)
    if blocked:
        return blocked
    client = _client()
    parsed = client.run(model["id"], client.resolve_params(model, params), _folder(ctx))
    if not str(ctx.get("artifact_dir") or "").strip():
        h.prune_downloads(download_root(_STATE.get("api")))
    out = outputs(parsed)
    if out.get("ok"):
        out["model"] = model["id"]
    return out


# --------------------------------------------------------------------------- nodes


@_guard
def text_to_image(ctx: Ctx) -> dict[str, Any]:
    if not _text(_inputs(ctx).get("prompt")):
        return {"ok": False, "error": "Nothing in Prompt: wire text in or type it in the details."}
    return _generate(ctx, "text-to-image", "Text to Image")


@_guard
def edit_image(ctx: Ctx) -> dict[str, Any]:
    def check(m: dict[str, Any]) -> str:
        return "" if (m["kind"] == "image" and h.takes_image(m)) else f"{m['title']} can't edit pictures; pick another model."
    if not _media(_inputs(ctx).get("image"), "Image"):
        return {"ok": False, "error": "Nothing in Image: wire a picture in."}
    return _generate(ctx, "image-edit", "Edit Image", check=check)


@_guard
def text_to_video(ctx: Ctx) -> dict[str, Any]:
    if not _text(_inputs(ctx).get("prompt")):
        return {"ok": False, "error": "Nothing in Prompt: wire text in or type it in the details."}
    return _generate(ctx, "text-to-video", "Text to Video")


@_guard
def image_to_video(ctx: Ctx) -> dict[str, Any]:
    if not _media(_inputs(ctx).get("image"), "Image"):
        return {"ok": False, "error": "Nothing in Image: wire the picture to animate in."}
    return _generate(ctx, "image-to-video", "Image to Video")


@_guard
def reference_to_video(ctx: Ctx) -> dict[str, Any]:
    return _generate(ctx, "reference-to-video", "Reference to Video")


@_guard
def edit_video(ctx: Ctx) -> dict[str, Any]:
    if not _media(_inputs(ctx).get("video"), "Video"):
        return {"ok": False, "error": "Nothing in Video: wire the video to change in."}
    return _generate(ctx, "video-edit", "Edit Video")


@_guard
def motion_transfer(ctx: Ctx) -> dict[str, Any]:
    return _generate(ctx, "motion", "Motion Transfer")


@_guard
def restyle_video(ctx: Ctx) -> dict[str, Any]:
    preset = str(_cfg(ctx).get("preset_id") or "").strip()
    if not preset:
        return {"ok": False, "error": "Set a Style preset in the details (higgsfield_presets lists them)."}
    return _generate(ctx, "restyle", "Restyle Video", fixed={"preset_id": preset})


@_guard
def object_swap(ctx: Ctx) -> dict[str, Any]:
    return _generate(ctx, "object-swap", "Object Swap")


@_guard
def generate_any(ctx: Ctx) -> dict[str, Any]:
    if not str(_cfg(ctx).get("model") or "").strip():
        return {"ok": False, "error": "Set the Model in the details (an id from higgsfield_models)."}
    return _generate(ctx, "", "generation")


@_guard
def estimate(ctx: Ctx) -> dict[str, Any]:
    cfg = _cfg(ctx)
    model = h.find_model(str(cfg.get("model") or ""), "" if cfg.get("model") else "text-to-image")
    params = h.parse_extra(cfg.get("params"))
    prompt = _text(_inputs(ctx).get("prompt"))
    if prompt and "prompt" in model["properties"]:
        params.setdefault("prompt", prompt)
    est = _client().estimate(model["id"], h.placeholder_params(model, params))
    return {"ok": True, "credits": est.get("credits"), "usd": est.get("usd"), "model": model["id"]}


@_guard
def create_character(ctx: Ctx) -> dict[str, Any]:
    cfg, inp = _cfg(ctx), _inputs(ctx)
    pics = [_media(r, "Photo") for r in _list(inp.get("images"))]
    pics = [p for p in pics if p]
    name = _text(inp.get("name")) or str(cfg.get("name") or "").strip()
    if not pics or not name:
        return {"ok": False, "error": "Soul ID needs a Name and at least one photo of the person."}
    if cfg.get("spend") is not True:
        return {"ok": False, "error": "Training a Soul ID character costs Higgsfield credits. Turn on Spend credits in this node's details to let it run."}
    version = str(cfg.get("version") or "v2")
    client = _client()
    made = client.create_character(name, [client.resolve(p, "Photo") for p in pics], version if version in ("v1", "v2", "cinema") else "v2")
    for _ in range(360):  # up to an hour
        if str(made.get("status")) in ("completed", "failed") or not made.get("id"):
            break
        time.sleep(10)
        made = client.character(str(made["id"]))
    if str(made.get("status")) != "completed":
        return {"ok": False, "error": f"Soul ID training {made.get('status') or 'did not start'}: {made.get('fail_reason') or ''}".strip()}
    return {"ok": True, "reference_id": str(made["id"]), "info": made}


HANDLERS: dict[str, Callable[[Ctx], dict[str, Any]]] = {
    "higgsfield.text_to_image": text_to_image,
    "higgsfield.edit_image": edit_image,
    "higgsfield.text_to_video": text_to_video,
    "higgsfield.image_to_video": image_to_video,
    "higgsfield.reference_to_video": reference_to_video,
    "higgsfield.edit_video": edit_video,
    "higgsfield.motion_transfer": motion_transfer,
    "higgsfield.restyle_video": restyle_video,
    "higgsfield.object_swap": object_swap,
    "higgsfield.generate": generate_any,
    "higgsfield.estimate": estimate,
    "higgsfield.create_character": create_character,
}


def register_nodes(api: Any) -> None:
    _STATE["api"] = api
    if not hasattr(api, "register_automation_node"):
        return
    for node_type, handler in HANDLERS.items():
        api.register_automation_node(node_type, handler)
