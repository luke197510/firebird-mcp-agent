import io
import pandas as pd


def dataframes_to_excel(dataframes: list[pd.DataFrame]) -> bytes:
    """Crea un file .xlsx con un foglio per ogni DataFrame."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for i, df in enumerate(dataframes):
            sheet = f"Tabella_{i + 1}"[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)
    return buffer.getvalue()
