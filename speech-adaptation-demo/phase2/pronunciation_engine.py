from collections import Counter
from typing import Dict, List, Tuple

import phonetics

from analytics import tokenize
from .db import PronunciationPattern, get_session


class PronunciationMapper:
    def detect_pattern(self, asr_output: str, user_correction: str) -> List[Tuple[str, str, float]]:
        asr_tokens = tokenize(asr_output)
        cor_tokens = tokenize(user_correction)
        pairs = []
        for a, b in zip(asr_tokens, cor_tokens):
            if a == b:
                continue
            pa = phonetics.metaphone(a)
            pb = phonetics.metaphone(b)
            score = 1.0 if pa == pb else 0.5 if phonetics.soundex(a) == phonetics.soundex(b) else 0.2
            pairs.append((a, b, score))
        return pairs

    def build_pronunciation_map(self, user_id: str) -> Dict[str, Dict[str, float]]:
        session = get_session()
        try:
            rows = (
                session.query(PronunciationPattern)
                .filter(PronunciationPattern.user_id == user_id)
                .all()
            )
        finally:
            session.close()
        mapping: Dict[str, Dict[str, float]] = {}
        for r in rows:
            mapping.setdefault(r.user_variant, {})
            mapping[r.user_variant][r.standard_form] = r.confidence
        return mapping

    def apply_map_to_asr(self, asr_output: str, mapping: Dict[str, Dict[str, float]]) -> str:
        tokens = tokenize(asr_output)
        out = []
        for t in tokens:
            if t in mapping:
                best = max(mapping[t].items(), key=lambda kv: kv[1])[0]
                out.append(best)
            else:
                out.append(t)
        return " ".join(out)

    def suggest_vocabulary_boost(self, mapping: Dict[str, Dict[str, float]]) -> List[Dict]:
        boosts = []
        for variant, targets in mapping.items():
            for target, conf in targets.items():
                boosts.append({"word": target, "boost": min(3.0, 1.5 + conf)})
        return boosts

    def update_patterns(self, user_id: str, asr_output: str, user_correction: str):
        pairs = self.detect_pattern(asr_output, user_correction)
        session = get_session()
        try:
            for a, b, score in pairs:
                row = (
                    session.query(PronunciationPattern)
                    .filter(
                        PronunciationPattern.user_id == user_id,
                        PronunciationPattern.standard_form == b,
                        PronunciationPattern.user_variant == a,
                    )
                    .one_or_none()
                )
                if row:
                    row.occurrence_count += 1
                    row.confidence = min(1.0, (row.confidence + score) / 2)
                else:
                    session.add(
                        PronunciationPattern(
                            user_id=user_id,
                            standard_form=b,
                            user_variant=a,
                            confidence=score,
                            occurrence_count=1,
                        )
                    )
            session.commit()
        finally:
            session.close()

    def top_patterns(self, user_id: str, limit: int = 50):
        session = get_session()
        try:
            rows = (
                session.query(PronunciationPattern)
                .filter(PronunciationPattern.user_id == user_id)
                .order_by(PronunciationPattern.occurrence_count.desc())
                .limit(limit)
                .all()
            )
            return rows
        finally:
            session.close()


def pattern_summary(rows) -> Dict[str, int]:
    counter = Counter()
    for r in rows:
        key = f"{r.user_variant}->{r.standard_form}"
        counter[key] += r.occurrence_count
    return dict(counter)
