# AGENTS

## Purpose

This repository is an Obsidian vault plus a local transcription/import pipeline for an autobiography project.

## Repo Shape

- `00 Inbox/` holds newly generated transcript notes.
- `01 Raw Transcripts/` and `02 Clean Transcripts/` hold promoted material.
- `03 Timeline/`, `04 People/`, `05 Places/`, and `06 Themes/` hold extracted notes.
- `07 Chapters/` holds chapter planning and draft material.
- `08 Prompts/` holds reusable prompt templates.
- `99 Admin/` holds workflow, tracking, and review notes.
- `_project/` holds local tooling, runtime folders, and Python project files.
- `_project/src/autobio_pipeline/cli.py` is the main automation entry point.

## Working Rules

- Treat the repository root as the only AI-visible vault.
- Do not point tooling at any other Obsidian vault.
- Keep audio ingest filenames stable and machine-friendly.
- Prefer renaming transcript notes only after human review.
- Preserve provenance in frontmatter when moving or renaming notes.
- Keep transcript cleanup light. Do not invent facts, chronology, or dialogue.
- Keep raw transcript notes unchanged. If the author later supplies a direct factual clarification, merge it into the clean note and label it as a later author clarification with the date.
- Use Obsidian wikilinks for internal note references, for example `[[03 Timeline/master-timeline|Master Timeline]]`.
- Do not use backticked file paths when the intent is to create clickable note links inside the vault.

## Commands

- `uv --project _project sync`
- `./_project/scripts/autobio-transcribe config`
- `./_project/scripts/autobio-transcribe voice-memos-list`
- `./_project/scripts/autobio-transcribe import-voice-memos --latest 1`
- `./_project/scripts/autobio-transcribe process`
- `./_project/scripts/autobio-transcribe watch --import-voice-memos`

## Commit Hygiene

- Do not commit `.env`.
- Do not commit audio files from `_project/pipeline/`.
- Do not commit transient runtime state.
- Commit vault structure, prompt templates, workflow docs, and code.

## Content Management

- Use [[99 Admin/review-checklist|Review Checklist]] when processing Inbox notes.
- Track unresolved chronology in [[03 Timeline/open-questions|Open Questions]].
- Track missing details and future memo prompts in [[99 Admin/gap-log|Gap Log]].
- Track drafting candidates in [[07 Chapters/chapter-plan|Chapter Plan]].
