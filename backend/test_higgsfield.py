"""Self-check for the Higgsfield plugin: a fake Higgsfield API, no network, no credits."""

from __future__ import annotations

import inspect
import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

try:
    from . import higgsfield as h, nodes, register, tools
except ImportError:  # run as a plain file
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend import higgsfield as h, nodes, register, tools

ROOT = Path(__file__).resolve().parents[1]
KEY = "kid_123:secret_456"
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\0" * 32
MP4 = b"\0\0\0\x18ftypmp42" + b"\0" * 32


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeHiggsfield:
    """Routes urllib requests like api.higgsfield.ai, its upload storage and its CDN would."""

    def __init__(self) -> None:
        self.submitted: list[tuple[str, dict[str, Any], str]] = []
        self.requests: dict[str, dict[str, Any]] = {}
        self.uploads: list[dict[str, str]] = []
        self.cdn_headers: list[dict[str, str]] = []
        self.fail_next: list[tuple[int, Any]] = []
        self.estimates = 0

    def _json(self, data: Any) -> _Resp:
        return _Resp(json.dumps(data).encode())

    def __call__(self, req, timeout):  # noqa: ANN001 — urllib.request.Request
        url = req.full_url
        if url.startswith("https://storage.example/"):
            assert "Authorization" not in dict(req.header_items())  # the key never goes to storage
            self.uploads.append(dict(req.header_items()))
            return _Resp(b"")
        if url.startswith("https://cdn.example/"):
            self.cdn_headers.append(dict(req.header_items()))
            return _Resp(MP4 if url.endswith(".mp4") else JPG)
        assert req.get_header("Authorization") == f"Key {KEY}"
        if self.fail_next:
            code, body = self.fail_next.pop(0)
            raise urllib.error.HTTPError(url, code, "fail", {}, io.BytesIO(json.dumps(body).encode()))
        path = url.removeprefix(h.BASE_URL)
        body = json.loads(req.data.decode()) if req.data else None
        if path == "/files/generate-upload-url":
            n = len(self.uploads) + 1
            ext = {"image/png": "png", "image/jpeg": "jpg", "video/mp4": "mp4"}.get(body["content_type"], "bin")
            return self._json({"public_url": f"https://cdn.example/in/{n}.{ext}", "upload_url": f"https://storage.example/put/{n}",
                               "content_type": body["content_type"], "upload_headers": {"Content-Type": body["content_type"]}})
        if path.startswith("/estimate/"):
            self.estimates += 1
            return self._json({"credits": "1.500", "usd": "0.094"})
        if path.startswith("/requests/"):
            rid = path.split("/")[2]
            if rid not in self.requests:
                raise urllib.error.HTTPError(url, 404, "nf", {}, io.BytesIO(b'{"detail": "Request not found"}'))
            if path.endswith("/cancel"):
                return _Resp(b"")
            return self._json(self.requests[rid])
        if "presets" in path or "soul-styles" in path:
            return self._json({"items": [{"id": "c2143317-f28d-4c3c-a0b8-39bd547e08a7", "name": "Anime"}]})
        if path == "/v1/custom-references":
            return self._json({"id": "ref1", "status": "queued", "name": body["name"]})
        if path == "/v1/custom-references/ref1":
            return self._json({"id": "ref1", "status": "completed"})
        model_id = path.lstrip("/")
        assert model_id in h.catalog(), model_id
        key = req.get_header("Idempotency-key")
        assert key, "every generation carries an Idempotency-Key"
        existing = next((rid for m, b, k in self.submitted for rid in [k] if k == key), None)
        if existing:  # a retry with the same key returns the same request
            return self._json({"status": "queued", "request_id": self.requests_by_key[key]})
        rid = f"req{len(self.submitted) + 1}"
        self.submitted.append((model_id, body, key))
        self.requests_by_key = {**getattr(self, "requests_by_key", {}), key: rid}
        if h.catalog()[model_id]["kind"] == "image":
            out: dict[str, Any] = {"images": [{"url": f"https://cdn.example/out/{rid}-1.jpg"}, {"url": f"https://cdn.example/out/{rid}-2.jpg"}]}
        else:
            out = {"video": {"url": f"https://cdn.example/out/{rid}.mp4"}}
        self.requests[rid] = {"status": "completed", "request_id": rid, **out}
        return self._json({"status": "queued", "request_id": rid, "status_url": f"{h.BASE_URL}/requests/{rid}/status",
                           "cancel_url": f"{h.BASE_URL}/requests/{rid}/cancel"})


