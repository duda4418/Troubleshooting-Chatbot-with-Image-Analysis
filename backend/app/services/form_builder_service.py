"""Form builder service - generates forms based on next action."""
from __future__ import annotations

from app.data.DTO.message_flow_dto import GeneratedForm, GeneratedFormField, GeneratedFormOption
from app.data.DTO.simplified_flow_dto import NextAction


class FormBuilderService:
    """Builds forms based on classification decisions."""
    
    def build_form(self, next_action: NextAction) -> GeneratedForm | None:
        """Build a form based on the next action."""
        if next_action == NextAction.PRESENT_FEEDBACK_FORM:
            return self._build_feedback_form()
        elif next_action == NextAction.PRESENT_RESOLUTION_FORM:
            return self._build_resolution_form()
        elif next_action == NextAction.PRESENT_ESCALATION_FORM:
            return self._build_escalation_form()
        return None
    
    def _build_feedback_form(self) -> GeneratedForm:
        """Build the 'Did that help?' feedback form."""
        return GeneratedForm(
            title="Did that help?",
            description="Let us know if this suggestion worked for you",
            fields=[
                GeneratedFormField(
                    question="Was this helpful?",
                    input_type="single_choice",
                    required=True,
                    options=[
                        GeneratedFormOption(value="yes", label="Yes, it worked!"),
                        GeneratedFormOption(value="no", label="No, still having issues"),
                    ],
                )
            ],
        )
    
    def _build_resolution_form(self) -> GeneratedForm:
        """Build the 'Is it resolved?' form."""
        return GeneratedForm(
            title="Is your issue resolved?",
            description="Please confirm if your problem has been fixed",
            fields=[
                GeneratedFormField(
                    question="Is the problem resolved?",
                    input_type="single_choice",
                    required=True,
                    options=[
                        GeneratedFormOption(value="yes", label="Yes, problem is fixed"),
                        GeneratedFormOption(value="no", label="No, still not working"),
                    ],
                )
            ],
        )
    
    def _build_escalation_form(self) -> GeneratedForm:
        """Build the escalation form for human support."""
        return GeneratedForm(
            title="Contact Support?",
            description="Would you like us to connect you with a specialist?",
            fields=[
                GeneratedFormField(
                    question="Do you want to escalate to human support?",
                    input_type="single_choice",
                    required=True,
                    options=[
                        GeneratedFormOption(value="yes", label="Yes, please escalate"),
                        GeneratedFormOption(value="no", label="No, I'll keep trying"),
                    ],
                )
            ],
        )
