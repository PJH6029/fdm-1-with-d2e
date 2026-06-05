from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import ModuleType

import pytest

from fdm_1_with_d2e.data import decode_d2e_json_mcap_records, ns_from_ms
from fdm_1_with_d2e.evaluation import (
    OFFICIAL_ROUNDTRIP_GENERATED_BY,
    OFFICIAL_ROUNDTRIP_MODULES,
    OFFICIAL_ROUNDTRIP_PROVENANCE_SCHEMA,
    OfficialRoundTripDependencies,
    OptionalOfficialMcapDependencyError,
    generate_writer_roundtrip_prediction_mcap,
    require_official_roundtrip_dependencies,
)


@dataclass(frozen=True, slots=True)
class _FakeMcapMessage:
    topic: str
    timestamp: int
    decoded: object


@dataclass(slots=True)
class _FakeMediaRef:
    pts_ns: int
    uri: str = "source.mkv"


@dataclass(slots=True)
class _FakeScreen:
    media_ref: _FakeMediaRef
    utc_ns: int | None = None
    resolved_against: str | None = None

    def resolve_relative_path(self, mcap_path: str) -> "_FakeScreen":
        self.resolved_against = mcap_path
        return self


@dataclass(frozen=True, slots=True)
class _FakeKeyboardDecoded:
    event_type: str
    vk: int


@dataclass(frozen=True, slots=True)
class _FakeRawMouseDecoded:
    last_x: int
    last_y: int
    button_flags: int = 0
    button_data: int = 0
    us_flags: int = 0
    device_handle: int | None = None


class _FakeKeyboardEvent:
    def __init__(self, *, event_type: str, vk: int, timestamp: int) -> None:
        self.event_type = event_type
        self.vk = vk
        self.timestamp = timestamp


class _FakeRawMouseEvent:
    class UsFlags:
        MOUSE_MOVE_RELATIVE = 0

    class ButtonFlags:
        RI_MOUSE_NOP = 0
        RI_MOUSE_LEFT_BUTTON_DOWN = 1
        RI_MOUSE_LEFT_BUTTON_UP = 2
        RI_MOUSE_RIGHT_BUTTON_DOWN = 4
        RI_MOUSE_RIGHT_BUTTON_UP = 8
        RI_MOUSE_MIDDLE_BUTTON_DOWN = 16
        RI_MOUSE_MIDDLE_BUTTON_UP = 32

    def __init__(
        self,
        *,
        last_x: int,
        last_y: int,
        us_flags: int | None,
        button_flags: int | None,
        button_data: int,
        device_handle: int | None,
        timestamp: int,
    ) -> None:
        self.last_x = last_x
        self.last_y = last_y
        self.us_flags = us_flags
        self.button_flags = button_flags
        self.button_data = button_data
        self.device_handle = device_handle
        self.timestamp = timestamp


class _FakeReader:
    messages: tuple[_FakeMcapMessage, ...] = ()

    def __init__(self, mcap_path: str | Path) -> None:
        self.mcap_path = Path(mcap_path)

    def __enter__(self) -> "_FakeReader":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def iter_messages(self, topics: list[str] | tuple[str, ...] | None = None):
        topic_filter = set(topics or ())
        for message in self.messages:
            if not topic_filter or message.topic in topic_filter:
                yield message


class _FakeWriter:
    instances: list["_FakeWriter"] = []

    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.metadata: list[dict[str, object]] = []
        self.messages: list[dict[str, object]] = []
        self.instances.append(self)

    def __enter__(self) -> "_FakeWriter":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if exc_type is None:
            payload = {"metadata": self.metadata, "messages": self.messages}
            self.output_path.write_text(json.dumps(payload, sort_keys=True, default=str), encoding="utf-8")

    def write_metadata(self, name: str, data: dict[str, str]) -> None:
        self.metadata.append({"name": name, "data": data})

    def write_message(self, message: object, *, topic: str, timestamp: int) -> None:
        self.messages.append(
            {
                "topic": topic,
                "timestamp": timestamp,
                "message_class": type(message).__name__,
                "payload": _public_payload(message),
            }
        )


def _public_payload(message: object) -> dict[str, object]:
    payload = dict(getattr(message, "__dict__", {}))
    for slot in getattr(message, "__slots__", ()):
        if not slot.startswith("_") and hasattr(message, slot):
            payload[slot] = getattr(message, slot)
    return payload


def _record(topic: str, timestamp_ms: int, payload: dict[str, object]) -> dict[str, object]:
    return {
        "topic": topic,
        "log_time_ns": ns_from_ms(timestamp_ms),
        "data": json.dumps(payload).encode("utf-8"),
    }