@pytest.fixture
def fake(monkeypatch, tmp_path):
    server = FakeHiggsfield()
    monkeypatch.setattr(h, "_urlopen", server)
    monkeypatch.setattr(h.time, "sleep", lambda _s: None)
    monkeypatch.setattr(nodes.time, "sleep", lambda _s: None)
    monkeypatch.setattr(tools.time, "sleep", lambda _s: None)
    monkeypatch.setattr(h, "plugin_prefs", lambda: {})
    monkeypatch.setattr(h, "_saved_credentials", lambda: KEY)
    monkeypatch.setitem(tools._DOWNLOADS, "root", tmp_path / "downloads")
    (tmp_path / "downloads").mkdir()
    return server


class FakeApi:
    def __init__(self, tmp: Path) -> None:
        self.tools: dict[str, Any] = {}
        self.nodes: dict[str, Any] = {}
        self.tmp = tmp

    def tool(self, name: str, intent: str = ""):
        def deco(fn):
            self.tools[name] = fn
            return fn
        return deco

    def register_secret_test(self, key, fn):
        self.secret_test = (key, fn)

    def register_automation_node(self, node_type, handler):
        self.nodes[node_type] = handler

    def local_dir(self, name=""):
        return str(self.tmp / name)

    def media_url(self, path):
        return ""

    def listener(self, command, params):
        return {"ok": True, "command": command, "params": params}

    def log(self, message):
        pass


@pytest.fixture
def api(fake, tmp_path):
    fapi = FakeApi(tmp_path)
    register(fapi)
    return fapi


def _ctx(inputs: dict[str, Any], **config: Any) -> dict[str, Any]:
    return {"config": config, "inputs": inputs, "payload": {}, "artifact_dir": ""}


# --------------------------------------------------------------------------- catalog and building


def test_credentials() -> None:
    assert h.split_credentials("abc:def") == ("abc", "def")
    assert h.split_credentials("Key abc:def:ghi") == ("abc", "def:ghi")
    assert h.split_credentials("abc\ndef") == ("abc", "def")
    with pytest.raises(h.HiggsfieldError, match="KEY_ID:KEY_SECRET"):
        h.split_credentials("onlyonepart")
    assert h.auth_header("a:b")["Authorization"] == "Key a:b"
    assert h.test_api_key("")["ok"] is False


def test_catalog_and_lookup() -> None:
    cat = h.catalog()
    assert len(cat) == 83
    assert all(mid in cat for mid in h.DEFAULT_MODELS.values())
    assert h.find_model("seedance 2.5 text")["id"] == "bytedance/seedance-2.5/text-to-video"
    assert h.find_model("", "image-to-video")["id"] == h.DEFAULT_MODELS["image-to-video"]
    with pytest.raises(ValueError, match="No single"):
        h.find_model("kling")
    assert h.takes_image(cat["xai/grok-imagine-image-2.0"]) and not h.takes_image(cat["z-image/turbo"])
    assert {r["workflow"] for r in h.models_list(kind="video")} >= {"text-to-video", "image-to-video", "motion"}


