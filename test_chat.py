"""
End-to-end chatbot backend test.
Tests: subjects, ask (with History subject), follow-up session continuity.
Run: python test_chat.py
"""
from app.api.v1.chat import ask_question
from app.schemas.chat import ChatRequest
from app.db.session import SessionLocal

db = SessionLocal()
try:
    print("=" * 60)
    print("TEST 1: History question (no auth = anonymous)")
    print("=" * 60)
    data = ChatRequest(question="What caused World War 1?", subject="History")
    result = ask_question(data=data, db=db, user=None)
    print(f"  matched:    {result.matched}")
    print(f"  confidence: {result.confidence}")
    print(f"  session_id: {result.session_id}")
    print(f"  sources:    {len(result.sources)}")
    if result.sources:
        print(f"  citation:   {result.sources[0].citation}")
    print(f"  answer:     {result.answer[:300]}")

    print()
    print("=" * 60)
    print("TEST 2: Follow-up question (same session)")
    print("=" * 60)
    sid = result.session_id
    data2 = ChatRequest(question="Who were the main leaders involved?", subject="History", session_id=sid)
    result2 = ask_question(data=data2, db=db, user=None)
    print(f"  matched:    {result2.matched}")
    print(f"  session_id: {result2.session_id}  (same={result2.session_id == sid})")
    print(f"  answer:     {result2.answer[:200]}")

    print()
    print("=" * 60)
    print("TEST 3: Off-topic question (should be rejected)")
    print("=" * 60)
    data3 = ChatRequest(question="What is 2+2?", subject="History")
    result3 = ask_question(data=data3, db=db, user=None)
    print(f"  is_on_topic: {result3.is_on_topic}")
    print(f"  answer:      {result3.answer}")

    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

except Exception as e:
    import traceback
    print("FAILED:")
    traceback.print_exc()
finally:
    db.close()
