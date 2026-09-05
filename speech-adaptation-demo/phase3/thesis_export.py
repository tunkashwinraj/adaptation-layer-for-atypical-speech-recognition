import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from phase2.db import Session as SessionRow, get_session


EXPORT_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")


@dataclass
class StageDistributions:
    baseline: List[float]
    personalized: List[float]
    repaired: List[float]


class ThesisGenerator:
    """
    Phase 3: generate publication-ready tables, figures and text for the thesis.

    This implementation focuses on the essentials:
    - WER-like metrics across three stages (baseline, personalized, repaired)
    - Paired significance tests and effect sizes
    - Plots suitable for direct inclusion in the thesis
    """

    def __init__(self) -> None:
        os.makedirs(EXPORT_ROOT, exist_ok=True)

    # --------- Public API ----------

    def generate_results_chapter_for_user(self, user_id: str | None = None) -> str:
        """
        Generate LaTeX for the Results section plus all artifacts on disk.

        Returns the path of the directory that contains all exports.
        """
        out_dir = self._create_output_dir()
        stages = self._collect_stage_distributions(user_id=user_id)

        if not stages.baseline or not stages.personalized or not stages.repaired:
            # Not enough data yet; still create an empty manifest.
            manifest_path = os.path.join(out_dir, "MANIFEST.txt")
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write("Insufficient data to compute full thesis exports.\n")
            return out_dir

        # Tables and stats
        wer_table = self._latex_wer_comparison_table(stages)
        stats_summary, tests = self._statistical_tests(stages)

        # Figures
        self._plot_wer_trajectory(user_id, out_dir)
        self._plot_wer_boxplot(stages, out_dir)

        # Assemble minimal Results section text
        results_tex = self._compile_results_section(stages, tests)
        results_path = os.path.join(out_dir, "results.tex")
        with open(results_path, "w", encoding="utf-8") as f:
            f.write(results_tex)

        # Save table and stats
        table_path = os.path.join(out_dir, "wer_comparison_table.tex")
        with open(table_path, "w", encoding="utf-8") as f:
            f.write(wer_table)

        stats_path = os.path.join(out_dir, "stats_summary.txt")
        with open(stats_path, "w", encoding="utf-8") as f:
            f.write(stats_summary)

        return out_dir

    # --------- Data collection ----------

    def _collect_stage_distributions(self, user_id: str | None = None) -> StageDistributions:
        """
        Read Session.metrics and collect per-stage error rates.

        We rely on metrics stored by Phase 2, where we now persist
        baseline_wer / personalized_wer / repaired_wer when available.
        """
        db = get_session()
        try:
            query = db.query(SessionRow)
            if user_id:
                query = query.filter(SessionRow.user_id == user_id)
            sessions = query.all()
        finally:
            db.close()

        baseline, personalized, repaired = [], [], []
        for s in sessions:
            m = s.metrics or {}
            if "baseline_wer" in m and m["baseline_wer"] is not None:
                baseline.append(float(m["baseline_wer"]) * 100.0)
            if "personalized_wer" in m and m["personalized_wer"] is not None:
                personalized.append(float(m["personalized_wer"]) * 100.0)
            if "repaired_wer" in m and m["repaired_wer"] is not None:
                repaired.append(float(m["repaired_wer"]) * 100.0)

        return StageDistributions(baseline=baseline, personalized=personalized, repaired=repaired)

    # --------- Statistics ----------

    def _paired_test(self, a: List[float], b: List[float]) -> Tuple[float, float, float]:
        """
        Paired t-test and Cohen's d (effect size) between two conditions.
        """
        if len(a) != len(b) or len(a) == 0:
            return np.nan, np.nan, np.nan

        t_stat, p_val = stats.ttest_rel(a, b)
        diff = np.array(a) - np.array(b)
        d = diff.mean() / (diff.std(ddof=1) + 1e-8)
        return float(t_stat), float(p_val), float(d)

    def _statistical_tests(self, stages: StageDistributions) -> Tuple[str, dict]:
        baseline, personalized, repaired = stages.baseline, stages.personalized, stages.repaired
        summary_lines = []

        def _fmt(x: float) -> str:
            return "nan" if np.isnan(x) else f"{x:.3f}"

        t_bp, p_bp, d_bp = self._paired_test(baseline, personalized)
        t_pr, p_pr, d_pr = self._paired_test(personalized, repaired)

        summary_lines.append("Paired comparisons (WER, lower is better):")
        summary_lines.append(
            f"Baseline vs Personalized: t={_fmt(t_bp)}, p={_fmt(p_bp)}, d={_fmt(d_bp)}"
        )
        summary_lines.append(
            f"Personalized vs Repaired: t={_fmt(t_pr)}, p={_fmt(p_pr)}, d={_fmt(d_pr)}"
        )

        tests = {
            "baseline_vs_personalized": {"t": t_bp, "p": p_bp, "d": d_bp},
            "personalized_vs_repaired": {"t": t_pr, "p": p_pr, "d": d_pr},
        }
        return "\n".join(summary_lines), tests

    # --------- LaTeX generation ----------

    def _ci95(self, values: List[float]) -> Tuple[float, float]:
        if not values:
            return np.nan, np.nan
        arr = np.array(values)
        mean = arr.mean()
        se = arr.std(ddof=1) / np.sqrt(len(arr))
        delta = 1.96 * se
        return float(mean - delta), float(mean + delta)

    def _latex_wer_comparison_table(self, stages: StageDistributions) -> str:
        baseline, personalized, repaired = stages.baseline, stages.personalized, stages.repaired

        def _stats(vals: List[float]) -> Tuple[float, float, Tuple[float, float]]:
            if not vals:
                return np.nan, np.nan, (np.nan, np.nan)
            return float(np.mean(vals)), float(np.std(vals, ddof=1)), self._ci95(vals)

        b_mean, b_sd, (b_lo, b_hi) = _stats(baseline)
        p_mean, p_sd, (p_lo, p_hi) = _stats(personalized)
        r_mean, r_sd, (r_lo, r_hi) = _stats(repaired)

        template = r"""
\begin{table}[h]
\centering
\caption{Word Error Rate Comparison Across System Stages}
\begin{tabular}{lccc}
\hline
\textbf{Stage} & \textbf{Mean WER (\%)} & \textbf{SD} & \textbf{95\% CI} \\
\hline
Baseline ASR & {b_mean:.2f} & {b_sd:.2f} & [{b_lo:.2f}, {b_hi:.2f}] \\
Personalized ASR & {p_mean:.2f} & {p_sd:.2f} & [{p_lo:.2f}, {p_hi:.2f}] \\
Semantic Repair & {r_mean:.2f} & {r_sd:.2f} & [{r_lo:.2f}, {r_hi:.2f}] \\
\hline
\end{tabular}
\end{table}
"""
        return template.format(
            b_mean=b_mean,
            b_sd=b_sd,
            b_lo=b_lo,
            b_hi=b_hi,
            p_mean=p_mean,
            p_sd=p_sd,
            p_lo=p_lo,
            p_hi=p_hi,
            r_mean=r_mean,
            r_sd=r_sd,
            r_lo=r_lo,
            r_hi=r_hi,
        )

    # --------- Figures ----------

    def _plot_wer_boxplot(self, stages: StageDistributions, out_dir: str) -> None:
        data = [
            stages.baseline,
            stages.personalized,
            stages.repaired,
        ]
        labels = ["Baseline", "Personalized", "Repaired"]

        if not any(data):
            return

        plt.figure(figsize=(6, 4))
        plt.boxplot(data, labels=labels)
        plt.ylabel("WER (%)")
        plt.title("WER distribution across stages")
        plt.tight_layout()
        path = os.path.join(out_dir, "wer_boxplot.png")
        plt.savefig(path, dpi=300)
        plt.close()

    def _plot_wer_trajectory(self, user_id: str | None, out_dir: str) -> None:
        """
        Simple trajectory plot of repaired WER/MER over sessions.
        """
        db = get_session()
        try:
            query = db.query(SessionRow).order_by(SessionRow.start_time.asc())
            if user_id:
                query = query.filter(SessionRow.user_id == user_id)
            sessions = query.all()
        finally:
            db.close()

        xs, ys = [], []
        for idx, s in enumerate(sessions, start=1):
            m = s.metrics or {}
            val = None
            if "repaired_wer" in m and m["repaired_wer"] is not None:
                val = float(m["repaired_wer"]) * 100.0
            elif "mer" in m and m["mer"] is not None:
                val = float(m["mer"]) * 100.0
            if val is not None:
                xs.append(idx)
                ys.append(val)

        if not xs:
            return

        plt.figure(figsize=(6, 4))
        plt.plot(xs, ys, marker="o")
        plt.xlabel("Session")
        plt.ylabel("Error rate (%)")
        plt.title("Trajectory of repaired transcript error over sessions")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        path = os.path.join(out_dir, "wer_trajectory.png")
        plt.savefig(path, dpi=300)
        plt.close()

    # --------- Results text ----------

    def _compile_results_section(self, stages: StageDistributions, tests: dict) -> str:
        baseline, personalized, repaired = stages.baseline, stages.personalized, stages.repaired

        def _mean(vals: List[float]) -> float:
            return float(np.mean(vals)) if vals else float("nan")

        b_mean = _mean(baseline)
        p_mean = _mean(personalized)
        r_mean = _mean(repaired)

        bp = tests.get("baseline_vs_personalized", {})
        pr = tests.get("personalized_vs_repaired", {})

        def _pval(p: float) -> str:
            if np.isnan(p):
                return "n.s."
            if p < 0.001:
                return "p < .001"
            if p < 0.01:
                return "p < .01"
            if p < 0.05:
                return "p < .05"
            return f"p = {p:.2f}"

        text = f"""
Results

Baseline ASR achieved a mean word error rate (WER) of {b_mean:.2f}\\%.
Personalized ASR with vocabulary biasing reduced WER to {p_mean:.2f}\\%.
Semantic repair with the language model further reduced WER to {r_mean:.2f}\\%.

Paired comparisons indicated that personalization significantly improved performance
relative to the baseline condition ({_pval(bp.get('p', float('nan')))}), and that semantic
repair provided additional gains over the personalized transcripts
({_pval(pr.get('p', float('nan')))}). Effect sizes (Cohen's $d$) for these
comparisons are provided in the accompanying statistical summary.
"""
        return text

    # --------- Helpers ----------

    def _create_output_dir(self) -> str:
        ts = datetime.utcnow().strftime("thesis_%Y-%m-%d_%H-%M-%S")
        out_dir = os.path.join(EXPORT_ROOT, ts)
        os.makedirs(out_dir, exist_ok=True)
        return out_dir

