"""
MCP server per Firebird 2.5 - espone le tabelle del database come tool per l'agente.
Avviare con: python mcp/firebird_server.py
"""
import os
import fdb
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

load_dotenv()

app = Server("firebird-database")

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


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="query_sql",
            description="Esegue una query SELECT sul database il gestionale (Firebird 2.5). Solo lettura.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "Query SQL SELECT da eseguire (max 500 righe restituite).",
                    }
                },
                "required": ["sql"],
            },
        ),
        types.Tool(
            name="list_tables",
            description="Restituisce l'elenco delle tabelle presenti nel database il gestionale.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="describe_table",
            description="Descrive la struttura (colonne e tipi) di una tabella il gestionale.",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Nome della tabella."}
                },
                "required": ["table_name"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    con = _connect()
    cur = con.cursor()
    try:
        if name == "list_tables":
            cur.execute(
                "SELECT RDB$RELATION_NAME FROM RDB$RELATIONS "
                "WHERE RDB$SYSTEM_FLAG = 0 ORDER BY RDB$RELATION_NAME"
            )
            tables = [r[0].strip() for r in cur.fetchall()]
            return [types.TextContent(type="text", text="\n".join(tables))]

        elif name == "describe_table":
            table = arguments["table_name"].upper()
            cur.execute(
                """
                SELECT rf.RDB$FIELD_NAME, f.RDB$FIELD_TYPE, f.RDB$FIELD_LENGTH
                FROM RDB$RELATION_FIELDS rf
                JOIN RDB$FIELDS f ON rf.RDB$FIELD_SOURCE = f.RDB$FIELD_NAME
                WHERE rf.RDB$RELATION_NAME = ?
                ORDER BY rf.RDB$FIELD_POSITION
                """,
                (table,),
            )
            rows = _rows_to_dicts(cur)
            lines = [f"{r['RDB$FIELD_NAME'].strip()} ({r['RDB$FIELD_TYPE']})" for r in rows]
            return [types.TextContent(type="text", text="\n".join(lines))]

        elif name == "query_sql":
            sql = arguments["sql"].strip()
            if not sql.upper().startswith("SELECT"):
                return [types.TextContent(type="text", text="ERRORE: solo query SELECT consentite.")]
            cur.execute(sql)
            rows = _rows_to_dicts(cur)[:500]
            import json
            return [types.TextContent(type="text", text=json.dumps(rows, default=str, ensure_ascii=False))]

        else:
            return [types.TextContent(type="text", text=f"Tool sconosciuto: {name}")]
    finally:
        cur.close()
        con.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))
