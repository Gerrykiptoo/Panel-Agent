"""Web app for the Panel Question Agent.

Run it once, then use everything in your browser:

    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from panel_agent import PanelAgent

load_dotenv()

st.set_page_config(page_title="Panel Question Agent", page_icon="🎙", layout="centered")

st.title("🎙 Panel Question Agent")
st.caption("Professional, unique, human-centered questions for any panel — powered by Gemini.")


@st.cache_resource(show_spinner=False)
def get_agent() -> PanelAgent | None:
    """Create the agent once and reuse it. Returns None if no API key."""
    try:
        return PanelAgent()
    except ValueError:
        return None


agent = get_agent()
if agent is None:
    st.error(
        "No Gemini API key found. Add `GEMINI_API_KEY=...` to your `.env` file, "
        "then refresh this page."
    )
    st.stop()

# --- Inputs -------------------------------------------------------------------

topic = st.text_input(
    "Panel topic / title",
    placeholder="e.g. Mental health and wellness panel",
)

context = st.text_input(
    "Audience / context (optional)",
    value="A general, thoughtful public audience.",
    help="Who is in the room? This steers the tone.",
)

style = st.radio(
    "Output style",
    ["Flat numbered list", "Grouped by theme"],
    horizontal=True,
    help="Flat list = a clean moderator's sheet. Grouped = organized into themed sections.",
)

with st.expander("✨ Match a style (optional) — paste example questions"):
    examples_text = st.text_area(
        "Example questions",
        placeholder="Paste a few questions whose tone you want the agent to match,\none per line.",
        height=140,
    )

col1, col2 = st.columns(2)
if style == "Flat numbered list":
    num_questions = col1.slider("How many questions?", 3, 20, 10)
    temperature = col2.slider("Creativity", 0.0, 1.0, 0.9, 0.05)
    num_themes = per_theme = None
else:
    num_themes = col1.slider("Number of themes", 2, 8, 4)
    per_theme = col2.slider("Questions per theme", 1, 6, 3)
    temperature = st.slider("Creativity", 0.0, 1.0, 0.9, 0.05)
    num_questions = None

generate = st.button("Generate questions", type="primary", use_container_width=True)

# --- Generate & display -------------------------------------------------------


def build_markdown_flat(result) -> str:
    lines = [f"# {result.title}\n"]
    for i, q in enumerate(result.questions, start=1):
        note = f"  _({q.note})_" if q.note else ""
        lines.append(f"{i}. {q.question}{note}")
    return "\n".join(lines)


def build_markdown_grouped(result) -> str:
    lines = [f"# {result.topic}\n"]
    for t_i, theme in enumerate(result.themes, start=1):
        lines.append(f"\n## {t_i}. {theme.theme}\n")
        for q_i, q in enumerate(theme.questions, start=1):
            lines.append(f"{t_i}.{q_i}. **{q.question}**")
            lines.append(f"   - _{q.angle}_\n")
    return "\n".join(lines)


if generate:
    if not topic.strip():
        st.warning("Please enter a panel topic first.")
        st.stop()

    examples = [ln.strip() for ln in examples_text.splitlines() if ln.strip()]

    with st.spinner("Thinking up brilliant questions..."):
        try:
            if style == "Flat numbered list":
                result = agent.generate_list(
                    topic=topic.strip(),
                    num_questions=num_questions,
                    context=context.strip(),
                    examples=examples or None,
                    temperature=temperature,
                )
                md = build_markdown_flat(result)
                st.subheader(result.title)
                for i, q in enumerate(result.questions, start=1):
                    st.markdown(f"**{i}.** {q.question}")
                    if q.note:
                        st.caption(f"📝 {q.note}")
            else:
                result = agent.generate(
                    topic=topic.strip(),
                    context=context.strip(),
                    num_themes=num_themes,
                    per_theme=per_theme,
                    temperature=temperature,
                )
                md = build_markdown_grouped(result)
                st.subheader(result.topic)
                for t_i, theme in enumerate(result.themes, start=1):
                    st.markdown(f"### {t_i}. {theme.theme}")
                    for q_i, q in enumerate(theme.questions, start=1):
                        st.markdown(f"**{t_i}.{q_i}** {q.question}")
                        st.caption(f"↳ {q.angle}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Generation failed: {exc}")
            st.stop()

    st.divider()
    st.download_button(
        "⬇️ Download as Markdown",
        data=md,
        file_name="panel_questions.md",
        mime="text/markdown",
        use_container_width=True,
    )
