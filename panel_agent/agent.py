"""Core engine: turns a topic into professional, theme-grouped panel questions."""

from __future__ import annotations

import os
import time

from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field

from .prompts import (
    FLAT_LIST_PROMPT,
    GENERATION_PROMPT,
    REFINE_PROMPT,
    SYSTEM_INSTRUCTION,
)

DEFAULT_MODEL = "gemini-2.5-flash"


# --- Structured output schema -------------------------------------------------
# Gemini fills these models directly, so we get reliable, grouped data
# instead of having to parse free-form text.


class Question(BaseModel):
    question: str = Field(description="The polished, open-ended panel question.")
    angle: str = Field(
        description="One sentence on why it is powerful and which aspect of human life it opens."
    )


class Theme(BaseModel):
    theme: str = Field(description="Short title for this group of questions.")
    questions: list[Question]


class PanelQuestions(BaseModel):
    topic: str
    themes: list[Theme]


class FlatQuestion(BaseModel):
    question: str = Field(description="A clear, direct, open-ended panel question.")
    note: str = Field(
        default="",
        description="Optional short moderator note (e.g. 'ask a man this'). Empty if none.",
    )


class PanelList(BaseModel):
    title: str = Field(description="The panel title.")
    questions: list[FlatQuestion]


class RefinedQuestion(BaseModel):
    original: str = Field(description="The user's original draft question.")
    refined: str = Field(description="The improved version of the question.")
    note: str = Field(description="Short note on what was changed and why.")


class RefinedSet(BaseModel):
    questions: list[RefinedQuestion]


class PanelAgent:
    """Generates panel questions for a given topic using Google Gemini."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "No API key found. Set GEMINI_API_KEY in your .env file "
                "or pass api_key=... to PanelAgent()."
            )
        self.client = genai.Client(api_key=key)
        self.model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL

    def _generate_content(self, *, contents: str, config, attempts: int = 4):
        """Call Gemini, retrying transient overload errors (503/429) with backoff."""
        delay = 2.0
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return self.client.models.generate_content(
                    model=self.model, contents=contents, config=config
                )
            except genai_errors.APIError as exc:
                # Retry only on transient errors; re-raise real problems immediately.
                if getattr(exc, "code", None) in (429, 500, 503) and attempt < attempts - 1:
                    last_exc = exc
                    time.sleep(delay)
                    delay *= 2  # exponential backoff
                    continue
                raise
        if last_exc:  # pragma: no cover - safety net
            raise last_exc

    def generate(
        self,
        topic: str,
        context: str = "A general, thoughtful public audience.",
        num_themes: int = 4,
        per_theme: int = 3,
        temperature: float = 0.9,
    ) -> PanelQuestions:
        """Generate theme-grouped panel questions for ``topic``.

        Args:
            topic: The subject of the panel.
            context: Who the audience is / the setting (steers tone).
            num_themes: How many distinct life-angle themes to produce.
            per_theme: How many questions per theme.
            temperature: Higher = more creative/varied questions.
        """
        prompt = GENERATION_PROMPT.format(
            topic=topic,
            context=context,
            num_themes=num_themes,
            per_theme=per_theme,
        )

        response = self._generate_content(
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=PanelQuestions,
            ),
        )

        # The SDK parses the JSON into our Pydantic model for us.
        result = response.parsed
        if result is None:  # pragma: no cover - defensive fallback
            result = PanelQuestions.model_validate_json(response.text)
        if not result.topic:
            result.topic = topic
        return result

    def generate_list(
        self,
        topic: str,
        num_questions: int = 10,
        context: str = "A general, thoughtful public audience.",
        examples: list[str] | None = None,
        temperature: float = 0.9,
    ) -> PanelList:
        """Generate a flat, numbered list of clear panel questions.

        Args:
            topic: The panel title / subject.
            num_questions: How many questions to produce.
            context: Who the audience is / the setting.
            examples: Optional sample questions to match in style/tone.
            temperature: Higher = more creative/varied questions.
        """
        examples_block = ""
        if examples:
            joined = "\n".join(f"- {e}" for e in examples if e.strip())
            if joined:
                examples_block = (
                    "\nMATCH THE STYLE AND TONE of these example questions "
                    "(write new ones in the same spirit, do not copy them):\n"
                    f"{joined}\n"
                )

        prompt = FLAT_LIST_PROMPT.format(
            topic=topic,
            context=context,
            num_questions=num_questions,
            examples_block=examples_block,
        )

        response = self._generate_content(
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=PanelList,
            ),
        )

        result = response.parsed
        if result is None:  # pragma: no cover - defensive fallback
            result = PanelList.model_validate_json(response.text)
        if not result.title:
            result.title = topic
        return result

    def refine(
        self,
        questions: list[str],
        instructions: str,
        temperature: float = 0.8,
    ) -> RefinedSet:
        """Refine draft ``questions`` according to the user's ``instructions``.

        Args:
            questions: The draft questions to improve.
            instructions: How the user wants them refined (their own words).
            temperature: Higher = more creative rewriting.
        """
        numbered = "\n".join(f"{i}. {q}" for i, q in enumerate(questions, start=1))
        prompt = REFINE_PROMPT.format(instructions=instructions, questions=numbered)

        response = self._generate_content(
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=RefinedSet,
            ),
        )

        result = response.parsed
        if result is None:  # pragma: no cover - defensive fallback
            result = RefinedSet.model_validate_json(response.text)
        return result
