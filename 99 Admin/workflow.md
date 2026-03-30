# Workflow

## Recording

- Record in Voice Memos on iPhone.
- Keep recordings between 10 and 25 minutes.
- Capture one memory, person, or event per recording.
- Start each recording with the approximate year, place, people involved, and a short title.
- Also use these special recording modes when helpful:
- `timeline`: a broad sweep through the major periods of your life in rough order.
- `guidance`: a memo about what future cleanup, extraction, or drafting should focus on.

## Intake

- Drag new audio from Voice Memos on Mac into the configured incoming folder.
- Or use `./scripts/autobio-transcribe import-voice-memos --latest 1` to pull the newest synced Voice Memo directly from the local Voice Memos storage folder.
- Run `./scripts/autobio-transcribe process` for phase one.
- Later, switch to `./scripts/autobio-transcribe watch --import-voice-memos` if you want the importer and transcriber to run together.

## Transcript Promotion

1. Review new notes in `00 Inbox/`.
2. Keep, retitle, and tag the worthwhile ones.
3. Move untouched keepers into `01 Raw Transcripts/`.
4. Move cleaned versions into `02 Clean Transcripts/`.
5. Use `99 Admin/review-checklist.md` during this step.

## Structured Extraction

From cleaned transcripts:

- update `03 Timeline/master-timeline.md`
- add unresolved chronology to `03 Timeline/open-questions.md`
- create or update notes in `04 People/`
- create or update notes in `05 Places/`
- create or update notes in `06 Themes/`
- add follow-up prompts to `99 Admin/gap-log.md`

## Drafting

- Build chapter fragments in `07 Chapters/` only after transcript cleanup and structured extraction.
- Track active chapter candidates in `07 Chapters/chapter-plan.md`.
- Commit the vault at least weekly.

## Management Notes

- `99 Admin/dashboard.md`: current focus and weekly control panel
- `99 Admin/gap-log.md`: missing details and future recording prompts
- `99 Admin/review-checklist.md`: transcript processing checklist
- `03 Timeline/open-questions.md`: unresolved chronology
- `07 Chapters/chapter-plan.md`: chapter candidate pipeline