def test_missing_official_roundtrip_dependencies_raise_clear_error() -> None:
    def missing_importer(_module_name: str) -> ModuleType:
        raise ImportError("not installed")

    with pytest.raises(OptionalOfficialMcapDependencyError) as excinfo:
        require_official_roundtrip_dependencies(importer=missing_importer)

    assert excinfo.value.missing_modules == OFFICIAL_ROUNDTRIP_MODULES
    assert "mcap-owa-support" in str(excinfo.value)
    assert "Offline tests do not require" in str(excinfo.value)


def test_writer_roundtrip_generates_prediction_mcap_and_provenance_with_fake_owa(tmp_path: Path) -> None:
    source = tmp_path / "source.mcap"
    source.write_bytes(b"source-ground-truth-mcap")
    prediction = tmp_path / "prediction.mcap"
    provenance_path = tmp_path / "prediction.mcap.provenance.json"
    _FakeWriter.instances.clear()
    _FakeReader.messages = (
        _FakeMcapMessage("screen", 1_000, _FakeScreen(media_ref=_FakeMediaRef(pts_ns=0))),
        _FakeMcapMessage("keyboard", 2_000, _FakeKeyboardDecoded(event_type="press", vk=65)),
        _FakeMcapMessage("mouse/raw", 3_000, _FakeRawMouseDecoded(last_x=4, last_y=-2)),
        _FakeMcapMessage("keyboard", 4_000, _FakeKeyboardDecoded(event_type="release", vk=65)),
        _FakeMcapMessage("mouse/raw", 5_000, _FakeRawMouseDecoded(last_x=0, last_y=0, button_flags=1)),
    )
    deps = OfficialRoundTripDependencies(
        OWAMcapReader=_FakeReader,
        OWAMcapWriter=_FakeWriter,
        KeyboardEvent=_FakeKeyboardEvent,
        RawMouseEvent=_FakeRawMouseEvent,
    )

    provenance = generate_writer_roundtrip_prediction_mcap(
        source,
        prediction,
        provenance_json_path=provenance_path,
        dataset_root=tmp_path / "dataset",
        dependencies=deps,
    )

    source_hash = hashlib.sha256(b"source-ground-truth-mcap").hexdigest()
    assert prediction.is_file()
    assert provenance_path.is_file()
    assert provenance["schema"] == OFFICIAL_ROUNDTRIP_PROVENANCE_SCHEMA
    assert provenance["action_mode"] == "exact"
    assert provenance["generated_by"] == OFFICIAL_ROUNDTRIP_GENERATED_BY
    assert provenance["source"]["sha256"] == source_hash
    assert provenance["prediction"]["sha256"] != source_hash
    assert provenance["not_copied_proof"]["source_sha256_equals_prediction_sha256"] is False
    assert provenance["topics_written"] == {"keyboard": 2, "mouse/raw": 2, "screen": 1}
    assert provenance["tokenized_bin_count"] is None
    assert provenance["tokenized_overflow_bin_count"] is None
    assert provenance["decoded_counts"] is None
    assert provenance["skipped_scroll_count"] == 0
    assert provenance["first_screen"] == {"mcap_timestamp_ns": 1_000, "pts_ns": 0}
    assert json.loads(provenance_path.read_text(encoding="utf-8"))["prediction"]["size_bytes"] == prediction.stat().st_size

    writer_payload = json.loads(prediction.read_text(encoding="utf-8"))
    assert writer_payload["metadata"][0]["name"] == "fdm_1_with_d2e.roundtrip_provenance"
    assert [message["topic"] for message in writer_payload["messages"]] == [
        "screen",
        "keyboard",
        "mouse/raw",
        "keyboard",
        "mouse/raw",
    ]
    assert writer_payload["messages"][1]["message_class"] == "_FakeKeyboardEvent"
    assert writer_payload["messages"][2]["message_class"] == "_FakeRawMouseEvent"


