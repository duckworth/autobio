from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Iterable

from openai import OpenAI

SUPPORTED_SUFFIXES = {
    ".m4a",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".wav",
    ".webm",
}
VOICE_MEMO_COPYABLE_SUFFIXES = {".m4a", ".mp3", ".mp4", ".wav"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
APPLE_EPOCH_OFFSET_SECONDS = 978307200
DEFAULT_VOICE_MEMOS_RECORDINGS_DIR = (
    "~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
)
FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{4})_(?P<topic>[a-z0-9][a-z0-9-]*)$"
)
ISO_TITLE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@dataclass(frozen=True)
class Settings:
    vault_root: Path
    inbox_dir: Path
    incoming_dir: Path
    processed_dir: Path
    failed_dir: Path
    session_log: Path
    model: str
    prompt: str
    poll_interval_seconds: float
    voice_memos_recordings_dir: Path
    voice_memos_db_path: Path
    voice_memos_state_path: Path


@dataclass(frozen=True)
class AudioMetadata:
    title: str
    date_recorded: str
    time_recorded: str
    topic_slug: str
    source_app: str | None = None
    source_title: str | None = None
    source_path: str | None = None
    voice_memo_unique_id: str | None = None

    @property
    def time_compact(self) -> str:
        return self.time_recorded.replace(":", "")


@dataclass(frozen=True)
class VoiceMemoRecord:
    unique_id: str
    title: str
    path: str
    recorded_at: datetime
    duration_seconds: float

    @property
    def suffix(self) -> str:
        return Path(self.path).suffix.lower()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def project_root() -> Path:
    return repo_root() / "_project"


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def settings_from_env() -> Settings:
    root = Path(os.environ.get("AUTOBIO_VAULT_ROOT", repo_root())).expanduser().resolve()
    project = project_root()
    voice_memos_dir = Path(
        os.environ.get(
            "AUTOBIO_VOICE_MEMOS_RECORDINGS_DIR",
            DEFAULT_VOICE_MEMOS_RECORDINGS_DIR,
        )
    ).expanduser()
    return Settings(
        vault_root=root,
        inbox_dir=root / "00 Inbox",
        incoming_dir=Path(
            os.environ.get("AUTOBIO_INCOMING_DIR", project / "pipeline" / "incoming-audio")
        ).expanduser(),
        processed_dir=Path(
            os.environ.get("AUTOBIO_PROCESSED_DIR", project / "pipeline" / "processed-audio")
        ).expanduser(),
        failed_dir=Path(
            os.environ.get("AUTOBIO_FAILED_DIR", project / "pipeline" / "failed-audio")
        ).expanduser(),
        session_log=root / "99 Admin" / "session-log.md",
        model=os.environ.get("AUTOBIO_TRANSCRIPTION_MODEL", "gpt-4o-transcribe"),
        prompt=os.environ.get(
            "AUTOBIO_TRANSCRIPTION_PROMPT",
            (
                "Transcribe this memoir recording faithfully. Preserve the speaker's "
                "wording, uncertainty, and punctuation. Do not summarize or invent "
                "missing details."
            ),
        ),
        poll_interval_seconds=float(os.environ.get("AUTOBIO_POLL_INTERVAL_SECONDS", "10")),
        voice_memos_recordings_dir=voice_memos_dir,
        voice_memos_db_path=Path(
            os.environ.get(
                "AUTOBIO_VOICE_MEMOS_DB_PATH",
                voice_memos_dir / "CloudRecordings.db",
            )
        ).expanduser(),
        voice_memos_state_path=root / "99 Admin" / "voice-memos-import-state.json",
    )


def ensure_directories(settings: Settings) -> None:
    for path in (
        settings.inbox_dir,
        settings.incoming_dir,
        settings.processed_dir,
        settings.failed_dir,
        settings.session_log.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)

    if not settings.session_log.exists():
        settings.session_log.write_text(
            "# Session Log\n\nThis log is appended automatically by the transcription script.\n\n## Entries\n",
            encoding="utf-8",
        )


def normalize_slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "untitled-recording"


def yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def audio_sidecar_path(audio_path: Path) -> Path:
    return audio_path.with_name(f"{audio_path.name}.json")


def load_audio_sidecar(audio_path: Path) -> dict[str, Any]:
    sidecar_path = audio_sidecar_path(audio_path)
    if not sidecar_path.exists():
        return {}
    return json.loads(sidecar_path.read_text(encoding="utf-8"))


