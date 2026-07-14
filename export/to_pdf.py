import re
import pandas as pd
from fpdf import FPDF

# Larghezza utile pagina A4 con margini 10mm
_PAGE_W = 190


def _clean(s: str) -> str:
    """Rimuove tutti i caratteri fuori dal range Latin-1 supportato da Helvetica."""
    return s.encode("latin-1", errors="ignore").decode("latin-1")


def _reset_x(pdf: FPDF) -> None:
    """Porta il cursore al margine sinistro per evitare 'not enough space'."""
    pdf.set_x(pdf.l_margin)


def artifact_to_pdf(text: str, dataframes: list[pd.DataFrame]) -> bytes:
    """Genera un PDF con il testo e le tabelle dell'artifact."""
    pdf = FPDF(orientation="L" if _needs_landscape(dataframes) else "P")
    page_w = 277 if pdf.w > 200 else _PAGE_W  # landscape o portrait
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- Testo ---
    for line in text.splitlines():
        stripped = re.sub(r"^#{1,3}\s*", "", line).strip("* \t")
        if not stripped:
            pdf.ln(3)
            continue
        _reset_x(pdf)
        if re.match(r"^#{1,3} ", line):
            pdf.set_font("Helvetica", "B", 13)
        else:
            pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, _clean(stripped))

    # --- Tabelle ---
    for i, df in enumerate(dataframes):
        pdf.ln(4)
        _reset_x(pdf)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"Tabella {i + 1}", ln=True)

        if df.empty:
            continue

        n_cols = len(df.columns)
        # Tronca testo cella in base alla larghezza: min 8mm per colonna
        col_w = max(page_w / max(n_cols, 1), 8)
        max_chars = max(int(col_w / 2), 4)  # ~2pt per carattere font-8

        # Header
        _reset_x(pdf)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(220, 220, 220)
        for col in df.columns:
            pdf.cell(col_w, 6, _clean(str(col))[:max_chars], border=1, fill=True)
        pdf.ln()

        # Righe
        pdf.set_font("Helvetica", size=8)
        pdf.set_fill_color(255, 255, 255)
        for _, row in df.iterrows():
            _reset_x(pdf)
            for val in row:
                pdf.cell(col_w, 5, _clean(str(val))[:max_chars], border=1)
            pdf.ln()

        _reset_x(pdf)

    return bytes(pdf.output())


def _needs_landscape(dataframes: list[pd.DataFrame]) -> bool:
    """Usa formato orizzontale se ci sono tabelle con molte colonne."""
    return any(len(df.columns) > 6 for df in dataframes)
