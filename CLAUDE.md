# Project: RefBot — Windows Desktop App

## User — Oksana
- Non-developer, zero coding experience, first app ever
- Will NOT write code — you (Claude) write ALL code, Oksana only runs it
- Communicates in Russian, code comments in English are fine
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
- Working directory: C:\Users\Ellie\sandbox
- Language: Python
- GUI framework: CustomTkinter (installed)
- Entry point: python main.py
- App type: RefBot — image reference viewer with timers
- Plugin: Superpowers installed

## Development Workflow
1. Oksana describes what she wants in plain language (Russian)
2. You write all code and create all files
3. You run and test commands directly
4. Keep app launchable via: python main.py
5. Start simple, add features incrementally
6. Always verify code works before presenting to Oksana

## Installed Packages
- customtkinter 5.2.2
- darkdetect 0.8.0
- packaging 26.0

## Known Quirks
- pip is not on PATH directly, always use: python -m pip
- OAuth localhost redirect didn't work initially, logged in via browser manually