def metadata_for_audio(audio_path: Path) -> AudioMetadata:
    sidecar = load_audio_sidecar(audio_path)
    if sidecar:
        return AudioMetadata(
            title=sidecar.get("title") or audio_path.stem.replace("-", " ").title(),
            date_recorded=sidecar.get("date_recorded"),
            time_recorded=sidecar.get("time_recorded"),
            topic_slug=sidecar.get("topic_slug") or normalize_slug(audio_path.stem),
            source_app=sidecar.get("source_app"),
            source_title=sidecar.get("source_title"),
            source_path=sidecar.get("source_path"),
            voice_memo_unique_id=sidecar.get("voice_memo_unique_id"),
        )

    match = FILENAME_RE.match(audio_path.stem)
    if match:
        date_recorded = match.group("date")
        time_compact = match.group("time")
        topic_slug = normalize_slug(match.group("topic"))
        time_recorded = f"{time_compact[:2]}:{time_compact[2:]}"
    else:
        modified_at = datetime.fromtimestamp(audio_path.stat().st_mtime).astimezone()
        date_recorded = modified_at.strftime("%Y-%m-%d")
        time_recorded = modified_at.strftime("%H:%M")
        topic_slug = normalize_slug(audio_path.stem)

    title = topic_slug.replace("-", " ").title()
    return AudioMetadata(
        title=title,
        date_recorded=date_recorded,
        time_recorded=time_recorded,
        topic_slug=topic_slug,
    )


def transcript_path_for(settings: Settings, metadata: AudioMetadata) -> Path:
    base_name = f"{metadata.date_recorded}_{metadata.time_compact}_{metadata.topic_slug}.md"
    return unique_path(settings.inbox_dir / base_name)


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def build_markdown(audio_name: str, metadata: AudioMetadata, transcript_text: str, model: str) -> str:
    safe_transcript = transcript_text.strip() or "[empty transcript]"
    frontmatter_lines = [
        "---",
        f"title: {yaml_quote(metadata.title)}",
        f"date_recorded: {metadata.date_recorded}",
        f"time_recorded: {metadata.time_recorded}",
        f"source_audio: {yaml_quote(audio_name)}",
        f"transcription_model: {yaml_quote(model)}",
    ]
    if metadata.source_app:
        frontmatter_lines.append(f"source_app: {yaml_quote(metadata.source_app)}")
    if metadata.source_title:
        frontmatter_lines.append(f"source_title: {yaml_quote(metadata.source_title)}")
    if metadata.source_path:
        frontmatter_lines.append(f"source_path: {yaml_quote(metadata.source_path)}")
    if metadata.voice_memo_unique_id:
        frontmatter_lines.append(f"voice_memo_unique_id: {yaml_quote(metadata.voice_memo_unique_id)}")
    frontmatter_lines.extend(
        [
            "status: raw",
            "tags:",
            "  - transcript",
            "  - inbox",
            "---",
        ]
    )
    return (
        "\n".join(frontmatter_lines)
        + "\n\n# Summary\n"
        "To be filled later.\n\n"
        "# Raw Transcript\n"
        f"{safe_transcript}\n\n"
        "# Notes\n"
        "- Recording type: story / timeline / guidance\n"
        "- Approximate year:\n"
        "- People mentioned:\n"
        "- Places mentioned:\n"
        "- Follow-up needed:\n"
    )


def append_session_log(settings: Settings, status: str, audio_name: str, detail: str) -> None:
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    entry = f"- {timestamp} | {status} | {audio_name} | {detail}\n"
    with settings.session_log.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def supported_audio_files(incoming_dir: Path) -> Iterable[Path]:
    for path in sorted(incoming_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path


def validate_audio(audio_path: Path) -> None:
    suffix = audio_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {suffix}")

    size = audio_path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"Audio file is {size} bytes, which exceeds the 25 MB transcription limit."
        )


def extract_transcript_text(result: object) -> str:
    if isinstance(result, str):
        return result.strip()

    text = getattr(result, "text", None)
    if isinstance(text, str):
        return text.strip()

    if isinstance(result, dict):
        maybe_text = result.get("text")
        if isinstance(maybe_text, str):
            return maybe_text.strip()

    raise RuntimeError(f"Unexpected transcription response type: {type(result)!r}")


