# Getting Started with Claude Code — for the Geotech Website Project

## What it actually is

Claude Code is Claude, but running in your project folder with the ability to read files, write code, run commands (like installing packages or running tests), and edit multiple files across a real codebase — instead of just chatting in a browser. You describe what you want; it plans, writes the code, runs it, and shows you the result. You approve or redirect as it goes.

You have two reasonable ways to run it. For an actual multi-file app build like this one, I'd use the **terminal** — it's the most capable and what nearly all instructions assume. If you'd rather avoid the command line entirely, the **Desktop app** does the same thing with a visual interface and diff review, which is more forgiving for a first-timer. Details for both below — pick one.

---

## Option A: Terminal (recommended for this project)

### 1. Install

Open a terminal (Terminal on Mac, or PowerShell on Windows) and run the command for your OS:

**macOS / Linux:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://claude.ai/install.ps1 | iex
```

This installs Claude Code and keeps it auto-updated. (If you'd rather use Homebrew or WinGet, those work too, but you'll need to update manually — the command above is simplest.)

### 2. Start it in your project folder

```bash
mkdir geotech-webapp
cd geotech-webapp
claude
```

First time, it'll open a browser window asking you to log in with your Claude account (the same one you're using here — needs a paid Claude subscription, or an Anthropic Console/API account).

### 3. You're in

You'll see a prompt where you just type in plain English. No special syntax.

---

## Option B: Desktop app (no terminal)

Download from claude.ai (Mac or Windows), install, sign in, and click the **Code** tab. It opens a project folder picker, then works the same way — you type requests, it shows you diffs before applying them. Requires a paid subscription.

---

## Setting up the project folder

1. Create a folder, e.g. `geotech-webapp`.
2. Inside it, make a subfolder `reference/` and put in it:
   - `parse_reports.py`, `emerson_results.csv`, `psd_results.csv`, `atterberg_results.csv`, `psd_chart.png`, `atterberg_chart.png` (everything I generated in this chat)
   - `geotech-webapp-buildplan.md` (the build plan)
   - Your original Excel workbooks (`WORKING_Lab_data_Interpretation.xlsx`, `Report_Graphs.xlsx`, etc.) and a handful of sample PDFs
3. Open Claude Code in this folder (`cd geotech-webapp && claude`, or open it via the Desktop app).

## Give it a CLAUDE.md (do this before your first real task)

This is a file Claude Code reads automatically at the start of every session — think of it as standing instructions so you don't re-explain the project every time. Create `CLAUDE.md` in the project root (you can literally ask Claude Code to do this for you: type `/init` and it'll draft one by reading your folder). Then edit it to include something like:

```markdown
# Geotech Lab Data & Borehole Log Interpretation App

## What this is
A web app for uploading geotechnical lab test PDFs (Macquarie Geotech format)
and borehole logs, auto-extracting results, generating the same charts as our
Excel workbook, and eventually auto-commenting on borehole logs.

## Reference materials (read these first)
- reference/geotech-webapp-buildplan.md — architecture and build order
- reference/parse_reports.py — working prototype parser for Emerson, PSD,
  and Atterberg reports, validated against real PDFs. Extend this pattern
  for other report types rather than rewriting from scratch.
- reference/*.xlsx — the manual workbook this app should replicate

## Stack
- Backend: Python (FastAPI), pdfplumber for PDF parsing
- Frontend: React/Next.js, Recharts or Plotly for charts
- DB: Postgres

## Conventions
- One parser module per report type, dispatched by report title text
- Always show the user a "here's what we extracted" review step before
  saving to the database — never silently trust an OCR/parse result
```

Keep it fairly short — this loads every session.

## Your first actual prompt

Once CLAUDE.md is in place, a good first ask is something narrow, not "build the whole thing":

> Read reference/geotech-webapp-buildplan.md and reference/parse_reports.py. Set up the project skeleton: a FastAPI backend and a React frontend, per the architecture in the build plan. Port parse_reports.py's Emerson/PSD/Atterberg logic into proper backend parser modules. Don't build the frontend charts yet — just get a `/upload` endpoint working that accepts a PDF and returns the parsed JSON.

Then keep going in small, checkable steps (add the CBR parser next, then the upload UI, then charts) rather than one giant request — that's how you stay able to review what it did.

## What to expect while it works

- It'll ask permission before running certain commands (installing packages, running shell commands) unless you've set a permission mode that allows it — starting cautious is fine for your first project.
- It edits files directly; review the diffs it shows you.
- If it does something wrong and you correct it, tell it to add a note to CLAUDE.md so it doesn't repeat the mistake — this is how the file becomes more useful over time.
- Use git. Ask it to commit as it completes each working step, so you can always roll back.

## If you get stuck

- `/help` inside a Claude Code session lists commands
- Official docs: https://code.claude.com/docs/en/overview
- Troubleshooting: https://code.claude.com/docs/en/troubleshoot-install
