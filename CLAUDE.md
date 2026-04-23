# Project: Drawer — Windows Desktop App

## User — Oksana
- Non-developer, zero coding experience, first app ever
- Will NOT write code — you (Claude) write ALL code, Oksana only runs it
- Communicates in Russian and English, you (Claude) communicate only in english, regardless of input language.
- Do not assume any tech expertise — explain everything simply.
- **Push back on wrong suggestions and ideas.** Because Oksana lacks dev expertise, some of her instructions or ideas will be wrong from a code or architecture perspective. When that happens, say so directly, explain why in plain terms, and offer alternatives. She relies on Claude's judgment; silently implementing a bad request is a disservice.
- Be patient, test everything before presenting. 

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
5. Push back on wrong instructions. If Oksana's request conflicts with the spec, the architecture invariants, or basic code correctness, say so directly, explain why, and propose alternatives. Do not implement silently.
6. Always verify code works before presenting to Oksana. If something cannot be tested locally, say so explicitly rather than implying success.
7. **Branch.** ALWAYS Create a feature branch off `main` (`feat/…`, `fix/…`, `chore/…`, `docs/…`). Never commit directly to `main` unless you specifically got a permission to do so
8. Commit in git only if tests pass. A red test means the branch stays uncommitted until it's green.
9. Simplify code 1. After finishing a feature - clean up before review. 2. After a bug fix - make sure the fix didn't introduce shortcuts 3. After a prototype - tighten up experimental code you want to keep 4. Before a PR - catch issues a reviewer would flag. Review the diff for dead code, premature abstractions, unnecessary comments, duplicated logic. The `simplify` skill is available for this pass. ALways tell Oksana that you finished simplify. If it's an overkill for a current work, say so explicitly, do not skip silently.
10. Oksana runs the app in python main.py and gives approval → only then push → PR
11. ALWAYS review PR → fix what can be fixed → discuss the rest
12. Oksana runs the app again → merge ONLY after Oksana's command
13. clean up the branch after merge


## Installed Packages (see requirements.txt for source of truth)
- PyQt6 >= 6.6
- qtawesome >= 1.3

## Known Quirks
- pip is not on PATH directly, always use: python -m pip
- OAuth localhost redirect didn't work initially, logged in via browser manually

