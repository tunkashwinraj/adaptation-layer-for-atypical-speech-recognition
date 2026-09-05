import json
import os
from datetime import datetime
from typing import Dict, List

import pandas as pd


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
REPORTS_DIR = os.path.join(EXPORTS_DIR, "reports")
VIS_DIR = os.path.join(EXPORTS_DIR, "visualizations")
DATA_DIR = os.path.join(EXPORTS_DIR, "datasets")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(VIS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


class ExportManager:
    def generate_latex_table(self, data: List[Dict], caption: str = "Performance Comparison") -> str:
        if not data:
            return ""
        df = pd.DataFrame(data)
        cols = "l" + "c" * (len(df.columns) - 1)
        header = " & ".join(df.columns) + " \\\\"
        rows = "\n".join(" & ".join(map(str, row)) + " \\\\" for row in df.values.tolist())
        return (
            "\\begin{table}[h]\n"
            f"\\caption{{{caption}}}\n"
            f"\\begin{{tabular}}{{{cols}}}\n"
            "\\hline\n"
            f"{header}\n"
            "\\hline\n"
            f"{rows}\n"
            "\\hline\n"
            "\\end{tabular}\n"
            "\\end{table}\n"
        )

    def generate_statistical_report(self, data: List[Dict]) -> Dict:
        df = pd.DataFrame(data)
        if df.empty:
            return {}
        return {
            "mean": df.mean(numeric_only=True).to_dict(),
            "std": df.std(numeric_only=True).to_dict(),
        }

    def export_visualizations(self, figures: List, dpi: int = 300, fmt: str = "png") -> List[str]:
        paths = []
        for i, fig in enumerate(figures):
            if fig is None:
                continue
            filename = f"figure_{i+1}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{fmt}"
            path = os.path.join(VIS_DIR, filename)
            fig.write_image(path, scale=2)
            paths.append(path)
        return paths

    def create_research_summary(self, study_metadata: Dict, metrics: Dict) -> str:
        payload = {
            "study_metadata": study_metadata,
            "metrics": metrics,
        }
        filename = f"research_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(REPORTS_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return path

    def export_anonymized_dataset(self, rows: List[Dict]) -> str:
        filename = f"dataset_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        path = os.path.join(DATA_DIR, filename)
        df = pd.DataFrame(rows)
        if "name" in df.columns:
            df = df.drop(columns=["name"])
        df.to_csv(path, index=False)
        return path
