"""Estrae tabelle GFM (GitHub Flavored Markdown) da una stringa di testo."""
import re
import pandas as pd

_TABLE_RE = re.compile(
    r'(\|.+\|\n\|[ :\-|]+\|\n(?:\|.+\|\n?)+)',
    re.MULTILINE,
)


def _parse_table(raw: str) -> pd.DataFrame:
    lines = [l.strip() for l in raw.strip().splitlines()]
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:  # salta riga separatore
        cells = [c.strip() for c in line.strip("|").split("|")]
        # padding/trim per allinearsi all'header
        while len(cells) < len(headers):
            cells.append("")
        rows.append(cells[: len(headers)])
    return pd.DataFrame(rows, columns=headers)


def extract_tables(text: str) -> tuple[str, list[pd.DataFrame]]:
    """Ritorna (testo_senza_tabelle, lista_dataframe).

    Ogni tabella trovata viene rimossa dal testo e sostituita con
    il segnaposto '[Tabella N]'. Se il parsing di una tabella fallisce
    viene lasciata nel testo originale.
    """
    dataframes: list[pd.DataFrame] = []
    clean = text

    for match in _TABLE_RE.finditer(text):
        try:
            df = _parse_table(match.group(0))
            dataframes.append(df)
            clean = clean.replace(match.group(0), f"\n*[Tabella {len(dataframes)}]*\n")
        except Exception:
            pass  # lascia la tabella nel testo se il parsing fallisce

    return clean, dataframes
