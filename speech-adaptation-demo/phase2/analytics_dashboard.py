import json
from typing import Dict, List

import pandas as pd
import plotly.express as px

from .db import get_session, Session, ModelPerformance


class AnalyticsDashboard:
    def performance_over_time(self, user_id: str):
        session = get_session()
        try:
            rows = (
                session.query(Session)
                .filter(Session.user_id == user_id)
                .order_by(Session.start_time.asc())
                .all()
            )
        finally:
            session.close()

        data = []
        for r in rows:
            metrics = r.metrics or {}
            data.append(
                {
                    "time": r.start_time,
                    "wer": metrics.get("wer"),
                    "semscore": metrics.get("semscore"),
                    "task_success": metrics.get("task_success"),
                }
            )
        df = pd.DataFrame(data)
        if df.empty:
            return None, None, None
        fig_wer = px.line(df, x="time", y="wer", title="WER Over Time")
        fig_sem = px.line(df, x="time", y="semscore", title="SemScore Over Time")
        fig_task = px.line(df, x="time", y="task_success", title="Task Success Rate")
        return fig_wer, fig_sem, fig_task

    def model_comparison_trends(self, user_id: str):
        session = get_session()
        try:
            rows = (
                session.query(ModelPerformance)
                .filter(ModelPerformance.user_id == user_id)
                .all()
            )
        finally:
            session.close()
        data = [
            {
                "time": r.timestamp,
                "model": r.model_name,
                "wer": r.wer,
                "semscore": r.semscore,
                "latency_ms": r.latency_ms,
                "cost_usd": r.cost_usd,
            }
            for r in rows
        ]
        df = pd.DataFrame(data)
        if df.empty:
            return None
        return px.line(df, x="time", y="wer", color="model", title="Model WER Over Time")

    def vocabulary_growth(self, vocab_history: List[Dict]):
        df = pd.DataFrame(vocab_history)
        if df.empty:
            return None
        return px.line(df, x="time", y="vocab_size", title="Vocabulary Growth")
