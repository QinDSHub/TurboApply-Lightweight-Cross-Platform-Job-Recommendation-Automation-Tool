"""
**Part 1:** Extract `company` and `applied_date`.

**Part 2:** Match registered company names with the platform's formal company names.
For example: `ABC` → `ABC Company`.

**Tested approaches:**
**Sentence Transformers** — semantic matching and normalization.
**OpenAI Text Embeddings API** — Top-1 similarity search.
**LinkTransformer** — entity matching.
**Jaro-Winkler** — similarity + threshold; **best performance**, but manual matching is still needed for cold-start companies.

Suggest to gain your own apply data aligned with the format in ../applied_data/last_apply_data.csv, also you could ignore it.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import re
import argparse
from utils import load_config

def parse_applied_data(apply_data_path: Path) -> pd.DataFrame:
    if not apply_data_path.exists():
        raise FileNotFoundError(f"apply_data_path not found: {apply_data_path}")
    if not apply_data_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {apply_data_path}")

    all_file_names = []
    for p in apply_data_path.iterdir():
        if not p.is_dir():
            continue
        for f in p.iterdir():
            if f.is_file() and not f.name.startswith('.'):
                all_file_names.append(f.name)

    print(f"[INFO] Total applied jobs: {len(all_file_names)}")

    datas = []
    for name in all_file_names:
        raw_company = re.split(r'[,，]', name)[0].strip()
        company = raw_company if raw_company else 'Unknown'

        parts = re.split(r'[,，]', name)
        position = parts[1].strip() if len(parts) > 1 and parts[1].strip() else 'Unknown'

        m = re.search(r'(\d{8})', name)
        date = m.group(1) if m else '20260101'

        datas.append([company, position, date])

    df = pd.DataFrame(datas, columns=['company', 'title', 'apply_date'])
    df['company'] = df['company'].str.lower()
    print(f"[INFO] Parsed shape: {df.shape}")
    return df

if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(description="get my apply history data")
    parser.add_argument("--config", type=str,
                        default=str(PROJECT_ROOT / "config.yaml"),
                        help="Path to the YAML config file")
    args = parser.parse_args()

    cfg = load_config(args.config)
    config_dir = Path(args.config).resolve().parent

    def resolve_path(base: Path, p: str) -> Path:
        p = Path(p)
        return p if p.is_absolute() else (base / p).resolve()

    apply_data_path = resolve_path(config_dir, cfg["apply_data_path"])
    save_file       = resolve_path(config_dir, cfg["save_file"])

    print(f"[INFO] Reading applied data from: {apply_data_path}")
    df = parse_applied_data(apply_data_path)

    save_file.parent.mkdir(parents=True, exist_ok=True)
    df_needed = df[['apply_date', 'company']].drop_duplicates().reset_index(drop=True)
    df_needed.to_csv(save_file, index=False, encoding="utf-8-sig")

    print(f"[INFO] Saved to: {save_file}")
    print("Completed your own applied historical data!")

