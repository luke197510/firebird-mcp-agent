"""
Agente database - AGNO + Mistral/Claude + tool Firebird con masking dati sensibili integrato.

Flusso:
  domanda → agent → tool Firebird → mask() → LLM → risposta con placeholder → unmask() → utente

Provider attivo: variabile d'ambiente LLM_PROVIDER ("mistral" | "claude", default "mistral")
"""
import os
import json
from dotenv import load_dotenv
import fdb
from agno.agent import Agent

from hooks import mask, unmask
from prompts import SYSTEM_PROMPT

load_dotenv()


def _build_model():
    provider = os.environ.get("LLM_PROVIDER", "mistral").lower()
    if provider == "claude":
        from agno.models.anthropic import Claude
        return Claude(id="claude-sonnet-4-6")
    else:
        from agno.models.mistral import MistralChat
        return MistralChat(id="mistral-large-latest")


def _connect():
    return fdb.connect(
        host=os.environ["FIREBIRD_HOST"],
        port=int(os.environ.get("FIREBIRD_PORT", 3050)),
        database=os.environ["FIREBIRD_DATABASE"],
        user=os.environ["FIREBIRD_USER"],
        password=os.environ["FIREBIRD_PASSWORD"],
        charset="UTF8",
    )


def _rows_to_dicts(cursor) -> list[dict]:
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


class DbSession:
    """Incapsula l'agente e la mappa di masking per una singola sessione."""

    def __init__(self):
        self._mapping: dict[str, str] = {}

        # Chiusura sui tool per accedere a self._mapping
        def list_tables() -> str:
            """Elenca tutte le tabelle presenti nel database."""
            con = _connect()
            cur = con.cursor()
            try:
                cur.execute(
                    "SELECT RDB$RELATION_NAME FROM RDB$RELATIONS "
                    "WHERE RDB$SYSTEM_FLAG = 0 ORDER BY RDB$RELATION_NAME"
                )
                return "\n".join(r[0].strip() for r in cur.fetchall())
            finally:
                cur.close(); con.close()

        def describe_table(table_name: str) -> str:
            """Descrive le colonne e i tipi di una tabella del database."""
            con = _connect()
            cur = con.cursor()
            try:
                cur.execute(
                    """
                    SELECT rf.RDB$FIELD_NAME, f.RDB$FIELD_TYPE
                    FROM RDB$RELATION_FIELDS rf
                    JOIN RDB$FIELDS f ON rf.RDB$FIELD_SOURCE = f.RDB$FIELD_NAME
                    WHERE rf.RDB$RELATION_NAME = ?
                    ORDER BY rf.RDB$FIELD_POSITION
                    """,
                    (table_name.upper(),),
                )
                rows = _rows_to_dicts(cur)
                return "\n".join(
                    f"{r['RDB$FIELD_NAME'].strip()} (tipo {r['RDB$FIELD_TYPE']})" for r in rows
                )
            finally:
                cur.close(); con.close()

        def query_sql(sql: str) -> str:
            """Esegue una query SELECT sul database il gestionale. Restituisce max 500 righe in JSON.
            I dati sensibili (nome, codice fiscale, ecc.) sono sostituiti da placeholder.
            Se la query contiene placeholder di sessione (es. [CF_1]), vengono risolti automaticamente."""
            if not sql.strip().upper().startswith("SELECT"):
                return "ERRORE: solo query SELECT consentite."
            # Pre-hook: risolve placeholder nel SQL prima di eseguire
            sql = unmask(sql, self._mapping)
            con = _connect()
            cur = con.cursor()
            try:
                cur.execute(sql)
                rows = _rows_to_dicts(cur)[:500]
                # Post-hook: maschera i dati sensibili nel risultato
                # start_counter evita collisioni se query_sql è chiamato più volte
                masked_rows, new_mapping = mask(rows, start_counter=len(self._mapping) + 1)
                self._mapping.update(new_mapping)
                return json.dumps(masked_rows, default=str, ensure_ascii=False)
            except Exception as e:
                return f"ERRORE SQL: {e}\nCorreggi la query e riprova."
            finally:
                cur.close(); con.close()

        self._agent = Agent(
            model=_build_model(),
            tools=[list_tables, describe_table, query_sql],
            instructions=SYSTEM_PROMPT,
            markdown=True,
        )

    def ask(self, question: str) -> str:
        self._mapping.clear()
        response = self._agent.run(question)
        text = response.content if hasattr(response, "content") else str(response)
        return unmask(text, self._mapping)

    async def aask(self, question: str) -> str:
        self._mapping.clear()
        response = await self._agent.arun(question)
        text = response.content if hasattr(response, "content") else str(response)
        return unmask(text, self._mapping)


if __name__ == "__main__":
    session = DbSession()
    question = input("Domanda: ")
    print("\n" + session.ask(question))
