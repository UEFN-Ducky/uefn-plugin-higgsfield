"""Higgsfield API — HTTP client, model catalog, request building and downloads.

Calls https://api.higgsfield.ai with ``Authorization: Key KEY_ID:KEY_SECRET`` from the
app's encrypted credentials (secret key ``higgsfield_api_key``, saved as KEY_ID:KEY_SECRET).
Every model shares one async lifecycle: submit → request_id → poll status → download.
The model list and each model's request schema come from docs.higgsfield.ai (models.json).
Stdlib only (urllib), so the module also runs outside the app for the self-check.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import random
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Any

log = logging.getLogger("uefn.plugin.higgsfield")

PLUGIN_ID = "higgsfield"
SECRET_KEY = "higgsfield_api_key"
BASE_URL = "https://api.higgsfield.ai"
CONSOLE_URL = "https://console.higgsfield.ai"
USER_AGENT = "UEFN-Ducky-Higgsfield/1.0"
DEFAULT_TIMEOUT = 60
DONE = "completed"
FAILED = frozenset({"failed", "nsfw", "canceled", "cancelled"})
RUNNING = frozenset({"queued", "in_progress", "pending", "processing", ""})
# What Higgsfield's presigned uploads accept.
UPLOAD_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
                ".gif": "image/gif", ".wav": "audio/wav", ".mp4": "video/mp4"}
MEDIA_EXTS = (*UPLOAD_TYPES, ".mov", ".webm", ".mp3", ".m4a", ".ogg", ".zip", ".jsx", ".fbx", ".ply", ".glb")
# The model each workflow uses when none is picked (Settings → Higgsfield can change two of them).
DEFAULT_MODELS = {
    "text-to-image": "higgsfield-ai/soul/v2/standard",
    "image-edit": "alibaba/qwen-image-3/edit",
    "text-to-video": "bytedance/seedance-2.5/text-to-video",
    "image-to-video": "bytedance/seedance-2.5/image-to-video",
    "reference-to-video": "bytedance/seedance-2.5/reference-to-video",
    "video-edit": "bytedance/seedance-2.5/video-edit",
    "motion": "higgsfield/genjutsu/motion-transfer/v1.0",
    "restyle": "higgsfield/genjutsu/restyle/v1.0",
    "object-swap": "higgsfield/genjutsu/object-swap/v1.0",
}
WORKFLOWS = tuple(DEFAULT_MODELS)
# Input fields by role, in the order a model is checked for them.
IMAGE_FIELDS = ("image_url", "first_frame_url", "image_reference_url")
END_IMAGE_FIELDS = ("end_image_url", "last_image_url", "last_frame_url")
_NOT_OUTPUT = frozenset({"status_url", "cancel_url"})
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{5,200}$")
_CATALOG: dict[str, Any] = {}


class HiggsfieldError(Exception):
    def __init__(self, message: str, *, status: int | None = None, detail: Any = None):
        super().__init__(message)
        self.status = status
        self.detail = detail


# --------------------------------------------------------------------------- credentials / prefs


def _saved_credentials() -> str:
    try:
        from backend.agent.secrets import get_key
    except ImportError:
        return ""
    return (get_key(SECRET_KEY) or "").strip()


def split_credentials(raw: str) -> tuple[str, str]:
    """``KEY_ID:KEY_SECRET`` (or the two on separate lines) → (key id, secret)."""
    text = str(raw or "").strip()
    if text.lower().startswith("key "):
        text = text[4:].strip()
    parts = [p for p in re.split(r"[\s:]+", text, maxsplit=1) if p] if ":" not in text else text.split(":", 1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise HiggsfieldError("Paste the Higgsfield key as KEY_ID:KEY_SECRET (both parts from console.higgsfield.ai → API keys).")
    return parts[0].strip(), parts[1].strip()


def auth_header(raw: str) -> dict[str, str]:
    key_id, secret = split_credentials(raw)
    return {"Authorization": f"Key {key_id}:{secret}", "Accept": "application/json", "User-Agent": USER_AGENT}


def plugin_prefs() -> dict[str, Any]:
    try:
        from frontend.ui_web.plugin_host_api import prefs_plugin_get

        prefs = prefs_plugin_get(PLUGIN_ID) or {}
    except Exception:  # noqa: BLE001 — prefs are best-effort
        prefs = {}
    return prefs if isinstance(prefs, dict) else {}


def default_model(workflow: str) -> str:
    pref = {"text-to-image": "default_image_model", "text-to-video": "default_video_model"}.get(workflow)
    chosen = str(plugin_prefs().get(pref) or "").strip() if pref else ""
    return chosen if chosen in catalog() else DEFAULT_MODELS[workflow]


# --------------------------------------------------------------------------- catalog


def catalog() -> dict[str, dict[str, Any]]:
    """Every generation model by its endpoint id (models.json, from docs.higgsfield.ai)."""
    if "models" not in _CATALOG:
        data = json.loads((Path(__file__).with_name("models.json")).read_text(encoding="utf-8"))
        _CATALOG["models"] = {m["id"]: m for m in data["models"]}
    return _CATALOG["models"]


def find_model(name: str, workflow: str = "") -> dict[str, Any]:
    """A model by endpoint id, or by its name when that is unambiguous ("Kling 3.0 Pro image")."""
    models = catalog()
    key = str(name or "").strip().strip("/")
    if not key:
        if not workflow:
            raise ValueError("model is required (see higgsfield_models)")
        return models[default_model(workflow)]
    if key in models:
        return models[key]
    words = [w for w in re.split(r"[^a-z0-9.]+", key.lower()) if w]
    pool = [m for m in models.values() if not workflow or m["workflow"] == workflow]
    hits = [m for m in pool if all(w in (m["id"] + " " + m["title"]).lower() for w in words)]
    if len(hits) == 1:
        return hits[0]
    near = ", ".join(m["id"] for m in (hits or pool)[:8])
    raise ValueError(f"No single Higgsfield model matches {name!r}" + (f" for {workflow}" if workflow else "") + f". Try: {near}")


def models_list(*, workflow: str = "", kind: str = "", query: str = "") -> list[dict[str, Any]]:
    q = query.strip().lower()
    out = []
    for m in catalog().values():
        if workflow and m["workflow"] != workflow:
            continue
        if kind and m["kind"] != kind:
            continue
        if q and q not in (m["id"] + " " + m["title"]).lower():
            continue
        out.append({"id": m["id"], "title": m["title"], "kind": m["kind"], "workflow": m["workflow"],
                    "required": m["required"], "inputs": sorted(m["properties"])})
    return out


def takes_image(model: dict[str, Any]) -> bool:
    props = model["properties"]
    return any(f in props for f in (*IMAGE_FIELDS, "image_urls"))


def media_fields(model: dict[str, Any]) -> list[str]:
    """Fields that carry a file link (single or list)."""
    return [k for k, v in model["properties"].items()
            if k.endswith(("_url", "_urls")) and k not in ("link_url",) or v.get("format") == "uri"]


# --------------------------------------------------------------------------- request building


def _pick(enum: list[Any], value: Any, what: str) -> Any:
    if value in enum:
        return value
    low = str(value).strip().lower()
    for option in enum:
        if str(option).lower() == low:
            return option
    raise ValueError(f"{what} {value!r} isn't offered here; pick one of {', '.join(map(str, enum))}.")


def _duration(spec: dict[str, Any], value: Any) -> int:
    seconds = int(round(float(value)))
    enum = spec.get("enum")
    if enum:
        return min(enum, key=lambda d: (abs(int(d) - seconds), -int(d)))  # the nearest allowed length
    lo, hi = spec.get("minimum"), spec.get("maximum")
    if lo is not None:
        seconds = max(int(lo), seconds)
    if hi is not None:
        seconds = min(int(hi), seconds)
    return seconds


def build_params(
    model: dict[str, Any],
    *,
    prompt: str = "",
    negative_prompt: str = "",
    image: str = "",
    images: list[str] | None = None,
    end_image: str = "",
    video: str = "",
    videos: list[str] | None = None,
    audio: str = "",
    audios: list[str] | None = None,
    duration: Any = None,
    aspect_ratio: str = "",
    resolution: str = "",
    seed: Any = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Common inputs → this model's own field names (only the fields it has)."""
    props = model["properties"]
    out: dict[str, Any] = {}
    title = model["title"]
    refs = [str(x) for x in images or [] if str(x).strip()]

    def need(field_names: tuple[str, ...], what: str) -> str:
        found = next((f for f in field_names if f in props), "")
        if not found:
            raise ValueError(f"{title} doesn't take {what}.")
        return found

    if prompt.strip():
        if "prompt" not in props:
            raise ValueError(f"{title} doesn't take a prompt.")
        out["prompt"] = prompt.strip()
    if negative_prompt.strip() and "negative_prompt" in props:
        out["negative_prompt"] = negative_prompt.strip()
    if image.strip():
        field = next((f for f in IMAGE_FIELDS if f in props), "")
        if field:
            out[field] = image.strip()
        elif "image_urls" in props:
            refs.insert(0, image.strip())
        else:
            raise ValueError(f"{title} doesn't take a picture.")
    if refs:
        if "image_urls" in props:
            cap = props["image_urls"].get("maxItems")
            out["image_urls"] = refs[: int(cap)] if cap else refs
        elif not any(f in out for f in IMAGE_FIELDS):
            out[need(IMAGE_FIELDS, "a picture")] = refs[0]
        else:
            raise ValueError(f"{title} takes one picture, not reference pictures.")
    if end_image.strip():
        out[need(END_IMAGE_FIELDS, "an end frame")] = end_image.strip()
    vids = [v for v in [video, *(videos or [])] if str(v).strip()]
    if vids:
        if "video_url" in props:
            out["video_url"] = vids[0]
            if len(vids) > 1 and "video_urls" in props:
                out["video_urls"] = vids[1:]
        elif "video_urls" in props:
            out["video_urls"] = vids
        else:
            raise ValueError(f"{title} doesn't take a video.")
    sounds = [a for a in [audio, *(audios or [])] if str(a).strip()]
    if sounds:
        if "audio_url" in props and len(sounds) == 1:
            out["audio_url"] = sounds[0]
        elif "audio_urls" in props:
            out["audio_urls"] = sounds
        elif "audio_url" in props:
            out["audio_url"] = sounds[0]
        else:
            raise ValueError(f"{title} doesn't take sound.")
    if duration not in (None, "", 0):
        if "duration" not in props:
            raise ValueError(f"{title} has no duration setting.")
        out["duration"] = _duration(props["duration"], duration)
    for field, value in (("aspect_ratio", aspect_ratio), ("resolution", resolution)):
        if str(value or "").strip():
            if field not in props:
                raise ValueError(f"{title} has no {field.replace('_', ' ')} setting.")
            enum = props[field].get("enum")
            out[field] = _pick(enum, str(value).strip(), field.replace("_", " ")) if enum else str(value).strip()
    if seed not in (None, "", 0) and "seed" in props:
        out["seed"] = int(seed)
    for key, value in (extra or {}).items():
        out[key] = value
    return out