def transcribe_audio(client: OpenAI, settings: Settings, audio_path: Path) -> str:
    with audio_path.open("rb") as audio_file:
        result = client.audio.transcriptions.create(
            model=settings.model,
            file=audio_file,
            response_format="text",
            prompt=settings.prompt,
        )
    return extract_transcript_text(result)


def move_with_sidecar(audio_path: Path, target_dir: Path) -> Path:
    destination = unique_path(target_dir / audio_path.name)
    shutil.move(str(audio_path), str(destination))

    sidecar_path = audio_sidecar_path(audio_path)
    if sidecar_path.exists():
        shutil.move(str(sidecar_path), str(audio_sidecar_path(destination)))
    return destination


def process_one(client: OpenAI, settings: Settings, audio_path: Path) -> None:
    validate_audio(audio_path)
    metadata = metadata_for_audio(audio_path)
    transcript_path = transcript_path_for(settings, metadata)

    transcript_text = transcribe_audio(client, settings, audio_path)
    transcript_markdown = build_markdown(
        audio_name=audio_path.name,
        metadata=metadata,
        transcript_text=transcript_text,
        model=settings.model,
    )
    transcript_path.write_text(transcript_markdown, encoding="utf-8")
    processed_path = move_with_sidecar(audio_path, settings.processed_dir)
    append_session_log(
        settings,
        status="processed",
        audio_name=processed_path.name,
        detail=f"transcript={transcript_path.relative_to(settings.vault_root)}",
    )
    print(f"processed {processed_path.name} -> {transcript_path.relative_to(settings.vault_root)}")


def process_batch(settings: Settings) -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy _project/.env.example to .env and add your key."
        )

    client = OpenAI(api_key=api_key)
    processed_count = 0
    for audio_path in supported_audio_files(settings.incoming_dir):
        try:
            process_one(client, settings, audio_path)
            processed_count += 1
        except Exception as exc:  # noqa: BLE001
            failed_path = move_with_sidecar(audio_path, settings.failed_dir)
            append_session_log(settings, "failed", failed_path.name, f"error={exc}")
            print(f"failed {failed_path.name}: {exc}", file=sys.stderr)
    return processed_count


def voice_memos_db_exists(settings: Settings) -> bool:
    return settings.voice_memos_db_path.exists()


def clean_voice_memo_title(title: str | None, fallback_path: str) -> str:
    if title and not ISO_TITLE_RE.match(title.strip()):
        return title.strip()
    return Path(fallback_path).stem.replace("-", " ").strip()


def apple_timestamp_to_local(value: float) -> datetime:
    return datetime.fromtimestamp(value + APPLE_EPOCH_OFFSET_SECONDS).astimezone()


def voice_memo_records(settings: Settings, match_text: str | None = None) -> list[VoiceMemoRecord]:
    if not voice_memos_db_exists(settings):
        raise RuntimeError(f"Voice Memos database not found at {settings.voice_memos_db_path}")

    query = (
        "SELECT ZUNIQUEID, ZENCRYPTEDTITLE, ZCUSTOMLABEL, ZPATH, ZDATE, ZDURATION "
        "FROM ZCLOUDRECORDING "
        "WHERE ZPATH IS NOT NULL AND ZPATH != '' "
        "ORDER BY ZDATE DESC"
    )
    records: list[VoiceMemoRecord] = []
    with sqlite3.connect(settings.voice_memos_db_path) as connection:
        for unique_id, encrypted_title, custom_label, path, recorded_at, duration_seconds in connection.execute(query):
            title = clean_voice_memo_title(encrypted_title or custom_label, path)
            record = VoiceMemoRecord(
                unique_id=unique_id or path,
                title=title,
                path=path,
                recorded_at=apple_timestamp_to_local(float(recorded_at)),
                duration_seconds=float(duration_seconds or 0),
            )
            if match_text:
                haystack = f"{record.title} {record.path}".lower()
                if match_text.lower() not in haystack:
                    continue
            records.append(record)
    return records


def load_voice_memos_state(settings: Settings) -> dict[str, Any]:
    if not settings.voice_memos_state_path.exists():
        return {"seen": []}
    return json.loads(settings.voice_memos_state_path.read_text(encoding="utf-8"))


def save_voice_memos_state(settings: Settings, state: dict[str, Any]) -> None:
    settings.voice_memos_state_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def seen_voice_memo_ids(settings: Settings) -> set[str]:
    state = load_voice_memos_state(settings)
    return set(state.get("seen", []))


