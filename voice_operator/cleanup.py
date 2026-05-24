from __future__ import annotations

import asyncio
import logging

from claude_agent_sdk import query, ClaudeAgentOptions

from voice_operator.context import AppContext

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5"
# The Agent SDK spawns the claude CLI; allow more headroom than a raw API call.
# Fail-soft (return raw transcript) if cleanup exceeds this.
TIMEOUT_SECONDS = 10.0

BUNDLED_PROMPT = """You are a dictation cleanup assistant. The user spoke into a voice \
dictation tool; you receive the raw speech-to-text transcript. Your job is to return \
ONLY the cleaned text the user intended to type.

Rules - apply ALL of them:
  1. Remove filler words: um, uh, er, like (when used as filler), you know, I mean, \
sort of (when used as filler).
  2. Add correct punctuation and capitalization. Break into sentences and paragraphs \
where natural.
  3. Resolve self-corrections. If the user said something then corrected themselves, \
keep only the corrected version.
     Examples:
       "meet Tuesday - wait, Wednesday"  -> "meet Wednesday"
       "send to John, no, send to Sarah" -> "send to Sarah"
  4. Fix obvious STT errors using surrounding context (e.g. "right" vs "write").
  5. Lightly adapt tone to the active app:
       - Slack / Discord / Teams / iMessage  -> casual, no greetings
       - Gmail / Outlook                     -> polite, complete sentences
       - VS Code / Cursor / IDE / terminal   -> terse, technical, preserve identifiers verbatim
       - Other / unknown                     -> neutral, preserve verbatim
  6. NEVER add information the user did not say.
  7. NEVER reorganize or summarize. Only clean.
  8. If the user gives an explicit formatting instruction inline ("...new paragraph...", \
"...bullet list..."), apply it and remove the instruction from the output.
  9. Preserve emojis, proper nouns, and code/identifiers exactly.
 10. Output ONLY the cleaned text. No preface, no quotes, no explanation."""


def build_system_prompt(ctx: AppContext, override: str | None) -> str:
    body = override if override else BUNDLED_PROMPT
    return f"{body}\n\nActive app: {ctx.app_name}\nWindow title: {ctx.window_title}"


def _extract_text(message) -> str:
    """Pull text from an Agent SDK message; tolerant of block-shape differences."""
    content = getattr(message, "content", None)
    if not content:
        return ""
    parts = []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)


async def polish(
    raw_text: str,
    ctx: AppContext,
    *,
    model: str | None = None,
    override: str | None = None,
) -> str:
    """Clean a raw transcript with Claude on the Max subscription (Agent SDK).

    Each call is an independent single-turn query (no conversation carryover).
    On any failure or timeout, return raw_text unchanged (fail-soft)."""
    raw_text = raw_text.strip()
    if not raw_text:
        return ""
    options = ClaudeAgentOptions(
        system_prompt=build_system_prompt(ctx, override),
        allowed_tools=[],                 # pure text in/out; no agentic behavior
        max_turns=1,
        model=model or DEFAULT_MODEL,
        permission_mode="bypassPermissions",  # fully unattended; never prompt
    )
    collected: list[str] = []

    async def _run() -> None:
        async for message in query(prompt=raw_text, options=options):
            collected.append(_extract_text(message))

    try:
        await asyncio.wait_for(_run(), timeout=TIMEOUT_SECONDS)
    except Exception as exc:  # fail-soft (includes asyncio.TimeoutError)
        log.warning("cleanup failed (%s); using raw transcript", exc)
        return raw_text
    cleaned = "".join(collected).strip()
    return cleaned or raw_text
