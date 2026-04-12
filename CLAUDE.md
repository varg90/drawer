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
- Working directory: C:\Users\Ellie\sandbox
- Language: Python
- GUI framework: CustomTkinter (installed)
- Entry point: python main.py
- App type: Drawer — image reference viewer with timers
- Plugin: Superpowers installed

## Development Workflow
1. Oksana describes what she wants in plain language (Russian/English)
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

## DISTILLED_AESTHETICS_PROMPT = """
<frontend_aesthetics>
You tend to converge toward generic, "on distribution" outputs. In frontend design, this creates what users call the "AI slop" aesthetic. Avoid this: make creative, distinctive frontends that surprise and delight. Focus on:

Typography: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics.

Color & Theme: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Draw from IDE themes and cultural aesthetics for inspiration.

Motion: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions.

Backgrounds: Create atmosphere and depth rather than defaulting to solid colors. Layer CSS gradients, use geometric patterns, or add contextual effects that match the overall aesthetic.

Avoid generic AI-generated aesthetics:
- Overused font families (Inter, Roboto, Arial, system fonts)
- Clichéd color schemes (particularly purple gradients on white backgrounds)
- Predictable layouts and component patterns
- Cookie-cutter design that lacks context-specific character

Interpret creatively and make unexpected choices that feel genuinely designed for the context. Vary between light and dark themes, different fonts, different aesthetics. You still tend to converge on common choices (Space Grotesk, for example) across generations. Avoid this: it is critical that you think outside the box!
</frontend_aesthetics>
"""