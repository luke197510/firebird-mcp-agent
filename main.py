"""
Entry point Firebird MCP Agent.
Uso: python main.py
"""
from agents.db_agent import DbSession


def main():
    print("=== Firebird MCP Agent - Gestionale il gestionale ===")
    session = DbSession()
    while True:
        try:
            question = input("\nDomanda (q per uscire): ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if question.lower() in ("q", "quit", "exit"):
            break
        if not question:
            continue
        print("\n" + session.ask(question))


if __name__ == "__main__":
    main()