def validate(model: dict[str, Any], params: dict[str, Any]) -> None:
    """Refuse what Higgsfield would reject: unknown fields, missing required ones, bad choices."""
    props = model["properties"]
    unknown = [k for k in params if k not in props]
    if unknown:
        raise ValueError(f"{model['title']} has no {', '.join(unknown)}. Its inputs: {', '.join(sorted(props))}.")
    missing = [k for k in model["required"] if params.get(k) in (None, "", [])]
    if missing:
        raise ValueError(f"{model['title']} needs {', '.join(missing)}.")
    for key, value in params.items():
        spec = props[key]
        if spec.get("enum") and value not in spec["enum"]:
            raise ValueError(f"{key} {value!r} isn't offered by {model['title']}; pick one of {', '.join(map(str, spec['enum']))}.")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if spec.get("minimum") is not None and value < spec["minimum"]:
                raise ValueError(f"{key} is at least {spec['minimum']} for {model['title']}.")
            if spec.get("maximum") is not None and value > spec["maximum"]:
                raise ValueError(f"{key} is at most {spec['maximum']} for {model['title']}.")
        if isinstance(value, list) and spec.get("maxItems") is not None and len(value) > spec["maxItems"]:
            raise ValueError(f"{key} takes at most {spec['maxItems']} for {model['title']}.")