def test_build_and_validate() -> None:
    kling = h.catalog()["kling-video/v3.0/pro/image-to-video"]
    p = h.build_params(kling, prompt="go", image="a.png", end_image="b.png", duration=20)
    assert p == {"prompt": "go", "image_url": "a.png", "last_image_url": "b.png", "duration": 15}  # clamped to the max
    turbo = h.catalog()["kling-video/v2.5-turbo/pro/text-to-video"]
    assert h.build_params(turbo, prompt="x", duration=7)["duration"] == 5  # nearest allowed length
    swap = h.catalog()["higgsfield/genjutsu/motion-transfer/v1.0"]
    assert h.build_params(swap, video="m.mp4", image="c.png") == {"video_url": "m.mp4", "image_urls": ["c.png"]}
    soul = h.catalog()["higgsfield-ai/soul/v2/standard"]
    assert h.build_params(soul, prompt="x", aspect_ratio="16:9", resolution="1080P")["resolution"] == "1080p"
    with pytest.raises(ValueError, match="aspect ratio"):
        h.build_params(soul, prompt="x", aspect_ratio="7:1")
    with pytest.raises(ValueError, match="doesn't take a video"):
        h.build_params(soul, prompt="x", video="v.mp4")
    with pytest.raises(ValueError, match="has no bogus"):
        h.validate(soul, {"prompt": "x", "bogus": 1})
    with pytest.raises(ValueError, match="needs prompt"):
        h.validate(soul, {})
    with pytest.raises(ValueError, match="JSON object"):
        h.parse_extra("[1]")
    stand_in = h.placeholder_params(kling, {"prompt": "go", "image_url": "C:/x/a.png"})
    assert stand_in["image_url"].startswith("https://") and stand_in["prompt"] == "go"


def test_status_parsing_and_files(tmp_path) -> None:
    done = h.parse_status({"status": "completed", "request_id": "r", "images": [{"url": "https://c/a.jpg"}, {"url": "https://c/b.jpg"}],
                           "status_url": "https://api/x"})
    assert done["finished"] and [r["key"] for r in done["results"]] == ["images.0", "images.1"]
    video = h.parse_status({"status": "completed", "video": {"url": "https://c/v.mp4"}})
    assert video["video_url"] == "https://c/v.mp4"
    nsfw = h.parse_status({"status": "nsfw"})
    assert nsfw["failed"] and "content check" in nsfw["failure_reason"]
    assert h.parse_status({"status": "in_progress"})["failed"] is False
    assert h.sniff_ext(MP4) == ".mp4" and h.sniff_ext(JPG) == ".jpg" and h.sniff_ext(b"RIFF\0\0\0\0WAVE") == ".wav"
    assert h._stem("images.1") == "image_2" and h._stem("video") == "video"
    assert h.kind_of("x.mp4") == "video" and h.kind_of("x.wav") == "audio"


# --------------------------------------------------------------------------- client


def test_client_lifecycle(fake, tmp_path) -> None:
    c = h.HiggsfieldClient(credentials=KEY)
    assert c.check() == "Connected"  # a made-up request answers 404 with a good key
    assert c.estimate("z-image/turbo", {"prompt": "x"}) == {"credits": 1.5, "usd": 0.094}
    pic = tmp_path / "in.png"
    pic.write_bytes(PNG)
    url = c.upload(pic)
    assert url == "https://cdn.example/in/1.png" and fake.uploads[0]["Content-type"] == "image/png"
    with pytest.raises(h.HiggsfieldError, match="not .mov"):
        (tmp_path / "x.mov").write_bytes(b"x")
        c.upload(tmp_path / "x.mov")
    done = c.run("bytedance/seedance-2.5/text-to-video", {"prompt": "x"}, tmp_path / "out")
    assert [Path(p).name for p in done["downloaded"]] == ["video.mp4"]
    assert all("Authorization" not in hdr for hdr in fake.cdn_headers)
    c.cancel(done["request_id"])


def test_client_errors_and_retries(fake) -> None:
    c = h.HiggsfieldClient(credentials=KEY)
    fake.fail_next = [(500, {"detail": "boom"})]
    first = c.submit("z-image/turbo", {"prompt": "x"})  # retried with the same Idempotency-Key
    assert first["request_id"] == "req1" and len(fake.submitted) == 1
    fake.fail_next = [(400, {"detail": "Maximum number of concurrent requests (4) has been reached"})]
    assert c.submit("z-image/turbo", {"prompt": "y"})["request_id"] == "req2"  # waited for a free slot
    fake.fail_next = [(401, {"detail": "Invalid credentials"})]
    with pytest.raises(h.HiggsfieldError, match="rejected the key"):
        c.check()
    fake.fail_next = [(403, {"detail": "Not enough credits"})]
    with pytest.raises(h.HiggsfieldError, match="not enough credits"):
        c.submit("z-image/turbo", {"prompt": "z"})
    fake.fail_next = [(422, {"detail": [{"loc": ["body", "duration"], "msg": "bad value"}]})]
    with pytest.raises(h.HiggsfieldError, match="duration: bad value"):
        c.submit("z-image/turbo", {"prompt": "z"})
    with pytest.raises(h.HiggsfieldError, match="API key not set"):
        h.HiggsfieldClient(credentials="")


