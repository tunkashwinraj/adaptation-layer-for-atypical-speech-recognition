import logging
from typing import Optional

from openai import OpenAI

LOGGER = logging.getLogger(__name__)


PROMPT_TEMPLATE = """You are an expert speech recognition error correction system. Your task is to correct ASR transcription errors while preserving the speaker's intended meaning.

CONTEXT: The speaker may have atypical speech patterns due to dysarthria, stroke, or other conditions. Common errors include:
- Medication names misheard (e.g., "Atorvastatin" -> "a tour of a station")
- Proper nouns confused (e.g., "Calgary" -> "cal gary")
- Technical terms misrecognized
- Word boundary errors
- Grammatical inconsistencies due to speech patterns

DOMAIN HINTS: {context_hints}

ASR TRANSCRIPT TO CORRECT:
{asr_transcript}

INSTRUCTIONS:
1. Identify obvious misrecognitions based on context
2. Correct errors while preserving exact meaning
3. Maintain the original sentence structure where possible
4. Fix grammatical issues caused by speech recognition errors
5. Return ONLY the corrected transcript, no explanations

CORRECTED TRANSCRIPT:
"""


def semantic_repair(asr_transcript: str, context_hints: Optional[str], model: str = "gpt-4") -> str:
    if not asr_transcript:
        return ""

    client = OpenAI()
    prompt = PROMPT_TEMPLATE.format(
        context_hints=context_hints or "No extra hints provided.",
        asr_transcript=asr_transcript,
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You correct ASR errors with high precision."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=500,
            top_p=0.9,
        )
        corrected = response.choices[0].message.content.strip()
        return corrected
    except Exception as exc:
        LOGGER.exception("OpenAI semantic repair failed: %s", exc)
        raise RuntimeError(f"OpenAI semantic repair failed: {exc}") from exc
