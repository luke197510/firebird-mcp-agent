# Firebird MCP Agent

Agente LLM che interroga in **linguaggio naturale** un database gestionale legacy
(Firebird 2.5), con **mascheramento dei dati personali** prima dell'invio al modello
ed esportazione dei risultati in Excel, PDF e Word.

Nasce da un problema reale: in un'azienda i dati che servono alle decisioni sono già
tutti nel gestionale, ma per estrarli serve qualcuno che sappia scrivere SQL. Chi ha le
domande — chi vende, chi ordina, chi decide — non è quella persona.

---

## Il problema, e perché non è banale

Collegare un LLM a un database sembra un esercizio da un pomeriggio. Non lo è, per tre
ragioni che si scoprono solo mettendoci le mani.

**1. I gestionali legacy non parlano SQL standard.** Firebird 2.5 in *Dialect 1* non
supporta `CAST(x AS DATE)`, né `CURRENT_DATE`, né i literal `DATE '2024-01-01'`. Un
modello che genera SQL "da manuale" fallisce sistematicamente sulle query con date —
cioè su quasi tutte le domande di business. La soluzione non è un modello più grosso: è
**documentare le eccezioni del dialetto nel system prompt**, così il modello genera SQL
che funziona al primo colpo.

**2. Non puoi spedire dati personali a un'API di terzi.** Un gestionale contiene nomi,
codici fiscali, indirizzi, recapiti. Mandarli a un LLM esterno è un problema di
compliance, non un dettaglio.

**3. I nomi delle colonne non spiegano niente.** In un gestionale reale un campo si
chiama `KM10` e nessun modello, per quanto capace, può indovinare cosa sia. Lo schema
va documentato: è il vero lavoro, ed è la parte che determina la qualità del risultato.

## L'architettura

```
     Domanda in linguaggio naturale
                 │
                 ▼
        ┌────────────────┐
        │  Agente (Agno) │  Claude o Mistral, intercambiabili
        └───────┬────────┘
                │ tool call
                ▼
        ┌────────────────┐
        │  MCP Server    │  query_sql · list_tables · describe_table
        │   (Firebird)   │  sola lettura, max 500 righe
        └───────┬────────┘
                │ righe grezze
                ▼
        ┌────────────────┐
        │  mask()        │  ← i dati personali NON escono di qui
        └───────┬────────┘
                │ righe con placeholder: [NOMINATIVO_1], [CODICE_FISCALE_2]
                ▼
             ╔══════╗
             ║ LLM  ║   (API esterna)
             ╚══╤═══╝
                │ risposta con placeholder
                ▼
        ┌────────────────┐
        │  unmask()      │  → i valori reali tornano solo lato utente
        └───────┬────────┘
                ▼
      Risposta + export (Excel / PDF / Word)
```

### Il punto chiave: mask / unmask

I dati identificativi vengono sostituiti da **placeholder univoci** prima della chiamata
al modello, e ripristinati **dopo** che la risposta è tornata. Il mapping
placeholder → valore reale resta in memoria locale e non lascia mai la macchina.

L'LLM ragiona su `[NOMINATIVO_3]`, produce la sua analisi, e l'utente finale legge il
nome vero. Il modello non ha mai visto un dato identificativo.

Il system prompt impone inoltre di mostrare sempre i **codici numerici** accanto ai nomi:
è quello che permette a chi legge di verificare la corrispondenza con i dati originali,
invece di doversi fidare.

### Perché MCP e non tool function ad hoc

Esporre il database via **Model Context Protocol** significa che lo stesso server è
utilizzabile da qualunque client MCP — l'agente di questo repo, ma anche Claude Desktop
o altri — senza riscrivere l'integrazione. Il database diventa una capacità componibile,
non un pezzo di codice incastrato dentro un'applicazione.

## Componenti

| Percorso | Ruolo |
|---|---|
| `mcp/firebird_server.py` | Server MCP: espone il database come tool (`query_sql`, `list_tables`, `describe_table`) |
| `hooks/data_mask.py` | Mascheramento e ripristino dei dati personali |
| `prompts/system_prompt.py` | Schema del database + convenzioni del dialetto SQL |
| `agents/db_agent.py` | Agente (framework Agno), provider LLM intercambiabile |
| `app.py` | Interfaccia Streamlit |
| `main.py` | Interfaccia a riga di comando |
| `export/` | Esportazione in Excel, PDF, Word |

## Limiti noti

Dichiararli è parte del lavoro.

- **Il filtro `SELECT` non è una misura di sicurezza.** `query_sql` verifica che la query
  inizi con `SELECT`: è un controllo sintattico, non un sandbox. **La protezione vera è
  un utente di database con permessi di sola lettura**, ed è così che va configurato
  (vedi `.env.example`).
- **Il masking copre gli identificativi diretti, non l'inferenza.** Nome, codice fiscale
  e recapiti non raggiungono il modello, ma il contenuto delle transazioni sì. Su domini
  sensibili questo va valutato caso per caso: l'anonimizzazione dei soli identificativi
  non equivale alla non-riconoscibilità.
- **Il limite di 500 righe** protegge la finestra di contesto, ma va gestito con
  aggregazioni: il system prompt spinge il modello ad aggregare lato database.
- **Lo schema nel system prompt è un esempio generico.** Su un database reale va
  sostituito con quello effettivo — è la parte da adattare, ed è quella che pesa di più
  sulla qualità delle query.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # e compilare con le proprie credenziali
python main.py            # CLI
streamlit run app.py      # interfaccia web
```

## Stack

Python · [MCP](https://modelcontextprotocol.io) · [Agno](https://github.com/agno-agi/agno) ·
Anthropic Claude / Mistral · Firebird 2.5 (`fdb`) · Streamlit · openpyxl / ReportLab / python-docx

---

Progetto realizzato su un Database in produzione e qui pubblicato in versione
generalizzata: lo schema del database originale è sostituito da uno schema di esempio,
e tutte le credenziali sono placeholder.