# --------------------------------------------------------------------------- tools


def test_tools_gate_then_run(api, fake, tmp_path) -> None:
    gate = api.tools["higgsfield_text_to_video"](prompt="a duck surfing")
    assert gate.startswith("Error: CREDIT GATE") and "~1.5 credits ($0.094)" in gate and not fake.submitted
    res = json.loads(api.tools["higgsfield_text_to_video"](prompt="a duck surfing", duration=7, confirm_spend=True))
    assert res["finished"] and res["downloaded"][0].endswith("video.mp4") and res["task_id"] == res["request_id"]
    model, body, _ = fake.submitted[-1]
    assert model == h.DEFAULT_MODELS["text-to-video"] and body == {"prompt": "a duck surfing", "duration": 7}  # Seedance 2.5 takes 4-30 s
    pic = tmp_path / "shot.png"
    pic.write_bytes(PNG)
    json.loads(api.tools["higgsfield_image_to_video"](image=str(pic), prompt="push in", model="kling 3 pro image", confirm_spend=True))
    model, body, _ = fake.submitted[-1]
    assert model == "kling-video/v3.0/pro/image-to-video" and body["image_url"].startswith("https://cdn.example/in/")
    pics = json.loads(api.tools["higgsfield_text_to_image"](prompt="key art", aspect_ratio="16:9", confirm_spend=True))
    assert [Path(p).name for p in pics["downloaded"]] == ["image_1.jpg", "image_2.jpg"]
    assert "can't edit pictures" in api.tools["higgsfield_edit_image"](image=str(pic), model="z-image/turbo", confirm_spend=True)
    json.loads(api.tools["higgsfield_restyle_video"](video="https://x.example/in.mp4", preset_id="c2143317-f28d-4c3c-a0b8-39bd547e08a7", confirm_spend=True))
    assert fake.submitted[-1][1]["preset_id"].startswith("c2143317")
    anyrun = json.loads(api.tools["higgsfield_generate"](model="wan/v2.7/text-to-video", params='{"prompt": "rain"}', confirm_spend=True))
    assert anyrun["finished"] and fake.submitted[-1][0] == "wan/v2.7/text-to-video"
    assert "has no nope" in api.tools["higgsfield_generate"](model="z-image/turbo", params='{"nope": 1}', prompt="x", confirm_spend=True)
    nowait = json.loads(api.tools["higgsfield_text_to_image"](prompt="x", confirm_spend=True, wait=False))
    assert nowait["status"] == "queued" and "next" in nowait
    status = json.loads(api.tools["higgsfield_status"](request_id=nowait["request_id"]))
    assert status["finished"] is True
    assert json.loads(api.tools["higgsfield_estimate"](model="z-image/turbo", params='{"prompt": "x"}'))["credits"] == 1.5
    assert json.loads(api.tools["higgsfield_presets"]())["presets"]["items"][0]["name"] == "Anime"
    char_gate = api.tools["higgsfield_create_character"](name="Duck", images=str(pic))
    assert "CREDIT GATE" in char_gate
    char = json.loads(api.tools["higgsfield_create_character"](name="Duck", images=str(pic), confirm_spend=True))
    assert char["status"] == "completed" and char["use_as"]["custom_reference_id"] == "ref1"
    landed = json.loads(api.tools["higgsfield_import_to_uefn"](path=res["downloaded"][0]))
    assert landed["destination_path"] == "Higgsfield"


# --------------------------------------------------------------------------- nodes


