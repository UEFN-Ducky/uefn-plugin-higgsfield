"""higgsfield_* MCP tools on the shared uefn-ducky server.

Paid jobs refuse unless confirm_spend=true (after a ducky_ask_user yes); the refusal quotes
Higgsfield's own estimate for the exact settings. wait=true polls and downloads the result.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from . import higgsfield as h

INTENT = (
    r"\b(higgsfield|seedance|kling|soul\s*(?:id|2|cinema)?|genjutsu|wan\s*\d|hailuo|minimax|pixverse|ltx|"
    r"happy\s*horse|recraft|ideogram|qwen\s*image|z-?image|grok\s*imagine|cinema\s*studio|marketing\s*studio|ads\s*studio|"
    r"text[- ]?to[- ]?video|image[- ]?to[- ]?video|motion\s*(?:transfer|control)|restyle|object\s*swap|ai\s*video)\b"
)

_DOWNLOADS: dict[str, Path] = {}


def _dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


def download_root(api: Any = None) -> Path:
    if "root" not in _DOWNLOADS:
        root: Path | None = None
        if api is not None and hasattr(api, "local_dir"):
            try:
                root = Path(api.local_dir("downloads"))
            except Exception:  # noqa: BLE001 — older apps: temp folder
                root = None
        if root is None:
            root = Path(tempfile.gettempdir()) / "uefn-ducky-higgsfield" / "downloads"
        root.mkdir(parents=True, exist_ok=True)
        _DOWNLOADS["root"] = root
    return _DOWNLOADS["root"]


def names(raw: Any, limit: int = 20) -> list[str]:
    """A comma/newline list or a JSON array → items."""
    if isinstance(raw, list):
        items = raw
    else:
        text = str(raw or "").strip()
        items = json.loads(text) if text.startswith("[") else [p for p in text.replace("\n", ",").split(",")]
    return [str(i).strip() for i in items if str(i).strip()][:limit]


def summary(parsed: dict[str, Any]) -> dict[str, Any]:
    keep = ("request_id", "model", "status", "finished", "failed", "failure_reason", "video_url", "image_urls",
            "downloaded", "output_dir", "estimate")
    out = {k: parsed[k] for k in keep if k in parsed and parsed[k] not in (None, "", [])}
    if out.get("request_id"):
        out["task_id"] = out["request_id"]  # the workflow nodes' name for it
    return out


def run_job(client: h.HiggsfieldClient, model: dict[str, Any], params: dict[str, Any], *, wait: bool,
            output_dir: str = "", api: Any = None) -> dict[str, Any]:
    params = client.resolve_params(model, params)
    if not wait:
        sub = client.submit(model["id"], params)
        return {"request_id": sub["request_id"], "model": model["id"], "status": sub.get("status") or "queued",
                "next": "higgsfield_status(request_id, poll=true) then higgsfield_download(request_id)"}
    root = Path(output_dir.strip()) if output_dir.strip() else download_root(api)
    parsed = client.run(model["id"], params, root)
    if not output_dir.strip():
        h.prune_downloads(download_root(api))
    return parsed


def gate_or_none(client: h.HiggsfieldClient, model: dict[str, Any], params: dict[str, Any], confirm_spend: bool, label: str) -> str | None:
    if confirm_spend:
        return None
    try:
        est = client.estimate(model["id"], h.placeholder_params(model, params))
    except h.HiggsfieldError:
        est = None
    return h.credit_gate(False, est, f"{label} with {model['title']}")


def _result(fn: Callable[[], Any]) -> str:
    try:
        res = fn()
    except (h.HiggsfieldError, ValueError, FileNotFoundError, OSError) as exc:
        return f"Error: {exc}"
    if isinstance(res, str):
        return res
    return _dumps(summary(res) if "finished" in res else res)


def register_tools(api: Any) -> None:
    def client() -> h.HiggsfieldClient:
        return h.HiggsfieldClient()

    def job(workflow: str, model_name: str, label: str, *, confirm_spend: bool, wait: bool, output_dir: str,
            extra: Any = "", any_model: bool = False, check: Callable[[dict[str, Any]], str] | None = None, **common: Any) -> Any:
        model = h.find_model(model_name) if (any_model and model_name.strip()) else h.find_model(model_name, workflow)
        if check is not None:
            problem = check(model)
            if problem:
                return f"Error: {problem}"
        params = h.build_params(model, **common, extra=h.parse_extra(extra))
        h.validate(model, params)
        c = client()
        blocked = gate_or_none(c, model, params, confirm_spend, label)
        if blocked:
            return blocked
        return run_job(c, model, params, wait=wait, output_dir=output_dir, api=api)

    if hasattr(api, "register_secret_test"):
        api.register_secret_test(h.SECRET_KEY, h.test_api_key)

    # ------------------------------------------------------------------ catalog and account (free)

    @api.tool(name="higgsfield_models", intent=INTENT)
    def higgsfield_models(workflow: str = "", kind: str = "", query: str = "") -> str:
        """List Higgsfield models (83: Soul, Seedance, Kling, Wan, Hailuo, PixVerse, LTX, Genjutsu, Recraft, Ideogram…). workflow: text-to-image|image-edit|text-to-video|image-to-video|reference-to-video|video-edit|motion|restyle|object-swap. Free."""
        rows = h.models_list(workflow=workflow.strip(), kind=kind.strip(), query=query)
        return _dumps({"count": len(rows), "defaults": h.DEFAULT_MODELS, "models": rows})

    @api.tool(name="higgsfield_model_info", intent=INTENT)
    def higgsfield_model_info(model: str) -> str:
        """One Higgsfield model's full input list (types, choices, defaults, limits) and usage notes. Free."""
        return _result(lambda: h.find_model(model))

    @api.tool(name="higgsfield_estimate", intent=INTENT)
    def higgsfield_estimate(model: str, params: str = "{}") -> str:
        """Higgsfield's own price for a model and settings (params: JSON object) in credits and USD, before spending. Free."""
        def go() -> dict[str, Any]:
            m = h.find_model(model)
            p = h.parse_extra(params)
            unknown = [k for k in p if k not in m["properties"]]
            if unknown:
                raise ValueError(f"{m['title']} has no {', '.join(unknown)}. Its inputs: {', '.join(sorted(m['properties']))}.")
            return {"model": m["id"], **client().estimate(m["id"], h.placeholder_params(m, p))}
        return _result(go)

    @api.tool(name="higgsfield_status", intent=INTENT)
    def higgsfield_status(request_id: str, poll: bool = False, timeout_sec: int = 1800) -> str:
        """Status of a Higgsfield request (queued, in_progress, completed, failed, nsfw, canceled) with its result links. poll=true waits for the end."""
        return _result(lambda: client().wait(request_id, timeout=timeout_sec) if poll else client().status(request_id))

    @api.tool(name="higgsfield_cancel", intent=INTENT)
    def higgsfield_cancel(request_id: str) -> str:
        """Cancel a Higgsfield request that is still queued (refunded). Started ones can't be canceled."""
        def go() -> dict[str, Any]:
            client().cancel(request_id)
            return {"ok": True, "request_id": request_id, "status": "canceled"}
        return _result(go)

    @api.tool(name="higgsfield_download", intent=INTENT)
    def higgsfield_download(request_id: str, output_dir: str = "") -> str:
        """Download every file of a completed Higgsfield request (pictures, video, sound, extras). Results stay at least 7 days."""
        def go() -> dict[str, Any]:
            parsed = client().status(request_id)
            if not parsed["finished"]:
                return {"error": f"Request is {parsed['status']}, not completed", **summary(parsed)}
            dest = Path(output_dir.strip()) if output_dir.strip() else download_root(api) / request_id
            parsed["downloaded"] = h.download_results(parsed, dest)
            parsed["output_dir"] = str(dest)
            return parsed
        return _result(go)

    @api.tool(name="higgsfield_upload", intent=INTENT)
    def higgsfield_upload(path: str) -> str:
        """Upload a local JPG/PNG/WebP/GIF picture, WAV sound or MP4 video; returns the public link any model input takes. Free."""
        return _result(lambda: {"public_url": client().upload(path), "path": path})

    @api.tool(name="higgsfield_presets", intent=INTENT)
    def higgsfield_presets(which: str = "restyle", search: str = "") -> str:
        """Style presets: which=restyle (Genjutsu Restyle preset_id values) or marketing (Marketing Studio preset_id values). Free."""
        return _result(lambda: {"which": which, "presets": client().presets("restyle" if which.startswith("re") else "marketing", search)})

    @api.tool(name="higgsfield_soul_styles", intent=INTENT)
    def higgsfield_soul_styles(version: str = "v2") -> str:
        """Soul style_id values for the Soul picture models (version v2 for Soul 2, v1 for Soul / Soul Cinema). Free."""
        return _result(lambda: {"version": version, "styles": client().soul_styles(version)})

    @api.tool(name="higgsfield_character_status", intent=INTENT)
    def higgsfield_character_status(reference_id: str) -> str:
        """A Soul ID character's training status (not_ready, queued, in_progress, completed, failed). Free."""
        return _result(lambda: client().character(reference_id))

    # ------------------------------------------------------------------ pictures

    @api.tool(name="higgsfield_text_to_image", intent=INTENT)
    def higgsfield_text_to_image(
        prompt: str,
        model: str = "",
        aspect_ratio: str = "",
        resolution: str = "",
        reference_images: str = "",
        seed: int = 0,
        extra: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Higgsfield picture from a prompt (default Soul 2; also Soul Cinema, Z-Image, Recraft, Ideogram, Qwen, Grok, Marketing/Ads Studio). extra: JSON of the model's own settings (style_id, custom_reference_id…)."""
        return _result(lambda: job("text-to-image", model, "text to image", confirm_spend=confirm_spend, wait=wait, output_dir=output_dir,
                                   extra=extra, prompt=prompt, images=names(reference_images), aspect_ratio=aspect_ratio,
                                   resolution=resolution, seed=seed))

    @api.tool(name="higgsfield_edit_image", intent=INTENT)
    def higgsfield_edit_image(
        image: str,
        prompt: str = "",
        model: str = "",
        reference_images: str = "",
        aspect_ratio: str = "",
        resolution: str = "",
        extra: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Change a picture by prompt (default Qwen Image 3 Edit; any picture model that takes an input image works). image: path, link or data: URI."""
        def check(m: dict[str, Any]) -> str:
            return "" if (m["kind"] == "image" and h.takes_image(m)) else f"{m['title']} can't edit pictures; see higgsfield_models(kind='image')."
        return _result(lambda: job("image-edit", model, "image edit", confirm_spend=confirm_spend, wait=wait, output_dir=output_dir,
                                   extra=extra, any_model=True, check=check, prompt=prompt, image=image,
                                   images=names(reference_images), aspect_ratio=aspect_ratio, resolution=resolution))

    # ------------------------------------------------------------------ video

    @api.tool(name="higgsfield_text_to_video", intent=INTENT)
    def higgsfield_text_to_video(
        prompt: str,
        model: str = "",
        duration: int = 0,
        aspect_ratio: str = "",
        resolution: str = "",
        negative_prompt: str = "",
        seed: int = 0,
        extra: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Higgsfield video from a prompt (default Seedance 2.5; also Kling 3/2.6/2.5, Wan 3/2.7/2.6, Hailuo, MiniMax H3, PixVerse 6, LTX 2.5, Happy Horse). Video takes minutes."""
        return _result(lambda: job("text-to-video", model, "text to video", confirm_spend=confirm_spend, wait=wait, output_dir=output_dir,
                                   extra=extra, prompt=prompt, duration=duration, aspect_ratio=aspect_ratio, resolution=resolution,
                                   negative_prompt=negative_prompt, seed=seed))

    @api.tool(name="higgsfield_image_to_video", intent=INTENT)
    def higgsfield_image_to_video(
        image: str,
        prompt: str = "",
        model: str = "",
        end_image: str = "",
        duration: int = 0,
        aspect_ratio: str = "",
        resolution: str = "",
        extra: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Animate a picture into a video (default Seedance 2.5; Kling, Wan, Hailuo, PixVerse, LTX, Happy Horse; first/last frame models take end_image)."""
        return _result(lambda: job("image-to-video", model, "image to video", confirm_spend=confirm_spend, wait=wait, output_dir=output_dir,
                                   extra=extra, prompt=prompt, image=image, end_image=end_image, duration=duration,
                                   aspect_ratio=aspect_ratio, resolution=resolution))

    @api.tool(name="higgsfield_reference_to_video", intent=INTENT)
    def higgsfield_reference_to_video(
        prompt: str,
        images: str = "",
        videos: str = "",
        audios: str = "",
        model: str = "",
        duration: int = 0,
        aspect_ratio: str = "",
        resolution: str = "",
        extra: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Video guided by reference pictures/videos/sounds (characters, products, style) — default Seedance 2.5; also Kling O3/Omni, Wan, MiniMax H3, Grok Imagine, Cinema Studio 4."""
        return _result(lambda: job("reference-to-video", model, "reference to video", confirm_spend=confirm_spend, wait=wait,
                                   output_dir=output_dir, extra=extra, prompt=prompt, images=names(images), videos=names(videos),
                                   audios=names(audios), duration=duration, aspect_ratio=aspect_ratio, resolution=resolution))

    @api.tool(name="higgsfield_edit_video", intent=INTENT)
    def higgsfield_edit_video(
        video: str,
        prompt: str,
        model: str = "",
        extend: bool = False,
        reference_images: str = "",
        duration: int = 0,
        extra: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Edit a video by prompt (Seedance 2.5 edit, Kling O3/Omni edit) or extend=true to continue it (Seedance 2.5 extend)."""
        name = model or ("bytedance/seedance-2.5/video-extend" if extend else "")
        return _result(lambda: job("video-edit", name, "video extend" if extend else "video edit", confirm_spend=confirm_spend,
                                   wait=wait, output_dir=output_dir, extra=extra, prompt=prompt, video=video,
                                   images=names(reference_images), duration=duration))

    @api.tool(name="higgsfield_motion_transfer", intent=INTENT)
    def higgsfield_motion_transfer(
        video: str,
        image: str,
        model: str = "",
        prompt: str = "",
        extra: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Put the character in a picture into a video's motion (Genjutsu Motion Transfer, Kling 3 / 2.6 Motion Control)."""
        return _result(lambda: job("motion", model, "motion transfer", confirm_spend=confirm_spend, wait=wait, output_dir=output_dir,
                                   extra=extra, prompt=prompt, video=video, image=image))

    @api.tool(name="higgsfield_restyle_video", intent=INTENT)
    def higgsfield_restyle_video(
        video: str,
        preset_id: str,
        reference_images: str = "",
        prompt: str = "",
        resolution: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Restyle a video (≥4 s, first 30 s used) in a Genjutsu style preset, keeping its motion and sound. preset_id from higgsfield_presets('restyle')."""
        return _result(lambda: job("restyle", "", "restyle", confirm_spend=confirm_spend, wait=wait, output_dir=output_dir,
                                   extra={"preset_id": preset_id.strip()}, prompt=prompt, video=video,
                                   images=names(reference_images, 5), resolution=resolution))

    @api.tool(name="higgsfield_object_swap", intent=INTENT)
    def higgsfield_object_swap(
        video: str,
        images: str,
        prompt: str = "",
        extra: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Swap an object in a video for the one in the pictures (Genjutsu Object Swap)."""
        return _result(lambda: job("object-swap", "", "object swap", confirm_spend=confirm_spend, wait=wait, output_dir=output_dir,
                                   extra=extra, prompt=prompt, video=video, images=names(images)))

    @api.tool(name="higgsfield_generate", intent=INTENT)
    def higgsfield_generate(
        model: str,
        params: str = "{}",
        prompt: str = "",
        image: str = "",
        images: str = "",
        video: str = "",
        audio: str = "",
        duration: int = 0,
        aspect_ratio: str = "",
        resolution: str = "",
        confirm_spend: bool = False,
        wait: bool = True,
        output_dir: str = "",
    ) -> str:
        """Run ANY Higgsfield model by endpoint id (higgsfield_models / higgsfield_model_info): params = JSON of its own fields; local files in *_url fields are uploaded."""
        return _result(lambda: job("", model, "generation", confirm_spend=confirm_spend, wait=wait, output_dir=output_dir,
                                   extra=params, any_model=True, prompt=prompt, image=image, images=names(images), video=video,
                                   audio=audio, duration=duration, aspect_ratio=aspect_ratio, resolution=resolution))

    # ------------------------------------------------------------------ Soul ID characters

    @api.tool(name="higgsfield_create_character", intent=INTENT)
    def higgsfield_create_character(
        name: str,
        images: str,
        model_version: str = "v2",
        confirm_spend: bool = False,
        wait: bool = True,
        timeout_sec: int = 3600,
    ) -> str:
        """Train a Soul ID character from 1-100 photos of one person; its id goes in custom_reference_id of the matching Soul model (v1 Soul, v2 Soul 2, cinema Soul Cinema)."""
        def go() -> Any:
            pics = names(images, 100)
            if not name.strip() or not pics:
                return "Error: name and at least one picture are required"
            if model_version not in ("v1", "v2", "cinema"):
                return "Error: model_version must be v1, v2 or cinema"
            if not confirm_spend:
                return h.credit_gate(False, None, f"Soul ID training ({len(pics)} photos)")
            c = client()
            made = c.create_character(name, [c.resolve(p, "picture") for p in pics], model_version)
            if not wait or not made.get("id"):
                return made
            deadline = time.monotonic() + max(60, int(timeout_sec))
            while str(made.get("status")) not in ("completed", "failed") and time.monotonic() < deadline:
                time.sleep(10)
                made = c.character(str(made["id"]))
            return {**made, "use_as": {"custom_reference_id": made.get("id")}}
        return _result(go)

    # ------------------------------------------------------------------ landing

    @api.tool(name="higgsfield_import_to_uefn", intent=INTENT)
    def higgsfield_import_to_uefn(path: str, destination_path: str = "", replace_existing: bool = True) -> str:
        """Import a downloaded Higgsfield picture, sound or video into the open UEFN project's Content Browser (default folder Higgsfield)."""
        def go() -> dict[str, Any]:
            local = Path(path.strip()).expanduser()
            if not local.is_file():
                raise h.HiggsfieldError(f"file not found: {path}")
            dest = destination_path.strip() or "Higgsfield"
            result = api.listener("import_asset", {"source_file": str(local.resolve()), "destination_path": dest,
                                                   "replace_existing": bool(replace_existing)})
            return {"ok": True, "path": str(local), "destination_path": dest, "uefn": result}
        try:
            return _result(go)
        except Exception as exc:  # noqa: BLE001 — the listener being offline is this tool's answer
            return f"Error importing to UEFN: {exc}. Is UEFN open with the Ducky listener online?"

    api.log("higgsfield tools registered")
