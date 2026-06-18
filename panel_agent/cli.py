"""Command-line interface for the panel question agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule

from .agent import PanelAgent, PanelQuestions, RefinedSet

console = Console()


def render(result: PanelQuestions) -> None:
    """Pretty-print the questions, grouped by theme, to the terminal."""
    console.print()
    console.print(
        Panel(
            f"[bold]{result.topic}[/bold]",
            title="🎙  Panel Questions",
            border_style="cyan",
        )
    )
    for t_index, theme in enumerate(result.themes, start=1):
        console.print()
        console.print(Rule(f"[bold magenta]{t_index}. {theme.theme}[/bold magenta]"))
        for q_index, q in enumerate(theme.questions, start=1):
            console.print(f"\n  [bold cyan]{t_index}.{q_index}[/bold cyan]  {q.question}")
            console.print(f"       [dim italic]↳ {q.angle}[/dim italic]")
    console.print()


def to_markdown(result: PanelQuestions) -> str:
    """Convert the result into a Markdown document for saving/sharing."""
    lines = [f"# Panel Questions — {result.topic}\n"]
    for t_index, theme in enumerate(result.themes, start=1):
        lines.append(f"\n## {t_index}. {theme.theme}\n")
        for q_index, q in enumerate(theme.questions, start=1):
            lines.append(f"{t_index}.{q_index}. **{q.question}**")
            lines.append(f"   - _{q.angle}_\n")
    return "\n".join(lines)


def render_refined(result: RefinedSet) -> None:
    """Pretty-print refined questions: original -> refined + note."""
    console.print()
    console.print(Panel("[bold]Refined questions[/bold]", title="✨ Refined", border_style="cyan"))
    for i, item in enumerate(result.questions, start=1):
        console.print()
        console.print(Rule(f"[bold magenta]{i}[/bold magenta]"))
        console.print(f"  [dim]Original:[/dim] {item.original}")
        console.print(f"  [bold cyan]Refined :[/bold cyan] {item.refined}")
        console.print(f"  [dim italic]↳ {item.note}[/dim italic]")
    console.print()


def run_refine(args, agent: PanelAgent) -> int:
    """Handle the 'refine' subcommand: improve draft questions the user's way."""
    if args.infile:
        raw = Path(args.infile).read_text(encoding="utf-8")
        questions = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    elif args.questions:
        questions = [q.strip() for q in args.questions if q.strip()]
    else:
        console.print("[cyan]Paste your draft questions, one per line. Blank line to finish:[/cyan]")
        questions = []
        while True:
            line = console.input()
            if not line.strip():
                break
            questions.append(line.strip())

    if not questions:
        console.print("[red]No questions to refine.[/red]")
        return 1

    instructions = args.how
    if not instructions:
        instructions = Prompt.ask(
            "[bold cyan]How should I refine them?[/bold cyan] (e.g. 'shorter and more provocative')"
        )

    with console.status("[cyan]Refining your questions...[/cyan]", spinner="dots"):
        try:
            result = agent.refine(questions, instructions, temperature=args.temperature)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Refine failed:[/red] {exc}")
            return 1

    render_refined(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    # "refine" mode is opt-in; everything else stays the simple `main.py "topic"`.
    raw_argv = sys.argv[1:] if argv is None else argv
    if raw_argv and raw_argv[0] == "refine":
        rp = argparse.ArgumentParser(prog="main.py refine",
                                     description="Refine draft questions your way.")
        rp.add_argument("questions", nargs="*", help="Draft questions (quote each).")
        rp.add_argument("-i", "--infile", metavar="FILE",
                        help="Read draft questions from a file (one per line).")
        rp.add_argument("--how", help="Instructions for how to refine them.")
        rp.add_argument("--temperature", type=float, default=0.8, help="Creativity 0.0-1.0.")
        rargs = rp.parse_args(raw_argv[1:])
        try:
            agent = PanelAgent()
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            return 1
        return run_refine(rargs, agent)

    parser = argparse.ArgumentParser(
        description="Generate professional, theme-grouped panel questions with Gemini."
    )
    parser.add_argument("topic", nargs="*", help="The panel topic (asked interactively if omitted).")
    parser.add_argument("-c", "--context", default="A general, thoughtful public audience.",
                        help="Audience/setting to steer the tone.")
    parser.add_argument("-t", "--themes", type=int, default=4, help="Number of themes (default: 4).")
    parser.add_argument("-q", "--per-theme", type=int, default=3,
                        help="Questions per theme (default: 3).")
    parser.add_argument("--temperature", type=float, default=0.9,
                        help="Creativity 0.0-1.0 (default: 0.9).")
    parser.add_argument("-o", "--out", metavar="FILE",
                        help="Also save the questions to a Markdown file.")
    args = parser.parse_args(argv)

    topic = " ".join(args.topic).strip()
    if not topic:
        topic = Prompt.ask("[bold cyan]What is the panel topic?[/bold cyan]").strip()
    if not topic:
        console.print("[red]No topic given. Nothing to do.[/red]")
        return 1

    try:
        agent = PanelAgent()
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    with console.status("[cyan]Thinking up brilliant questions...[/cyan]", spinner="dots"):
        try:
            result = agent.generate(
                topic=topic,
                context=args.context,
                num_themes=args.themes,
                per_theme=args.per_theme,
                temperature=args.temperature,
            )
        except Exception as exc:  # noqa: BLE001 - surface any API error cleanly
            console.print(f"[red]Generation failed:[/red] {exc}")
            return 1

    render(result)

    if args.out:
        path = Path(args.out)
        path.write_text(to_markdown(result), encoding="utf-8")
        console.print(f"[green]Saved to[/green] {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
