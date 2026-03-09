import logging
from typing import Dict, Any
from fastapi import APIRouter, Header, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from svix.webhooks import Webhook, WebhookVerificationError

from app.core.config import settings
from app.db.session import get_db
from app.repositories.student_repo import StudentRepository
from app.core.security import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/clerk")
async def handle_clerk_webhook(
    request: Request,
    svix_id: str = Header(..., alias="svix-id", include_in_schema=False),
    svix_timestamp: str = Header(..., alias="svix-timestamp", include_in_schema=False),
    svix_signature: str = Header(..., alias="svix-signature", include_in_schema=False),
    db: Session = Depends(get_db),
):
    """
    Handle Clerk webhook events to sync users into the database.
    Requires CLERK_WEBHOOK_SECRET to be set in the environment.
    """
    if not settings.clerk_webhook_secret:
        logger.error("CLERK_WEBHOOK_SECRET is not configured.")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Get the raw request body to verify the signature
    payload = await request.body()
    headers = {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": svix_signature,
    }

    # Verify signature
    try:
        wh = Webhook(settings.clerk_webhook_secret)
        event: Dict[str, Any] = wh.verify(payload, headers)
    except WebhookVerificationError as e:
        print(f"WEBHOOK ERR: {e}. Secret: {settings.clerk_webhook_secret}")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error parsing webhook payload: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")

    event_type = event.get("type")
    data = event.get("data", {})
    clerk_user_id = data.get("id")

    if not clerk_user_id:
        logger.warning(f"Received {event_type} webhook without a user ID")
        return {"ok": True, "message": "No user ID, ignored"}

    logger.info(f"Processing Clerk webhook: {event_type} for user {clerk_user_id}")
    student_repo = StudentRepository(db)

    try:
        if event_type == "user.created" or event_type == "user.updated":
            # Extract primary email address
            email = None
            email_addresses = data.get("email_addresses", [])
            primary_email_id = data.get("primary_email_address_id")
            
            for ea in email_addresses:
                if ea.get("id") == primary_email_id:
                    email = ea.get("email_address")
                    break
            
            if not email and email_addresses:
                # Fallback to the first email if no primary is set (rare)
                email = email_addresses[0].get("email_address")

            # Create or update student
            user_auth = AuthUser(clerk_user_id=clerk_user_id, email=email)
            student = student_repo.create_if_missing(user_auth)
            
            # Note: The username mapping is handled by create_if_missing which generates 
            # a placeholder if missing. Gender is handled by the Clerk service directly.
            
            logger.info(f"Successfully synced Clerk user {clerk_user_id} to DB (id={student.id})")

        elif event_type == "user.deleted":
            student = student_repo.get_by_clerk_id(clerk_user_id)
            if student:
                # We can safely delete the student. Cascade rules on student_subjects will clean up.
                db.delete(student)
                db.commit()
                logger.info(f"Successfully deleted user {clerk_user_id} from DB")
            else:
                logger.info(f"User {clerk_user_id} not found in DB to delete, ignoring")
        else:
            logger.info(f"Unhandled Clerk webhook event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing Clerk webhook {event_type}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error processing webhook")

    return {"ok": True, "type": event_type, "user_id": clerk_user_id}
