"""
Pre/post hook per mascherare dati sensibili prima della chiamata LLM
e riattaccarli nella risposta finale.
"""

# Nomi di colonna che contengono dati personali. Adattare al proprio schema.
# Confronto case-insensitive (il DB Firebird restituisce nomi in UPPER).
_SENSITIVE_FIELDS = {
    # Identificativi fiscali
    "CF", "CODICE_FISCALE", "COD_FISC", "PARTITA_IVA",
    # Nomi di persone
    "NOMINATIVO", "NOME_OPERATORE", "RAGIONE_SOCIALE", "ANAGRAFICA",
    # Recapiti
    "INDIRIZZO", "INDIRIZZO1", "INDIRIZZO2",
    "TELEFONO", "TELEFONO1", "TELEFONO2",
    "EMAIL", "EMAIL1",
}


def mask(data: list[dict], start_counter: int = 1) -> tuple[list[dict], dict[str, str]]:
    """Sostituisce i valori sensibili con placeholder univoci.

    start_counter permette di continuare la numerazione tra chiamate successive
    nella stessa sessione, evitando collisioni nel mapping.
    Restituisce (righe_mascherata, mappa placeholder→valore_reale).
    """
    mapping: dict[str, str] = {}
    counter = start_counter
    masked = []
    for row in data:
        new_row = {}
        for key, value in row.items():
            if key.upper() in _SENSITIVE_FIELDS and value and str(value).strip():
                placeholder = f"[{key.upper()}_{counter}]"
                mapping[placeholder] = str(value)
                new_row[key] = placeholder
                counter += 1
            else:
                new_row[key] = value
        masked.append(new_row)
    return masked, mapping


def unmask(text: str, mapping: dict[str, str]) -> str:
    """Rimappa i placeholder con i valori reali nella risposta LLM."""
    for placeholder, real_value in mapping.items():
        text = text.replace(placeholder, real_value)
    return text
