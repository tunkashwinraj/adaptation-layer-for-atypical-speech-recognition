import logging
from typing import Dict

from openai import OpenAI

from analytics import wer

# Optional: sentence-transformers + sklearn for semantic similarity
_SENTENCE_MODEL = None
_SEMSCORE_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    _SEMSCORE_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    cosine_similarity = None

LOG = logging.getLogger(__name__)


def _get_sentence_model():
    global _SENTENCE_MODEL
    if not _SEMSCORE_AVAILABLE or SentenceTransformer is None:
        return None
    if _SENTENCE_MODEL is None:
        _SENTENCE_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _SENTENCE_MODEL


def calculate_semscore(reference: str, hypothesis: str) -> float:
    """Semantic similarity 0–1. Returns token-overlap fallback if sentence_transformers unavailable."""
    if _SEMSCORE_AVAILABLE and cosine_similarity is not None:
        model = _get_sentence_model()
        if model is not None:
            ref_emb = model.encode(reference or "")
            hyp_emb = model.encode(hypothesis or "")
            return float(cosine_similarity([ref_emb], [hyp_emb])[0][0])
    # Fallback: simple token Jaccard so metrics_bundle still works
    ref_t = set((reference or "").lower().split())
    hyp_t = set((hypothesis or "").lower().split())
    if not ref_t:
        return 1.0
    return len(ref_t & hyp_t) / len(ref_t | hyp_t) if (ref_t or hyp_t) else 1.0


def calculate_lattescore(asr_output: str, ground_truth: str, task_context: str) -> float:
    client = OpenAI()
    prompt = (
        f"Task: {task_context}\n"
        f"Expected: {ground_truth}\n"
        f"ASR Output: {asr_output}\n"
        "Can the task succeed? Score 0.0-1.0:"
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=10,
    )
    content = response.choices[0].message.content.strip()
    try:
        return float(content)
    except ValueError:
        return 0.0


def task_success_rate(asr_output: str, ground_truth: str) -> float:
    # Simple success based on WER threshold
    w = wer(ground_truth, asr_output)
    if w is None:
        return 0.0
    return 1.0 if w <= 0.2 else 0.0


def meaning_error_rate(reference: str, hypothesis: str) -> float:
    # Approximate MER by entity/action token overlap
    ref_tokens = reference.lower().split()
    hyp_tokens = hypothesis.lower().split()
    if not ref_tokens:
        return 0.0
    # Consider content tokens (simple heuristic: length > 3)
    ref_content = [t for t in ref_tokens if len(t) > 3]
    hyp_content = [t for t in hyp_tokens if len(t) > 3]
    if not ref_content:
        return 0.0
    mismatches = sum(1 for t in ref_content if t not in hyp_content)
    return mismatches / max(1, len(ref_content))


def metrics_bundle(reference: str, hypothesis: str, task_context: str = "") -> Dict:
    return {
        "semscore": calculate_semscore(reference, hypothesis),
        "task_success_rate": task_success_rate(hypothesis, reference),
        "mer": meaning_error_rate(reference, hypothesis),
        "lattescore": calculate_lattescore(hypothesis, reference, task_context) if task_context else None,
    }
