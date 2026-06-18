# 🎙 Panel Question Agent

An AI agent that turns any **topic** into a set of **professional, unique, and
deeply human** questions for a panelist — grouped into themes that touch
different aspects of life. Built in Python on Google's **Gemini** model.

## Why it's good

- **Professional & stage-ready** — poised, open-ended questions, never generic.
- **Human at the core** — even technical topics circle back to real lives.
- **Multi-dimensional** — each set spans personal, ethical, societal, emotional,
  and future-facing angles.
- **Grouped by theme** — clean, organized output you can take straight to a stage.

## Setup

```bash
# 1. (optional but recommended) create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. install dependencies
pip install -r requirements.txt

# 3. add your Gemini API key
cp .env.example .env
#   then edit .env and paste your key (get one free at
#   https://aistudio.google.com/apikey)
```

## Usage

```bash
# Simplest — pass a topic
python main.py "The future of remote work"

# Ask interactively
python main.py

# Tune it
python main.py "Artificial intelligence in education" \
    --context "A conference of high-school teachers" \
    --themes 5 --per-theme 4 --temperature 0.95

# Save the result as Markdown
python main.py "Climate change" -o output/climate.md
```

### Options

| Flag | Meaning | Default |
|------|---------|---------|
| `-c, --context` | Audience / setting to steer the tone | general public |
| `-t, --themes` | Number of themes | 4 |
| `-q, --per-theme` | Questions per theme | 3 |
| `--temperature` | Creativity (0.0–1.0) | 0.9 |
| `-o, --out` | Also save to a Markdown file | — |

## Project structure

```
Agent/
├── main.py                 # entry point
├── panel_agent/
│   ├── agent.py            # core engine + Gemini call + output schema
│   ├── prompts.py          # the agent's "voice" (system + task prompts)
│   └── cli.py              # command-line interface & pretty output
├── requirements.txt
└── .env.example
```

## Use it as a library

```python
from panel_agent import PanelAgent

agent = PanelAgent()  # reads GEMINI_API_KEY from environment
result = agent.generate("The meaning of home", num_themes=3, per_theme=4)

for theme in result.themes:
    print(theme.theme)
    for q in theme.questions:
        print(" -", q.question)
```