def test_nodes_gate_and_chain(api, fake) -> None:
    gated = nodes.text_to_image(_ctx({"prompt": "key art"}))
    assert gated["ok"] is False and "~1.5 credits" in gated["error"] and "Spend credits" in gated["error"] and not fake.submitted
    pic = nodes.text_to_image(_ctx({"prompt": "key art"}, spend=True, aspect_ratio="16:9"))
    assert pic["ok"] and pic["image"]["kind"] == "image" and len(pic["images"]) == 2
    assert pic["image"]["remote"].startswith("https://cdn.example/out/") and pic["image"]["plugin_id"] == "higgsfield"
    uploads_before = len(fake.uploads)
    vid = nodes.image_to_video(_ctx({"image": pic["image"], "prompt": "camera push", "duration": 5}, spend=True))
    assert vid["ok"] and vid["video"]["kind"] == "video" and vid["video"]["path"].endswith(".mp4")
    assert fake.submitted[-1][1]["image_url"] == pic["image"]["remote"] and len(fake.uploads) == uploads_before  # no re-upload
    moved = nodes.motion_transfer(_ctx({"video": vid["video"], "image": pic["image"]}, spend=True))
    assert moved["ok"] and fake.submitted[-1][1] == {"video_url": vid["video"]["remote"], "image_urls": [pic["image"]["remote"]]}
    assert nodes.restyle_video(_ctx({"video": vid["video"]}, spend=True))["error"].startswith("Set a Style preset")
    assert "Set the Model" in nodes.generate_any(_ctx({}, spend=True))["error"]
    anyrun = nodes.generate_any(_ctx({"prompt": "rain"}, spend=True, model="z-image/turbo", params='{"seed": 3}'))
    assert anyrun["ok"] and fake.submitted[-1][1] == {"prompt": "rain", "seed": 3}
    assert nodes.estimate(_ctx({"prompt": "x"}))["credits"] == 1.5
    edit = nodes.edit_image(_ctx({"image": pic["image"], "prompt": "sunset"}, spend=True))
    assert edit["ok"] and fake.submitted[-1][0] == h.DEFAULT_MODELS["image-edit"]
    missing = nodes.image_to_video(_ctx({"image": {"kind": "image", "path": "C:/nowhere/gone.png"}}, spend=True))
    assert missing["ok"] is False and "isn't on this PC" in missing["error"]
    char = nodes.create_character(_ctx({"images": [pic["image"]], "name": "Duck"}, spend=True))
    assert char["ok"] and char["reference_id"] == "ref1"


# --------------------------------------------------------------------------- manifest


def test_manifest_matches_code(api) -> None:
    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    contrib = manifest["contributes"]
    declared = {row["id"] for row in contrib["automations"]["nodes"]}
    assert declared == set(nodes.HANDLERS) == set(api.nodes)
    cat = h.catalog()
    for row in contrib["automations"]["nodes"]:
        for f in row["config_fields"]:
            if f["id"] == "model" and f["type"] == "select":
                assert f["options"] and all(o["id"] in cat for o in f["options"]), row["id"]
    for row in contrib["automations"]["image_generators"]:
        assert row["tool"] in api.tools and row["args"]["model"] in cat
    for row in contrib["automations"]["media_backends"]:
        params = set(inspect.signature(api.tools[row["tool"]]).parameters)
        assert row["args"]["model"] in cat and row["node"] == "image.edit"
        for arg in [*row["pins"].values(), *row["args"]]:
            assert arg in params, (row["id"], arg)
    for name in contrib["agent.tools"]["plan_tools"]:
        assert name in api.tools
    builtin = {"input.text", "input.image", "input.video", "util.preview"}
    for tmpl in contrib["automations"]["templates"]:
        ids = {n["id"] for n in tmpl["graph"]["nodes"]}
        assert all(n["type"] in builtin or n["type"] in declared for n in tmpl["graph"]["nodes"])
        targets = {e["target"] for e in tmpl["graph"]["edges"]} | {e["source"] for e in tmpl["graph"]["edges"]}
        assert targets == ids, tmpl["id"]  # every node is wired: no leftovers
    assert api.secret_test[0] == manifest["secret_keys"][0] == h.SECRET_KEY
    for path in (ROOT / "skills" / "higgsfield-api").rglob("*.md"):
        assert path.read_text(encoding="utf-8").startswith("---\n"), path
