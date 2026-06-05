"""D2E recording discovery and optional OWAMcap/MCAP reader adapter."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from importlib import import_module
from pathlib import Path
from types import ModuleType

from fdm_1_with_d2e.data.types import D2ERecording, OWAMcapMessage

_SOURCE_METADATA_DIR = ".source-metadata"
_DEFAULT_LABELED_DIR = "labeled"
_REQUIRED_OWAMCAP_MODULES = ("mcap.reader",)


class OptionalOWAMcapDependencyError(ImportError):
    """Raised when optional MCAP/OWAMcap dependencies are unavailable."""

    def __init__(self, missing_modules: Iterable[str]) -> None:
        missing = tuple(missing_modules)
        hint = ", ".join(missing)
        super().__init__(
            "OWAMcap reading requires optional MCAP dependencies that are not installed: "
            f"{hint}. Install the D2E/OWAMcap reader extras in the execution environment "
            "before reading real .mcap files. Offline fixture tests do not require them."
        )
        self.missing_modules = missing


def discover_labeled_recordings(
    dataset_root: str | Path,
    *,
    labeled_dir: str = _DEFAULT_LABELED_DIR,
    video_suffix: str = ".mkv",
    mcap_suffix: str = ".mcap",
) -> tuple[D2ERecording, ...]:
    """Discover deterministic labeled ``.mkv`` + ``.mcap`` recording pairs.

    The function only inspects path names and pair existence; it does not open
    or parse video/MCAP file contents. Directories named ``.source-metadata`` are
    ignored because they are provenance metadata, not model input.
    """

    root = Path(dataset_root)
    labeled_root = root / labeled_dir
    if not labeled_root.exists():
        return ()

    recordings: list[D2ERecording] = []
    for video_path in sorted(labeled_root.rglob(f"*{video_suffix}"), key=_path_sort_key):
        if _is_under_source_metadata(video_path, labeled_root):
            continue
        mcap_path = video_path.with_suffix(mcap_suffix)
        if not mcap_path.is_file():
            continue
        relative = video_path.relative_to(labeled_root)
        game = relative.parent.as_posix() if relative.parent != Path(".") else ""
        recordings.append(
            D2ERecording(
                game=game,
                stem=video_path.stem,
                video_path=video_path,
                mcap_path=mcap_path,
                dataset_root=root,
                split=labeled_dir,
            )
        )

    return tuple(sorted(recordings, key=lambda item: (item.game, item.stem, item.relative_video_path.as_posix())))


def find_unpaired_labeled_files(
    dataset_root: str | Path,
    *,
    labeled_dir: str = _DEFAULT_LABELED_DIR,
    video_suffix: str = ".mkv",
    mcap_suffix: str = ".mcap",
) -> tuple[Path, ...]:
    """Return labeled videos or MCAP files missing their same-stem pair."""

    root = Path(dataset_root)
    labeled_root = root / labeled_dir
    if not labeled_root.exists():
        return ()

    unpaired: list[Path] = []
    for path in sorted(
        [*labeled_root.rglob(f"*{video_suffix}"), *labeled_root.rglob(f"*{mcap_suffix}")],
        key=_path_sort_key,
    ):
        if _is_under_source_metadata(path, labeled_root):
            continue
        counterpart_suffix = mcap_suffix if path.suffix == video_suffix else video_suffix
        if not path.with_suffix(counterpart_suffix).is_file():
            unpaired.append(path)
    return tuple(unpaired)


def require_owamcap_dependencies(
    module_names: Iterable[str] | None = None,
) -> dict[str, ModuleType]:
    """Import optional MCAP modules or raise a clear dependency error."""

    if module_names is None:
        module_names = _REQUIRED_OWAMCAP_MODULES

    loaded: dict[str, ModuleType] = {}
    missing: list[str] = []
    for module_name in module_names:
        try:
            loaded[module_name] = import_module(module_name)
        except ImportError:
            missing.append(module_name)
    if missing:
        raise OptionalOWAMcapDependencyError(missing)
    return loaded


class OWAMcapReader:
    """Thin optional adapter around the Python MCAP reader.

    This class deliberately avoids making MCAP a default dependency. It provides
    a raw-message iterator once the dependency is installed; real D2E schema
    decoding and message-to-canonical-event coverage are audited in the later
    real-D2E MLXP smoke story.
    """

    def __init__(self, mcap_path: str | Path) -> None:
        self.mcap_path = Path(mcap_path)
        modules = require_owamcap_dependencies()
        self._reader_module = modules["mcap.reader"]

    def iter_raw_messages(self) -> Iterator[OWAMcapMessage]:
        """Yield raw MCAP messages without requiring schema-specific decoders."""

        make_reader = getattr(self._reader_module, "make_reader")
        with self.mcap_path.open("rb") as file_obj:
            reader = make_reader(file_obj)
            for schema, channel, message in reader.iter_messages():
                yield OWAMcapMessage(
                    topic=getattr(channel, "topic", ""),
                    log_time_ns=int(getattr(message, "log_time")),
                    publish_time_ns=_optional_int(getattr(message, "publish_time", None)),
                    schema_name=getattr(schema, "name", None) if schema is not None else None,
                    data=bytes(getattr(message, "data")),
                )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _path_sort_key(path: Path) -> tuple[str, ...]:
    return tuple(part.casefold() for part in path.parts)


def _is_under_source_metadata(path: Path, labeled_root: Path) -> bool:
    try:
        relative = path.relative_to(labeled_root)
    except ValueError:
        return False
    return _SOURCE_METADATA_DIR in relative.parts