def mark_voice_memos_seen(settings: Settings, records: Iterable[VoiceMemoRecord]) -> None:
    current = seen_voice_memo_ids(settings)
    current.update(record.unique_id for record in records)
    state = {
        "updated_at": datetime.now().astimezone().isoformat(),
        "seen": sorted(current),
    }
    save_voice_memos_state(settings, state)


def seed_voice_memos_state(settings: Settings) -> int:
    records = voice_memo_records(settings)
    mark_voice_memos_seen(settings, records)
    return len(records)


def build_import_name(record: VoiceMemoRecord) -> str:
    date_part = record.recorded_at.strftime("%Y-%m-%d")
    time_part = record.recorded_at.strftime("%H%M")
    topic_slug = normalize_slug(record.title)
    return f"{date_part}_{time_part}_{topic_slug}.m4a"


def write_import_sidecar(audio_path: Path, record: VoiceMemoRecord) -> None:
    payload = {
        "title": record.title,
        "date_recorded": record.recorded_at.strftime("%Y-%m-%d"),
        "time_recorded": record.recorded_at.strftime("%H:%M"),
        "topic_slug": normalize_slug(record.title),
        "source_app": "voice-memos",
        "source_title": record.title,
        "source_path": record.path,
        "voice_memo_unique_id": record.unique_id,
    }
    audio_sidecar_path(audio_path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def ffmpeg_path() -> str:
    command = shutil.which("ffmpeg")
    if command:
        return command
    raise RuntimeError("ffmpeg is required to import .qta Voice Memos files but was not found in PATH.")


def import_voice_memo_record(settings: Settings, record: VoiceMemoRecord) -> Path:
    source_path = settings.voice_memos_recordings_dir / record.path
    if not source_path.exists():
        raise RuntimeError(f"Voice Memo source file is missing: {source_path}")

    destination = unique_path(settings.incoming_dir / build_import_name(record))
    suffix = source_path.suffix.lower()

    if suffix in VOICE_MEMO_COPYABLE_SUFFIXES:
        shutil.copy2(source_path, destination)
    elif suffix == ".qta":
        subprocess.run(
            [
                ffmpeg_path(),
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source_path),
                "-vn",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(destination),
            ],
            check=True,
        )
    else:
        raise RuntimeError(f"Unsupported Voice Memos source format: {suffix}")

    write_import_sidecar(destination, record)
    append_session_log(
        settings,
        status="imported",
        audio_name=destination.name,
        detail=f"source=voice-memos original={record.path}",
    )
    return destination


def select_voice_memos_to_import(
    settings: Settings,
    *,
    latest: int | None,
    all_unseen: bool,
    match_text: str | None,
    force: bool,
) -> list[VoiceMemoRecord]:
    records = voice_memo_records(settings, match_text=match_text)
    if force:
        selected = records
    else:
        seen = seen_voice_memo_ids(settings)
        selected = [record for record in records if record.unique_id not in seen]

    if all_unseen:
        return selected
    if latest is None:
        latest = 1
    return selected[:latest]


def import_voice_memos(
    settings: Settings,
    *,
    latest: int | None,
    all_unseen: bool,
    match_text: str | None,
    force: bool,
) -> int:
    records = select_voice_memos_to_import(
        settings,
        latest=latest,
        all_unseen=all_unseen,
        match_text=match_text,
        force=force,
    )
    imported: list[VoiceMemoRecord] = []
    for record in records:
        destination = import_voice_memo_record(settings, record)
        print(f"imported {record.path} -> {destination.name}")
        imported.append(record)

    if imported and not force:
        mark_voice_memos_seen(settings, imported)
    elif imported and force:
        mark_voice_memos_seen(settings, imported)
    return len(imported)


def print_voice_memos(settings: Settings, *, limit: int, match_text: str | None) -> None:
    records = voice_memo_records(settings, match_text=match_text)
    seen = seen_voice_memo_ids(settings)
    for record in records[:limit]:
        marker = "seen" if record.unique_id in seen else "new "
        timestamp = record.recorded_at.strftime("%Y-%m-%d %H:%M")
        print(f"{marker} | {timestamp} | {record.duration_seconds:6.1f}s | {record.title} | {record.path}")


