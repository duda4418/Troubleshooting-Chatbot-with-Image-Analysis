import logging
from typing import Optional
from uuid import UUID

from app.data.repositories.conversation_session_repository import ConversationSessionRepository

logger = logging.getLogger(__name__)


class FormHandlerService:
    """Handles form submissions and determines appropriate actions."""
    
    def __init__(
        self,
        *,
        session_repository: ConversationSessionRepository,
    ):
        self._session_repo = session_repository
    
    async def handle_form_response(
        self,
        session_id: UUID,
        form_response: dict,
    ) -> Optional[dict]:
        """
        Handle form submission and determine action.
        
        Returns:
            - None if conversation should continue normally (NO selected)
            - dict with action details if conversation should be closed or special handling
        """
        fields = form_response.get("fields", [])
        form_id = form_response.get("form_id", "")
        
        logger.info(f"Processing form submission: form_id={form_id}")
        logger.info(f"Fields received: {fields}")
        
        # Extract field values - check both 'field_id' and 'id' for compatibility
        is_resolved = None
        escalate_confirmed = None
        
        for field in fields:
            field_id = field.get("field_id") or field.get("id", "")
            value = field.get("value")
            label = field.get("label", "")
            
            logger.info(f"  Field: id={field_id}, value={value}, label={label}")
            
            # Match by field_id first, then by label text as fallback
            if field_id == "is_resolved" or "problem resolved" in label.lower():
                is_resolved = value == "yes"
                logger.info(f"  → Detected resolution form: is_resolved={is_resolved}")
            elif field_id == "escalate_confirmed" or "escalate to human" in label.lower():
                escalate_confirmed = value == "yes"
                logger.info(f"  → Detected escalation form: escalate_confirmed={escalate_confirmed}")
        
        # Resolution form
        if is_resolved is not None:
            if is_resolved:
                logger.info("User confirmed problem is RESOLVED - closing session")
                await self._session_repo.set_status(session_id, "resolved")
                
                return {
                    "action": "close_resolved",
                    "reply": "Great! I'm glad the issue is resolved. Feel free to start a new conversation if you need help again.",
                }
            else:
                logger.info("User indicated problem NOT RESOLVED - continuing with context")
                return None  # Continue flow normally, AI will see the NO in context
        
        # Escalation form
        elif escalate_confirmed is not None:
            if escalate_confirmed:
                logger.info("User confirmed ESCALATION - escalating session")
                await self._session_repo.set_status(session_id, "escalated")
                
                return {
                    "action": "escalate",
                    "reply": "I've escalated your issue to our support team. They'll reach out to you shortly.",
                }
            else:
                logger.info("User declined escalation - continuing with context")
                return None  # Continue flow normally
        
        # Unknown form type
        else:
            logger.warning(f"Unknown form type - is_resolved={is_resolved}, escalate_confirmed={escalate_confirmed}")
            logger.warning(f"Form response data: {form_response}")
            return None  # Continue flow normally
