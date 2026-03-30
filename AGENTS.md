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
- `pipeline/` holds local runtime intake folders and should not be treated as durable source content.
- `src/autobio_pipeline/cli.py` is the main automation entry point.

## Working Rules

- Treat the repository root as the only AI-visible vault.
- Do not point tooling at any other Obsidian vault.
- Keep audio ingest filenames stable and machine-friendly.
- Prefer renaming transcript notes only after human review.
- Preserve provenance in frontmatter when moving or renaming notes.
- Keep transcript cleanup light. Do not invent facts, chronology, or dialogue.

## Commands

- `uv sync`
- `./scripts/autobio-transcribe config`
- `./scripts/autobio-transcribe voice-memos-list`
- `./scripts/autobio-transcribe import-voice-memos --latest 1`
- `./scripts/autobio-transcribe process`
- `./scripts/autobio-transcribe watch --import-voice-memos`

## Commit Hygiene

- Do not commit `.env`.
- Do not commit audio files from `pipeline/`.
- Do not commit transient runtime state.
- Commit vault structure, prompt templates, workflow docs, and code.

## Content Management

- Use `99 Admin/review-checklist.md` when processing Inbox notes.
- Track unresolved chronology in `03 Timeline/open-questions.md`.
- Track missing details and future memo prompts in `99 Admin/gap-log.md`.
- Track drafting candidates in `07 Chapters/chapter-plan.md`.
