import re
from collections import Counter
from typing import Dict, List, Tuple


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> List[str]:
    return normalize_text(text).split()


def levenshtein(a: List[str], b: List[str]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev = dp[0]
        dp[0] = i
        for j, cb in enumerate(b, 1):
            cur = dp[j]
            if ca == cb:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j - 1], dp[j])
            prev = cur
    return dp[-1]


def wer(ref: str, hyp: str):
    ref_tokens = tokenize(ref)
    hyp_tokens = tokenize(hyp)
    if not ref_tokens:
        return None
    return levenshtein(ref_tokens, hyp_tokens) / max(1, len(ref_tokens))


def cer(ref: str, hyp: str):
    ref_chars = list(normalize_text(ref).replace(" ", ""))
    hyp_chars = list(normalize_text(hyp).replace(" ", ""))
    if not ref_chars:
        return None
    return levenshtein(ref_chars, hyp_chars) / max(1, len(ref_chars))


def jaccard_similarity(a: str, b: str) -> float:
    ta = set(tokenize(a))
    tb = set(tokenize(b))
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def cosine_similarity(a: str, b: str) -> float:
    ta = tokenize(a)
    tb = tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    ca = Counter(ta)
    cb = Counter(tb)
    all_keys = set(ca) | set(cb)
    dot = sum(ca[k] * cb[k] for k in all_keys)
    na = sum(v * v for v in ca.values()) ** 0.5
    nb = sum(v * v for v in cb.values()) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def token_overlap_ratio(a: str, b: str) -> float:
    ta = tokenize(a)
    tb = tokenize(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    common = sum((Counter(ta) & Counter(tb)).values())
    total = max(1, max(len(ta), len(tb)))
    return common / total


def diff_ops(a: str, b: str) -> Tuple[Dict[str, int], List[Tuple[str, str]]]:
    a_tokens = tokenize(a)
    b_tokens = tokenize(b)
    # Simple alignment via SequenceMatcher opcodes on tokens.
    import difflib

    matcher = difflib.SequenceMatcher(a=a_tokens, b=b_tokens)
    counts = {"insert": 0, "delete": 0, "replace": 0}
    replacements: List[Tuple[str, str]] = []
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        if op == "insert":
            counts["insert"] += (b1 - b0)
        elif op == "delete":
            counts["delete"] += (a1 - a0)
        elif op == "replace":
            counts["replace"] += max(a1 - a0, b1 - b0)
            a_chunk = a_tokens[a0:a1]
            b_chunk = b_tokens[b0:b1]
            for i in range(min(len(a_chunk), len(b_chunk))):
                replacements.append((a_chunk[i], b_chunk[i]))
    return counts, replacements


def confidence_stats(word_timings: List[dict], low_threshold: float = 0.6) -> Dict[str, float]:
    if not word_timings:
        return {
            "avg_conf": None,
            "min_conf": None,
            "low_conf_count": 0,
            "low_conf_ratio": None,
        }
    confs = [w.get("confidence", 0.0) for w in word_timings]
    low_count = sum(1 for c in confs if c is not None and c < low_threshold)
    return {
        "avg_conf": sum(confs) / max(1, len(confs)),
        "min_conf": min(confs) if confs else None,
        "low_conf_count": low_count,
        "low_conf_ratio": low_count / max(1, len(confs)),
    }


def timing_stats(word_timings: List[dict], pause_threshold: float = 0.5) -> Dict[str, float]:
    if not word_timings:
        return {
            "duration_sec": None,
            "words": 0,
            "words_per_sec": None,
            "pause_count": 0,
            "avg_pause_sec": None,
        }
    words = len(word_timings)
    starts = [w.get("start", 0.0) for w in word_timings]
    ends = [w.get("end", 0.0) for w in word_timings]
    duration = max(0.0, max(ends) - min(starts)) if words else 0.0
    pauses = []
    for i in range(1, words):
        gap = max(0.0, starts[i] - ends[i - 1])
        if gap >= pause_threshold:
            pauses.append(gap)
    return {
        "duration_sec": duration,
        "words": words,
        "words_per_sec": (words / duration) if duration > 0 else None,
        "pause_count": len(pauses),
        "avg_pause_sec": (sum(pauses) / len(pauses)) if pauses else None,
    }


def count_syllables(word: str) -> int:
    word = word.lower()
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def readability_stats(text: str) -> Dict[str, float]:
    text = text or ""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    words = tokenize(text)
    syllables = sum(count_syllables(w) for w in words)
    num_sentences = max(1, len(sentences))
    num_words = max(1, len(words))
    wps = num_words / num_sentences
    syl_per_word = syllables / num_words if num_words else 0

    # Flesch Reading Ease and Flesch-Kincaid Grade
    fre = 206.835 - (1.015 * wps) - (84.6 * syl_per_word)
    fk = (0.39 * wps) + (11.8 * syl_per_word) - 15.59
    return {
        "sentences": num_sentences,
        "words": len(words),
        "syllables": syllables,
        "flesch_reading_ease": fre,
        "flesch_kincaid_grade": fk,
    }


def grammar_flags(text: str) -> Dict[str, int]:
    text = text or ""
    tokens = tokenize(text)
    repeats = 0
    for i in range(1, len(tokens)):
        if tokens[i] == tokens[i - 1]:
            repeats += 1
    long_sentence = 0
    for s in re.split(r"[.!?]+", text):
        if len(tokenize(s)) >= 30:
            long_sentence += 1
    double_space = 1 if "  " in text else 0
    return {
        "repeated_words": repeats,
        "long_sentences": long_sentence,
        "double_space": double_space,
    }

