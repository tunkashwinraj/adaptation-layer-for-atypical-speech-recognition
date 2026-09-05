from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from .db import Correction, Session, InteractionEvent, get_session


class AdaptiveInteractionManager:
    """
    Phase 3: real frustration detection based on actual logged data.

    Signals are derived from:
    - Number of corrections for the user
    - Repeated errors (same corrected phrase appearing multiple times)
    - Rapid retries (sessions within a short time window)
    - WER / MER trend over recent sessions
    """

    def _load_user_history(self, user_id: str) -> Tuple[List[Correction], List[Session]]:
        db = get_session()
        try:
            corrections = (
                db.query(Correction)
                .filter(Correction.user_id == user_id)
                .order_by(Correction.timestamp.asc())
                .all()
            )
            sessions = (
                db.query(Session)
                .filter(Session.user_id == user_id)
                .order_by(Session.start_time.asc())
                .all()
            )
        finally:
            db.close()
        return corrections, sessions

    def _compute_signals(self, user_id: str, current_metric: float | None) -> Dict:
        corrections, sessions = self._load_user_history(user_id)

        # Corrections-based signals
        correction_count = len(corrections)
        corrected_phrases = [c.user_correction.lower().strip() for c in corrections if c.user_correction]
        total_errors = len(corrected_phrases)
        unique_errors = len(set(corrected_phrases)) if corrected_phrases else 0
        repeated_errors = 1 if total_errors > unique_errors and total_errors >= 3 else 0

        # Retry timing: count consecutive sessions within 5 seconds
        rapid_retries = 0
        for prev, nxt in zip(sessions, sessions[1:]):
            if prev.end_time and nxt.start_time:
                if (nxt.start_time - prev.end_time) <= timedelta(seconds=5):
                    rapid_retries += 1

        # WER / MER trend (stored in metrics as "wer" or "mer")
        wer_history: List[float] = []
        for s in sessions:
            metrics = s.metrics or {}
            if "wer" in metrics and metrics["wer"] is not None:
                wer_history.append(float(metrics["wer"]))
            elif "mer" in metrics and metrics["mer"] is not None:
                wer_history.append(float(metrics["mer"]))
        if current_metric is not None:
            wer_history.append(float(current_metric))

        wer_increasing = 0
        if len(wer_history) >= 2 and wer_history[-1] > wer_history[0]:
            wer_increasing = 1

        return {
            "correction_count": correction_count,
            "total_errors": total_errors,
            "unique_errors": unique_errors,
            "repeated_errors": repeated_errors,
            "rapid_retries": rapid_retries,
            "wer_history": wer_history,
            "wer_increasing": wer_increasing,
        }

    def detect_frustration(self, session_data: Dict) -> Dict:
        """
        Entry point used from the Gradio app.

        Expected keys in session_data:
        - user_id: current profile/user id (required for DB lookups)
        - current_metric: latest WER / MER value (optional)
        """
        user_id = session_data.get("user_id")
        current_metric = session_data.get("current_metric")

        if not user_id:
            signals = {
                "correction_count": 0,
                "total_errors": 0,
                "unique_errors": 0,
                "repeated_errors": 0,
                "rapid_retries": 0,
                "wer_history": [],
                "wer_increasing": 0,
            }
        else:
            signals = self._compute_signals(user_id, current_metric)

        score = self.calculate_frustration_score(signals)
        mode = self.select_interaction_mode(score)

        # Persist interaction event for later analysis
        self._record_interaction_event(
            session_data.get("session_id"), score, mode, signals
        )

        return {"score": score, "mode": mode, "signals": signals}

    def calculate_frustration_score(self, signals: Dict) -> float:
        """
        Simplified formula from the Phase 3 spec:

        frustration = (
            (correction_count > 2) * 0.3 +
            (unique_errors < total_errors) * 0.3 +
            (rapid_retries > 0) * 0.2 +
            (wer_increasing) * 0.2
        )
        """
        correction_count = signals.get("correction_count", 0)
        total_errors = signals.get("total_errors", 0)
        unique_errors = signals.get("unique_errors", 0)
        rapid_retries = signals.get("rapid_retries", 0)
        wer_increasing = signals.get("wer_increasing", 0)

        frustration = (
            (1 if correction_count > 2 else 0) * 0.3
            + (1 if unique_errors < total_errors and total_errors > 0 else 0) * 0.3
            + (1 if rapid_retries > 0 else 0) * 0.2
            + (1 if wer_increasing else 0) * 0.2
        )

        return float(min(frustration, 1.0))

    def select_interaction_mode(self, frustration_score: float) -> str:
        if frustration_score >= 0.7:
            return "CONFLICT"
        if frustration_score >= 0.4:
            return "EXPLORATION"
        return "INTEGRATION"

    def generate_adaptive_response(self, mode: str, context: str | None = None) -> str:
        if mode == "CONFLICT":
            return "I may have missed something. Let's confirm one step at a time."
        if mode == "EXPLORATION":
            return "I can try a different interpretation. Want to rephrase or add more context?"
        return "Got it. Proceeding with the updated transcript."

    def suggest_alternative_input(self) -> str:
        return "You can also type the key phrase or upload a clearer recording."

    def _record_interaction_event(
        self,
        session_id: str | None,
        frustration_score: float,
        mode: str,
        signals: Dict,
        user_response: str | None = None,
    ) -> None:
        """
        Store a lightweight interaction event so we can analyze trajectories later.
        """
        db = get_session()
        try:
            event = InteractionEvent(
                session_id=session_id,
                timestamp=datetime.utcnow(),
                frustration_score=frustration_score,
                interaction_mode=mode,
                signals=signals,
                user_response=user_response or "",
            )
            db.add(event)
            db.commit()
        finally:
            db.close()
