import math
from collections import Counter
from datetime import datetime
from typing import Dict, List

from .db import Correction, Vocabulary, get_session
from analytics import tokenize, wer


class CorrectionManager:
    def add_correction(self, user_id: str, audio_path: str, asr_baseline: str,
                       asr_personalized: str, user_correction: str, context: str):
        session = get_session()
        try:
            entry = Correction(
                user_id=user_id,
                audio_path=audio_path,
                asr_baseline=asr_baseline,
                asr_personalized=asr_personalized,
                user_correction=user_correction,
                context=context or "",
            )
            session.add(entry)
            session.commit()
        finally:
            session.close()

    def get_correction_history(self, user_id: str, limit: int = 50) -> List[Correction]:
        session = get_session()
        try:
            return (
                session.query(Correction)
                .filter(Correction.user_id == user_id)
                .order_by(Correction.timestamp.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    def analyze_patterns(self, user_id: str) -> Dict[str, int]:
        session = get_session()
        try:
            rows = session.query(Correction).filter(Correction.user_id == user_id).all()
        finally:
            session.close()

        confusion = Counter()
        for r in rows:
            asr_tokens = tokenize(r.asr_personalized or r.asr_baseline or "")
            cor_tokens = tokenize(r.user_correction or "")
            for a, b in zip(asr_tokens, cor_tokens):
                if a != b:
                    confusion[(a, b)] += 1
        return {f"{a}->{b}": c for (a, b), c in confusion.most_common(50)}

    def update_vocabulary(self, user_id: str):
        session = get_session()
        try:
            rows = session.query(Correction).filter(Correction.user_id == user_id).all()
            vocab_counter = Counter()
            for r in rows:
                vocab_counter.update(tokenize(r.user_correction or ""))

            for word, freq in vocab_counter.items():
                row = (
                    session.query(Vocabulary)
                    .filter(Vocabulary.user_id == user_id, Vocabulary.word == word)
                    .one_or_none()
                )
                boost = min(3.0, 1.2 + math.log(1 + freq))
                if row:
                    row.frequency = freq
                    row.boost_value = boost
                    row.last_used = datetime.utcnow()
                else:
                    session.add(
                        Vocabulary(
                            user_id=user_id,
                            word=word,
                            boost_value=boost,
                            frequency=freq,
                            last_used=datetime.utcnow(),
                        )
                    )
            session.commit()
        finally:
            session.close()

    def calculate_learning_velocity(self, user_id: str) -> float:
        session = get_session()
        try:
            rows = (
                session.query(Correction)
                .filter(Correction.user_id == user_id)
                .order_by(Correction.timestamp.asc())
                .all()
            )
        finally:
            session.close()

        if len(rows) < 2:
            return 0.0

        wers = []
        for r in rows:
            if r.user_correction and r.asr_personalized:
                w = wer(r.user_correction, r.asr_personalized)
                if w is not None:
                    wers.append(w)
        if len(wers) < 2:
            return 0.0
        return wers[0] - wers[-1]


class LearningMetrics:
    @staticmethod
    def calculate_learning_velocity(corrections_over_time: List[Dict]) -> float:
        if len(corrections_over_time) < 2:
            return 0.0
        start = corrections_over_time[0].get("wer", 0.0)
        end = corrections_over_time[-1].get("wer", 0.0)
        return start - end

    @staticmethod
    def predict_convergence(current_wer: float, velocity: float, target: float = 0.1):
        if velocity <= 0:
            return None
        remaining = max(0.0, current_wer - target)
        return remaining / velocity

    @staticmethod
    def measure_vocabulary_impact(baseline_wer: float, personalized_wer: float) -> float:
        if baseline_wer is None or personalized_wer is None:
            return 0.0
        return max(0.0, baseline_wer - personalized_wer)
