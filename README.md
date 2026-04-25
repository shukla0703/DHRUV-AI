# DHRUV AI

DHRUV AI is a Windows-first voice assistant and desktop control application with a branded control-center UI, persistent memory, voice input, wake-word support, and a LangChain-powered action layer.

The current build is centered on the provided DHRUV logo and visual language:

- deep midnight backgrounds
- electric cyan and blue signal accents
- white star-core highlights
- logo-first dashboard composition

## What It Does

- voice and typed interaction
- wake-word listening
- open websites, including direct URLs and common domains
- launch common Windows apps
- system status, including CPU type
- persistent local memory for searches, opened sites, and assistant replies
- LangChain/OpenAI-backed fallback intelligence

## Project Structure

```text
DHRUV AI/
├── DHRUV.spec
├── assets/
├── build_windows_app.ps1
├── design/
├── main.py
├── main.pyw
├── README.md
├── requirements.txt
└── src/
└── dhruv/
```

## Branding Assets

- Main logo: [assets/dhruv-logo.png](C:\Users\shamb\OneDrive\Documents\Codes\Aether AI\assets\dhruv-logo.png)
- Windows icon: [assets/dhruv-logo.ico](C:\Users\shamb\OneDrive\Documents\Codes\Aether AI\assets\dhruv-logo.ico)
- UI theme notes: [design/dhruv_ui_theme.md](C:\Users\shamb\OneDrive\Documents\Codes\Aether AI\design\dhruv_ui_theme.md)
- Landing-page concept: [design/dhruv_landing_page_concept.html](C:\Users\shamb\OneDrive\Documents\Codes\Aether AI\design\dhruv_landing_page_concept.html)

## Environment

Copy `.env.example` to `.env` and adjust as needed.

Important defaults:

- `AETHER_NAME=DHRUV AI`
- `AETHER_WAKE_WORD=dhruv`
- `AETHER_MEMORY_TURNS=6`
- `AETHER_MEMORY_STORE=data/dhruv_memory.json`

Optional keys:

- `OPENAI_API_KEY`
- `NEWS_API_KEY`
- `OPENCAGE_API_KEY`

## Run

Standard launch:

```powershell
python main.py
```

Windowed launch without terminal:

```powershell
pythonw main.pyw
```

## Example Commands

- `dhruv what time is it`
- `open reddit.com`
- `open huggingface`
- `open https://example.com`
- `check system status`
- `what cpu do i have`
- `recall recent memory`

## Build The Windows App

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows_app.ps1
```

That builds the packaged desktop app into `dist\DHRUV AI`.

## UI Direction

The desktop interface is now designed as a guidance dashboard rather than a generic neon HUD:

- hero section with the supplied DHRUV logo
- command console with stronger action hierarchy
- live memory vault
- orbital star-core center visual
- cyan/blue signal styling derived from the logo

## Notes

- The internal Python package path now matches the product branding at `src/dhruv`.
- The packaged app icon is generated from the supplied logo.
- The landing-page concept file is a static design artifact, not yet a production web app.