def parse_extra(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"More settings must be a JSON object like {{\"seed\": 7}}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("More settings must be a JSON object like {\"seed\": 7}.")
    return data


# --------------------------------------------------------------------------- files


def is_url(value: str) -> bool:
    return str(value).startswith(("http://", "https://"))


def looks_like_path(value: str) -> bool:
    if is_url(value):
        return False
    return "\\" in value or "/" in value or (len(value) > 2 and value[1] == ":") or value.lower().endswith(MEDIA_EXTS)


def data_uri_to_file(uri: str) -> Path:
    head, _, payload = uri.partition(",")
    if ";base64" not in head:
        raise HiggsfieldError("Only base64 data: URIs can be uploaded.")
    mime = head[5:].split(";", 1)[0].lower()
    ext = next((e for e, m in UPLOAD_TYPES.items() if m == mime), ".png")
    try:
        raw = base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise HiggsfieldError(f"Bad data: URI: {exc}") from exc
    folder = Path(tempfile.gettempdir()) / "uefn-ducky-higgsfield"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"inline-{uuid.uuid4().hex[:12]}{ext}"
    dest.write_bytes(raw)
    return dest


def sniff_ext(head: bytes) -> str:
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if head[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return ".wav"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if head[4:8] == b"ftyp":
        return ".mov" if head[8:10] == b"qt" else ".mp4"
    if head[:4] == b"\x1aE\xdf\xa3":
        return ".webm"
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return ".mp3"
    if head[:4] == b"PK\x03\x04":
        return ".zip"
    if head[:4] == b"glTF":
        return ".glb"
    if head.startswith(b"Kaydara FBX Binary"):
        return ".fbx"
    if head[:4] == b"ply\n" or head[:5] == b"ply\r\n":
        return ".ply"
    return ""


def url_ext(url: str) -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return suffix if suffix in MEDIA_EXTS or suffix in (".jpeg",) else ""


def safe_extract(zip_path: Path, folder: Path) -> list[str]:
    out: list[str] = []
    folder.mkdir(parents=True, exist_ok=True)
    root = folder.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            target = (folder / info.filename).resolve()
            if root not in target.parents:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            out.append(str(target))
    return out


def prune_downloads(root: Path, *, keep: int = 80, max_age_days: float = 14) -> None:
    try:
        folders = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return
    cutoff = time.time() - max_age_days * 86400
    for n, folder in enumerate(folders):
        try:
            if n >= keep or folder.stat().st_mtime < cutoff:
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass


def kind_of(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return "image"
    if ext in (".mp4", ".mov", ".webm"):
        return "video"
    if ext in (".mp3", ".wav", ".m4a", ".ogg"):
        return "audio"
    if ext in (".glb", ".fbx", ".ply"):
        return "mesh"
    return "file"


# --------------------------------------------------------------------------- status parsing


def collect_outputs(raw: Any, prefix: str = "") -> list[dict[str, str]]:
    """Every result file in a status body: images[].url, video.url, audio(s), extra artifacts."""
    found: list[dict[str, str]] = []
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in _NOT_OUTPUT:
                continue
            name = f"{prefix}{key}"
            if key == "url" and isinstance(value, str) and is_url(value):
                found.append({"key": prefix.rstrip(".") or "file", "url": value})
            elif isinstance(value, str) and key.endswith("_url") and is_url(value) and prefix:
                found.append({"key": name, "url": value})
            elif isinstance(value, (dict, list)):
                found.extend(collect_outputs(value, f"{name}."))
    elif isinstance(raw, list):
        for n, value in enumerate(raw):
            found.extend(collect_outputs(value, f"{prefix}{n}."))
    return found


def failure_reason(raw: dict[str, Any]) -> str:
    status = str(raw.get("status") or "").lower()
    if status == "nsfw":
        return "Higgsfield's content check refused the prompt, a picture or the result (nsfw); no credits were spent. Change the input."
    if status in ("canceled", "cancelled"):
        return "The Higgsfield request was canceled before it started; nothing was charged."
    err = raw.get("error")
    msg = err.get("message") if isinstance(err, dict) else err
    return f"{msg or 'Higgsfield generation failed'}; no credits were spent."


def parse_status(raw: dict[str, Any]) -> dict[str, Any]:
    status = str(raw.get("status") or "").strip().lower()
    finished = status == DONE
    failed = not finished and (status in FAILED or status not in RUNNING)
    results = collect_outputs({k: v for k, v in raw.items() if k not in ("request_id", "status", "error")})
    video = raw.get("video") if isinstance(raw.get("video"), dict) else {}
    images = [img.get("url") for img in raw.get("images") or [] if isinstance(img, dict) and img.get("url")]
    return {
        "request_id": raw.get("request_id"),
        "status": status or "unknown",
        "finished": finished,
        "failed": failed,
        "failure_reason": failure_reason(raw) if failed else None,
        "video_url": video.get("url") or "",
        "image_urls": images,
        "results": results,
    }


# --------------------------------------------------------------------------- client


def _urlopen(req: urllib.request.Request, timeout: float):  # tests replace this
    return urllib.request.urlopen(req, timeout=timeout)


def _detail(raw: str) -> str:
    try:
        data = json.loads(raw) if raw else {}
    except ValueError:
        return raw[:300]
    detail = data.get("detail", data) if isinstance(data, dict) else data
    if isinstance(detail, list):  # FastAPI validation errors
        parts = []
        for item in detail[:5]:
            if isinstance(item, dict):
                where = ".".join(str(x) for x in item.get("loc") or [] if x != "body")
                parts.append(f"{where}: {item.get('msg')}" if where else str(item.get("msg")))
        return "; ".join(parts)
    return str(detail)[:400]


def error_message(status: int | None, detail: str) -> str:
    if status == 401:
        return "Higgsfield rejected the key (401). Paste KEY_ID:KEY_SECRET from console.higgsfield.ai in Settings → Higgsfield and press Test."
    if status == 403:
        return "Higgsfield: not enough credits (403). Top up at console.higgsfield.ai."
    if status == 404:
        return f"Higgsfield: not found for this account (404){': ' + detail if detail else ''}."
    if status == 423:
        return "Higgsfield: this model is blocked for now (423). Try later or another model."
    if status == 503:
        return "Higgsfield: this model is off or not ready (503). Try later or another model."
    if status == 422:
        return f"Higgsfield refused the settings (422): {detail}"
    return f"Higgsfield error {status}" + (f": {detail}" if detail else "")


def _busy(status: int | None, detail: str) -> bool:
    return status == 400 and "concurrent" in detail.lower()


class HiggsfieldClient:
    def __init__(self, credentials: str | None = None, *, base_url: str = BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        raw = (credentials if credentials is not None else _saved_credentials()).strip()
        if not raw:
            raise HiggsfieldError("Higgsfield API key not set. Paste KEY_ID:KEY_SECRET in Settings → Higgsfield (console.higgsfield.ai → API keys).")
        self.headers = auth_header(raw)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _send(self, req: urllib.request.Request, *, retries: int = 3, busy_waits: int = 0) -> Any:
        delay = 1.0
        busy = 0
        for attempt in range(retries + busy_waits + 1):
            try:
                with _urlopen(req, self.timeout) as resp:
                    body = resp.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as exc:
                raw = ""
                try:
                    raw = exc.read().decode("utf-8", "replace")
                except Exception:  # noqa: BLE001
                    pass
                detail = _detail(raw)
                if _busy(exc.code, detail) and busy < busy_waits:
                    busy += 1  # account concurrency reached: wait for a running request to finish
                    time.sleep(10 * busy)
                    continue
                if exc.code >= 500 and exc.code not in (503,) and attempt < retries:
                    time.sleep(delay + random.uniform(0, 0.5))
                    delay *= 2
                    continue
                if _busy(exc.code, detail):
                    raise HiggsfieldError(f"Higgsfield is busy: {detail}. Wait for a running request to finish.", status=400, detail=detail) from exc
                raise HiggsfieldError(error_message(exc.code, detail), status=exc.code, detail=detail) from exc
            except urllib.error.URLError as exc:
                if attempt < retries:
                    time.sleep(delay + random.uniform(0, 0.5))
                    delay *= 2
                    continue
                raise HiggsfieldError(f"Can't reach Higgsfield: {exc.reason}") from exc
            if not body.strip():
                return {}
            try:
                return json.loads(body)
            except ValueError as exc:
                raise HiggsfieldError(f"Higgsfield sent something that isn't JSON: {body[:200]}") from exc
        raise HiggsfieldError("Higgsfield did not answer after several tries.")

    def request(self, method: str, path: str, body: Any = None, *, idempotency_key: str = "", retries: int = 3,
                busy_waits: int = 0) -> Any:
        headers = dict(self.headers)
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        url = path if is_url(path) else f"{self.base_url}/{path.lstrip('/')}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        return self._send(req, retries=retries, busy_waits=busy_waits)

    # ---- account check

    def check(self) -> str:
        """Free: a lookup of a request that doesn't exist answers 404 with a good key, 401 with a bad one."""
        try:
            self.request("GET", f"/requests/{uuid.uuid4()}/status", retries=1)
        except HiggsfieldError as exc:
            if exc.status == 404:
                return "Connected"
            raise
        return "Connected"

    # ---- generation

    def submit(self, model_id: str, params: dict[str, Any]) -> dict[str, Any]:
        # One key per generation: a retry after a lost answer returns the same request, never a second charge.
        data = self.request("POST", f"/{model_id}", params, idempotency_key=str(uuid.uuid4()), busy_waits=3)
        if not isinstance(data, dict) or not data.get("request_id"):
            raise HiggsfieldError(f"Higgsfield sent no request id: {data}")
        return data

    def status(self, request_id: str) -> dict[str, Any]:
        rid = urllib.parse.quote(str(request_id or "").strip(), safe="")
        if not rid:
            raise HiggsfieldError("request_id is required")
        data = self.request("GET", f"/requests/{rid}/status")
        parsed = parse_status(data if isinstance(data, dict) else {})
        parsed["request_id"] = parsed.get("request_id") or str(request_id)
        return parsed

    def wait(self, request_id: str, *, timeout: float = 1800) -> dict[str, Any]:
        deadline = time.monotonic() + max(10.0, float(timeout))
        delay = 2.0
        while True:
            parsed = self.status(request_id)
            if parsed["finished"] or parsed["failed"]:
                return parsed
            if time.monotonic() >= deadline:
                raise HiggsfieldError(f"Higgsfield request {request_id} was still {parsed['status']} after {int(timeout)} s; check it later with higgsfield_status.")
            time.sleep(delay + random.uniform(0, 0.5))
            delay = min(delay * 1.5, 10.0)

    def cancel(self, request_id: str) -> None:
        rid = urllib.parse.quote(str(request_id or "").strip(), safe="")
        self.request("POST", f"/requests/{rid}/cancel", retries=1)

    def estimate(self, model_id: str, params: dict[str, Any]) -> dict[str, Any]:
        data = self.request("POST", f"/estimate/{model_id}", params, retries=1)
        data = data if isinstance(data, dict) else {}
        out: dict[str, Any] = {}
        for key in ("credits", "usd"):
            try:
                out[key] = round(float(data.get(key)), 3)
            except (TypeError, ValueError):
                pass
        return out

    def run(self, model_id: str, params: dict[str, Any], output_dir: str | Path, *, timeout: float = 1800) -> dict[str, Any]:
        """Submit, wait, download. Raises HiggsfieldError when the request fails."""
        submitted = self.submit(model_id, params)
        rid = str(submitted["request_id"])
        parsed = self.wait(rid, timeout=timeout)
        if parsed["failed"]:
            raise HiggsfieldError(parsed["failure_reason"] or "Higgsfield generation failed", detail=parsed)
        dest = Path(output_dir) / rid
        parsed["downloaded"] = download_results(parsed, dest)
        parsed["output_dir"] = str(dest)
        parsed["model"] = model_id
        return parsed

    # ---- files

    def upload(self, path: str | Path) -> str:
        p = Path(path).expanduser()
        if not p.is_file():
            raise HiggsfieldError(f"File not found: {p}")
        ext = ".jpg" if p.suffix.lower() == ".jpeg" else p.suffix.lower()
        content_type = UPLOAD_TYPES.get(ext)
        if not content_type:
            raise HiggsfieldError(f"Higgsfield uploads take JPG, PNG, WebP, GIF, WAV or MP4, not {p.suffix or 'this file'} ({p.name}).")
        ticket = self.request("POST", "/files/generate-upload-url", {"content_type": content_type})
        if not isinstance(ticket, dict) or not ticket.get("upload_url") or not ticket.get("public_url"):
            raise HiggsfieldError(f"Higgsfield sent no upload link: {ticket}")
        headers = {str(k): str(v) for k, v in (ticket.get("upload_headers") or {"Content-Type": content_type}).items()}
        headers["User-Agent"] = USER_AGENT  # never the API key: this goes to storage
        req = urllib.request.Request(ticket["upload_url"], data=p.read_bytes(), headers=headers, method="PUT")
        try:
            with _urlopen(req, 600) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            raise HiggsfieldError(f"Upload of {p.name} failed (HTTP {exc.code}).") from exc
        except urllib.error.URLError as exc:
            raise HiggsfieldError(f"Upload of {p.name} failed: {exc.reason}") from exc
        return str(ticket["public_url"])

    def resolve(self, value: str, what: str = "file") -> str:
        """A path, data: URI or link → a public link Higgsfield can read."""
        s = str(value or "").strip().strip('"')
        if not s:
            raise HiggsfieldError(f"{what} is empty")
        if s.startswith("data:"):
            return self.upload(data_uri_to_file(s))
        if is_url(s):
            return s
        if Path(s).expanduser().is_file():
            return self.upload(s)
        raise HiggsfieldError(f"{what}: file not found: {s}")

    def resolve_params(self, model: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Upload every local file the parameters point at (link fields only)."""
        out = dict(params)
        for field in media_fields(model):
            value = out.get(field)
            if isinstance(value, str) and value.strip():
                out[field] = self.resolve(value, field)
            elif isinstance(value, list):
                out[field] = [self.resolve(v, field) if isinstance(v, str) else v for v in value]
        return out

    # ---- lookups

    def presets(self, which: str, search: str = "", size: int = 50) -> Any:
        if which == "restyle":
            return self.request("GET", "/models/higgsfield/genjutsu/restyle/v1.0/presets")
        q = {"size": max(1, min(int(size or 50), 100)), "cursor": 0}
        if search.strip():
            q["search"] = search.strip()[:100]
        return self.request("GET", f"/marketing-studio/image/presets?{urllib.parse.urlencode(q)}")

    def soul_styles(self, version: str = "v2") -> Any:
        return self.request("GET", "/v1/text2image/soul-styles" + ("/v2" if version == "v2" else ""))

    def create_character(self, name: str, image_urls: list[str], model_version: str = "v2") -> dict[str, Any]:
        body = {"name": name.strip()[:100], "model_version": model_version,
                "input_images": [{"type": "image_url", "image_url": u} for u in image_urls[:100]]}
        data = self.request("POST", "/v1/custom-references", body, idempotency_key=str(uuid.uuid4()))
        return data if isinstance(data, dict) else {}

    def character(self, ref_id: str) -> dict[str, Any]:
        data = self.request("GET", f"/v1/custom-references/{urllib.parse.quote(str(ref_id).strip(), safe='')}")
        return data if isinstance(data, dict) else {}


def _fetch(url: str, timeout: float = 600) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")  # CDN: never the key
    delay = 1.0
    for attempt in range(4):
        try:
            with _urlopen(req, timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if attempt < 3 and exc.code >= 500:
                time.sleep(delay)
                delay *= 2
                continue
            raise HiggsfieldError(f"Download failed (HTTP {exc.code}); results stay for at least 7 days.") from exc
        except urllib.error.URLError as exc:
            if attempt < 3:
                time.sleep(delay)
                delay *= 2
                continue
            raise HiggsfieldError(f"Download failed: {exc.reason}") from exc
    raise HiggsfieldError("Download failed")


def _stem(key: str) -> str:
    parts = key.split(".")
    base = re.sub(r"_url$", "", parts[0]) or "file"
    base = {"images": "image", "audios": "audio", "videos": "video"}.get(base, base)
    if len(parts) > 1 and parts[1].isdigit():
        return f"{base}_{int(parts[1]) + 1}"
    return re.sub(r"[^A-Za-z0-9_-]+", "_", base)[:60] or "file"


def download_results(parsed: dict[str, Any], output_dir: str | Path) -> list[str]:
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    seen: set[str] = set()
    for item in parsed.get("results") or []:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        data = _fetch(url)
        ext = url_ext(url) or sniff_ext(data[:64]) or ".bin"
        ext = ".jpg" if ext == ".jpeg" else ext
        stem = _stem(item["key"])
        dest = folder / f"{stem}{ext}"
        n = 1
        while str(dest) in paths:
            dest = folder / f"{stem}_{n}{ext}"
            n += 1
        dest.write_bytes(data)
        if ext == ".zip":
            unpacked = safe_extract(dest, folder / stem)
            if unpacked:
                dest.unlink(missing_ok=True)
                paths.extend(unpacked)
                continue
        paths.append(str(dest))
    return paths


# --------------------------------------------------------------------------- spend


def placeholder_params(model: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """The same request with local files swapped for stand-in links, so a free estimate needs no upload."""
    out = dict(params)
    for field in media_fields(model):
        value = out.get(field)
        stand_in = "https://example.com/input.mp4" if "video" in field else "https://example.com/input.wav" if "audio" in field else "https://example.com/input.png"
        if isinstance(value, str) and value and not is_url(value):
            out[field] = stand_in
        elif isinstance(value, list):
            out[field] = [v if is_url(str(v)) else stand_in for v in value]
    return out


def cost_text(estimate: dict[str, Any] | None) -> str:
    if not estimate or "credits" not in estimate:
        return "Higgsfield credits (no estimate for these settings)"
    return f"~{estimate['credits']:g} credits" + (f" (${estimate['usd']:.3f})" if "usd" in estimate else "")


def credit_gate(confirm_spend: bool, estimate: dict[str, Any] | None, label: str) -> str | None:
    if confirm_spend:
        return None
    return (
        f"Error: CREDIT GATE — Higgsfield {label} costs {cost_text(estimate)}. "
        "1) Call ducky_ask_user with a yes/no spend question that names the job, the model and that cost — "
        "never ask only in chat text. "
        "2) Only if they approve: call again with confirm_spend=true. Do not invent approval."
    )


def test_api_key(api_key: str = "") -> dict[str, Any]:
    """Settings → Test: a free lookup that tells a good key (404 for a made-up request) from a bad one (401)."""
    raw = (api_key or "").strip()
    if not raw:
        return {"ok": False, "detail": "Paste KEY_ID:KEY_SECRET first"}
    try:
        client = HiggsfieldClient(credentials=raw)
        detail = client.check()
        try:
            est = client.estimate(DEFAULT_MODELS["text-to-image"], {"prompt": "test"})
            detail += f" — a Soul 2 picture costs {cost_text(est)}"
        except HiggsfieldError:
            pass
        return {"ok": True, "detail": detail}
    except HiggsfieldError as exc:
        return {"ok": False, "detail": str(exc)}


test_api_key.__test__ = False  # Settings helper; pytest must not collect this
