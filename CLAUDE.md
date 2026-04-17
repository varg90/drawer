# Project: Drawer — Windows Desktop App

## User — Oksana
- Non-developer, zero coding experience, first app ever
- Will NOT write code — you (Claude) write ALL code, Oksana only runs it
- Communicates in Russian and English, code comments in English are fine
- Do not assume any tech expertise — explain everything simply
- Be patient, test everything before presenting

## Environment (Windows PC)
- OS: Windows
- Python: 3.14.3 (installed, on PATH)
- Node.js: v24.14.1
- Claude Code: installed via npm, auth via claude.ai (Max x5 subscription)
- No C# installed
- PowerShell execution policy: RemoteSigned
- pip works via: python -m pip install <package> (not just pip)
- Paste in terminal: right-click mouse (Ctrl+V doesn't work in Claude Code)

## Project Setup
- Working directory: C:\Users\Ellie\Drawer
- Language: Python
- GUI framework: PyQt6 (migrated from CustomTkinter; CustomTkinter no longer used)
- Entry point: python main.py
- App type: Drawer — image reference/discipline tool with timers (not a general viewer — no zoom/pan/annotations)
- Current version: 0.5.0
- Plugin: Superpowers installed

## Development Workflow
1. Oksana describes what she wants in plain language (Russian/English)
2. You write all code and create all files
3. You run and test commands directly
4. Keep app launchable via: python main.py
5. Start simple, add features incrementally
6. Always verify code works before presenting to Oksana
7. Commit every change that pass tests

## Installed Packages (see requirements.txt for source of truth)
- PyQt6 >= 6.6
- qtawesome >= 1.3

## Known Quirks
- pip is not on PATH directly, always use: python -m pip
- OAuth localhost redirect didn't work initially, logged in via browser manually