def test_tokenized_mode_uses_repo_decoder_tokenizer_and_writes_official_action_messages(tmp_path: Path) -> None:
    source = tmp_path / "source.mcap"
    source.write_bytes(b"source-real-d2e-json-mcap")
    prediction = tmp_path / "prediction-tokenized.mcap"
    _FakeWriter.instances.clear()
    _FakeReader.messages = (
        _FakeMcapMessage("screen", ns_from_ms(0), _FakeScreen(media_ref=_FakeMediaRef(pts_ns=0))),
        _FakeMcapMessage("screen", ns_from_ms(100), _FakeScreen(media_ref=_FakeMediaRef(pts_ns=ns_from_ms(100)))),
    )
    records = [
        _record("screen", 0, {"media_ref": {"pts_ns": 0}, "shape": [480, 854, 3]}),
        _record("keyboard", 10, {"event_type": "press", "vk": 65}),
        _record("mouse/raw", 20, {"last_x": 4, "last_y": -2}),
        _record("mouse", 30, {"event_type": "click", "button": "left", "pressed": True}),
        _record("mouse", 40, {"event_type": "scroll", "dx": 0, "dy": 1}),
        _record("keyboard", 60, {"event_type": "release", "vk": 65}),
        _record("mouse", 70, {"event_type": "click", "button": "left", "pressed": False}),
        _record("screen", 100, {"media_ref": {"pts_ns": ns_from_ms(100)}, "shape": [480, 854, 3]}),
    ]

    def action_reader(_source_path: str | Path):
        return decode_d2e_json_mcap_records(records)

    deps = OfficialRoundTripDependencies(
        OWAMcapReader=_FakeReader,
        OWAMcapWriter=_FakeWriter,
        KeyboardEvent=_FakeKeyboardEvent,
        RawMouseEvent=_FakeRawMouseEvent,
    )

    provenance = generate_writer_roundtrip_prediction_mcap(
        source,
        prediction,
        action_mode="tokenized",
        dependencies=deps,
        action_reader=action_reader,
    )

    assert provenance["action_mode"] == "tokenized"
    assert provenance["topics_written"] == {"keyboard": 2, "mouse/raw": 3, "screen": 2}
    assert provenance["events_written"] == {
        "keyboard_tokenized": 2,
        "mouse_button_tokenized": 2,
        "mouse_move_tokenized": 1,
        "screen_exact_reemit": 2,
    }
    assert provenance["tokenized_bin_count"] == 3
    assert provenance["tokenized_overflow_bin_count"] == 0
    assert provenance["tokenized_overflow_bin_fraction"] == 0.0
    assert provenance["decoded_counts"] == {
        "keyboard": 2,
        "mouse_button": 2,
        "mouse_move": 1,
        "screen": 2,
        "scroll": 1,
    }
    assert provenance["skipped_scroll_count"] == 1
    assert provenance["not_copied_proof"]["source_sha256_equals_prediction_sha256"] is False

    writer_payload = json.loads(prediction.read_text(encoding="utf-8"))
    assert [message["topic"] for message in writer_payload["messages"]] == [
        "screen",
        "mouse/raw",
        "keyboard",
        "mouse/raw",
        "keyboard",
        "mouse/raw",
        "screen",
    ]
    keyboard_payloads = [
        message["payload"] for message in writer_payload["messages"] if message["message_class"] == "_FakeKeyboardEvent"
    ]
    assert keyboard_payloads == [
        {"event_type": "press", "timestamp": ns_from_ms(10), "vk": 65},
        {"event_type": "release", "timestamp": ns_from_ms(60), "vk": 65},
    ]
    mouse_payloads = [
        message["payload"] for message in writer_payload["messages"] if message["message_class"] == "_FakeRawMouseEvent"
    ]
    assert [payload["button_flags"] for payload in mouse_payloads] == [0, 1, 2]
    assert (mouse_payloads[0]["last_x"], mouse_payloads[0]["last_y"]) != (0, 0)
    assert [(payload["last_x"], payload["last_y"]) for payload in mouse_payloads[1:]] == [(0, 0), (0, 0)]


def test_writer_roundtrip_requires_official_evaluate_topics(tmp_path: Path) -> None:
    source = tmp_path / "source.mcap"
    source.write_bytes(b"source")
    prediction = tmp_path / "prediction.mcap"
    _FakeReader.messages = (_FakeMcapMessage("screen", 1_000, _FakeScreen(media_ref=_FakeMediaRef(pts_ns=0))),)
    deps = OfficialRoundTripDependencies(
        OWAMcapReader=_FakeReader,
        OWAMcapWriter=_FakeWriter,
        KeyboardEvent=_FakeKeyboardEvent,
        RawMouseEvent=_FakeRawMouseEvent,
    )

    with pytest.raises(ValueError, match="required official evaluate.py topics"):
        generate_writer_roundtrip_prediction_mcap(source, prediction, dependencies=deps)

    assert not prediction.exists()
    assert not (tmp_path / ".prediction.mcap.tmp").exists()
