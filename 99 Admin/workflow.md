# Workflow

## Core Principle

- Build a memory archive first and a book second.
- Use the sequence `capture -> organize -> interpret -> write`.
- Treat recurring memories as high-priority recording candidates because memory decays.

## Recording

- Record in Voice Memos on iPhone.
- Keep recordings between 10 and 25 minutes.
- Capture one memory, person, or event per recording.
- Prefer concrete scenes and turning points over broad categories.
- Start each recording with the approximate year, place, people involved, and a short title.
- Also use these special recording modes when helpful:
- `timeline`: a broad sweep through the major periods of your life in rough order.
- `guidance`: a memo about what future cleanup, extraction, or drafting should focus on.
- If a memory keeps resurfacing, record it even if it is incomplete.
- Do not force painful material on a rigid schedule. Pace it.

## Intake

- Drag new audio from Voice Memos on Mac into the configured incoming folder.
- Or use `./_project/scripts/autobio-transcribe import-voice-memos --latest 1` to pull the newest synced Voice Memo directly from the local Voice Memos storage folder.
- Run `./_project/scripts/autobio-transcribe process` for phase one.
- Later, switch to `./_project/scripts/autobio-transcribe watch --import-voice-memos` if you want the importer and transcriber to run together.

## Transcript Promotion

1. Review new notes in [[00 Inbox]].
2. Keep, retitle, and tag the worthwhile ones.
3. Move untouched keepers into `01 Raw Transcripts/`.
4. Move cleaned versions into [[02 Clean Transcripts]].
5. Use [[99 Admin/review-checklist|Review Checklist]] during this step.
6. If you later answer an open question directly, update the clean transcript and mark it as a later author clarification instead of silently rewriting the raw note.

## Structured Extraction

From cleaned transcripts:

- update [[03 Timeline/master-timeline|Master Timeline]]
- add unresolved chronology to [[03 Timeline/open-questions|Open Questions]]
- create or update notes in `04 People/`
- create or update notes in `05 Places/`
- create or update notes in `06 Themes/`
- add follow-up prompts to [[99 Admin/gap-log|Gap Log]]

## Drafting

- Build chapter fragments in [[07 Chapters]] only after transcript cleanup and structured extraction.
- Prefer meaningful slices and turning points over trying to narrate your whole life in order.
- Track active chapter candidates in [[07 Chapters/chapter-plan|Chapter Plan]].
- Commit the vault at least weekly.

## Management Notes

- [[99 Admin/dashboard|Dashboard]]: current focus and weekly control panel
- [[99 Admin/project-principles|Project Principles]]: archive-first editorial rules
- [[99 Admin/gap-log|Gap Log]]: missing details and future recording prompts
- [[99 Admin/review-checklist|Review Checklist]]: transcript processing checklist
- [[03 Timeline/open-questions|Open Questions]]: unresolved chronology
- [[07 Chapters/chapter-plan|Chapter Plan]]: chapter candidate pipeline

## Linking Rule

- Use Obsidian wikilinks like `[[03 Timeline/master-timeline|Master Timeline]]` for internal note references.
- Do not use backticked file paths for note-to-note references when the intent is navigation inside Obsidian.
