"""Quick CLI to test the RAG chat locally — run: python test_chat.py"""
from app.rag.chat_service import chat_service


def main():
    print("\n  MindUp AI Tutor — Test Mode")
    print("  Type 'exit' to quit\n")

    session_id = None

    while True:
        q = input("You: ").strip()
        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            break

        result = chat_service.ask(
            question=q,
            subject=None,
            session_id=session_id,
        )

        session_id = result["session_id"]

        print(f"\nBot: {result['answer']}")
        print(f"  [confidence: {result['confidence']} | matched: {result['matched']}]")

        if result["sources"]:
            print("  Sources:")
            for s in result["sources"]:
                print(f"    - {s.get('citation', s['source_file'])}")

        if result["cited_pages"]:
            print(f"  Cited pages: {result['cited_pages']}")

        print()


if __name__ == "__main__":
    main()
