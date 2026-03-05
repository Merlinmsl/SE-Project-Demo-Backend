import urllib.request, json
import time
from svix.webhooks import Webhook

# Shared mock secret for test
WEBHOOK_SECRET = "whsec_bXlfc3VwZXJfc2VjcmV0X2tleV8xMjM0NTY3ODkwMTI="

def test_webhook(event_type: str, user_id: str, email: str):
    """Send simulated clerk webhook."""
    payload = {
        "data": {
            "id": user_id,
            "email_addresses": [
                {
                    "email_address": email,
                    "id": f"email_{user_id}"
                }
            ],
            "primary_email_address_id": f"email_{user_id}",
            "username": f"user_{user_id}"
        },
        "object": "event",
        "type": event_type
    }
    
    body = json.dumps(payload).encode('utf-8')
    wh = Webhook(WEBHOOK_SECRET)
    
    msg_id = f"msg_{int(time.time())}"
    import datetime
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    
    # Use native svix signer to guarantee signature matches exactly
    signature = wh.sign(msg_id, timestamp, body.decode('utf-8'))
    
    headers = {
        "svix-id": msg_id,
        "svix-timestamp": str(int(timestamp.timestamp())),
        "svix-signature": signature,
        "Content-Type": "application/json"
    }
    
    try:
        req = urllib.request.Request(
            "http://localhost:8000/api/webhooks/clerk", 
            headers=headers, 
            method="POST", 
            data=body
        )
        with urllib.request.urlopen(req) as r:
            res = json.loads(r.read())
            print(f"[OK] {event_type} webhook successful: {res}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[FAIL] {event_type} webhook error {e.code}: {e.read().decode()}")
        return False

# Test workflow
print("Testing Clerk Webhook (creating user_webhook_test)")
ok = test_webhook("user.created", "user_webhook_test", "webhook@test.com")

if ok:
    print("\nVerifying user exists via SQLAlchemy:")
    import os
    os.system('.venv\\Scripts\\python.exe -c "from app.db.session import engine; from sqlalchemy import text; r = engine.connect().execute(text(\\\"SELECT id, clerk_user_id, email, username FROM students WHERE clerk_user_id=\'user_webhook_test\'\\\")).first(); print(\'FOUND STUDENT:\', r)"')
    
    print("\nTesting user.deleted")
    test_webhook("user.deleted", "user_webhook_test", "webhook@test.com")
    
    print("\nVerifying user deleted via SQLAlchemy:")
    os.system('.venv\\Scripts\\python.exe -c "from app.db.session import engine; from sqlalchemy import text; r = engine.connect().execute(text(\\\"SELECT id FROM students WHERE clerk_user_id=\'user_webhook_test\'\\\")).first(); print(\'STUDENT EXISTS AFTER DELETE:\', r is not None)"')