def print_config(settings: Settings) -> None:
    print(f"vault_root={settings.vault_root}")
    print(f"inbox_dir={settings.inbox_dir}")
    print(f"incoming_dir={settings.incoming_dir}")
    print(f"processed_dir={settings.processed_dir}")
    print(f"failed_dir={settings.failed_dir}")
    print(f"session_log={settings.session_log}")
    print(f"model={settings.model}")
    print(f"poll_interval_seconds={settings.poll_interval_seconds}")
    print(f"voice_memos_recordings_dir={settings.voice_memos_recordings_dir}")
    print(f"voice_memos_db_path={settings.voice_memos_db_path}")
    print(f"voice_memos_state_path={settings.voice_memos_state_path}")


def watch(
    settings: Settings,
    poll_interval: float | None = None,
    *,
    import_voice_memos_enabled: bool = False,
) -> int:
    interval = poll_interval if poll_interval is not None else settings.poll_interval_seconds
    if import_voice_memos_enabled and not settings.voice_memos_state_path.exists():
        seeded = seed_voice_memos_state(settings)
        print(f"seeded Voice Memos state with {seeded} existing recording(s)")

    print(f"watching {settings.incoming_dir} every {interval:.1f}s")
    try:
        while True:
            if import_voice_memos_enabled:
                import_voice_memos(
                    settings,
                    latest=None,
                    all_unseen=True,
                    match_text=None,
                    force=False,
                )
            processed = process_batch(settings)
            if processed == 0:
                time.sleep(interval)
    except KeyboardInterrupt:
        print("stopped watcher")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe memoir audio files into Markdown notes for the autobiography vault."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("config", help="Print the effective configuration.")
    subparsers.add_parser("process", help="Process all supported files in the incoming folder once.")

    list_parser = subparsers.add_parser(
        "voice-memos-list",
        help="List recent recordings discovered in the local Voice Memos database.",
    )
    list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of recordings to show.")
    list_parser.add_argument(
        "--match",
        default=None,
        help="Filter by text contained in the title or source path.",
    )

    import_parser = subparsers.add_parser(
        "import-voice-memos",
        help="Copy or convert Voice Memos recordings into the incoming pipeline folder.",
    )
    import_parser.add_argument(
        "--latest",
        type=int,
        default=1,
        help="Import the newest unseen recordings. Ignored when --all-unseen is set.",
    )
    import_parser.add_argument(
        "--all-unseen",
        action="store_true",
        help="Import every unseen recording that matches the current filter.",
    )
    import_parser.add_argument(
        "--match",
        default=None,
        help="Filter by text contained in the title or source path.",
    )
    import_parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the seen-state file and import matching recordings again.",
    )

    subparsers.add_parser(
        "seed-voice-memos-state",
        help="Mark the current Voice Memos library as seen so watch mode only imports future recordings.",
    )

    watch_parser = subparsers.add_parser(
        "watch",
        help="Poll the incoming folder and process files continuously.",
    )
    watch_parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help="Override AUTOBIO_POLL_INTERVAL_SECONDS for this run.",
    )
    watch_parser.add_argument(
        "--import-voice-memos",
        action="store_true",
        help="Also import new Voice Memos recordings before each processing pass.",
    )
    return parser


def main() -> int:
    try:
        load_dotenv(repo_root() / ".env")
        settings = settings_from_env()
        ensure_directories(settings)

        parser = build_parser()
        args = parser.parse_args()

        if args.command == "config":
            print_config(settings)
            return 0
        if args.command == "process":
            processed = process_batch(settings)
            print(f"completed batch with {processed} processed file(s)")
            return 0
        if args.command == "voice-memos-list":
            print_voice_memos(settings, limit=args.limit, match_text=args.match)
            return 0
        if args.command == "import-voice-memos":
            imported = import_voice_memos(
                settings,
                latest=args.latest,
                all_unseen=args.all_unseen,
                match_text=args.match,
                force=args.force,
            )
            print(f"completed import with {imported} file(s)")
            return 0
        if args.command == "seed-voice-memos-state":
            seeded = seed_voice_memos_state(settings)
            print(f"seeded state with {seeded} Voice Memos recording(s)")
            return 0
        if args.command == "watch":
            return watch(
                settings,
                poll_interval=args.poll_interval,
                import_voice_memos_enabled=args.import_voice_memos,
            )

        parser.error(f"Unknown command: {args.command}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
