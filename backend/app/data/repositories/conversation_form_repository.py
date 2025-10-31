from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional
from uuid import UUID

from sqlmodel import select

from app.core.database import DatabaseProvider
from app.data.repositories.base_repository import BaseRepository
from app.data.schemas.models import (
    ConversationForm,
    ConversationFormField,
    ConversationFormFieldOption,
    ConversationFormResponse,
    FormInputType,
    FormStatus,
    utcnow,
)


class ConversationFormRepository(BaseRepository[ConversationForm]):
    """Data access helpers for dynamic conversation forms."""

    def __init__(self, db_provider: DatabaseProvider) -> None:
        super().__init__(db_provider, ConversationForm)

    async def list_by_session(self, session_id: UUID, limit: int = 20) -> List[ConversationForm]:
        async with self.db_provider.get_session() as session:
            stmt = (
                select(ConversationForm)
                .where(ConversationForm.session_id == session_id)
                .order_by(ConversationForm.updated_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def set_status(
        self,
        form_id: UUID,
        status: FormStatus,
        *,
        rejection_reason: Optional[str] = None,
    ) -> Optional[ConversationForm]:
        async with self.db_provider.get_session() as session:
            form = await session.get(ConversationForm, form_id)
            if not form:
                return None

            now = utcnow()
            form.status = status
            form.updated_at = now

            if status == FormStatus.SUBMITTED:
                form.submitted_at = now
                form.rejected_at = None
                form.rejection_reason = None
            elif status == FormStatus.REJECTED:
                form.rejected_at = now
                form.rejection_reason = rejection_reason
            else:
                form.submitted_at = None
                form.rejected_at = None
                form.rejection_reason = None

            session.add(form)
            await session.commit()
            await session.refresh(form)
            return form

    async def save_field_response(
        self,
        *,
        form_id: UUID,
        field_id: UUID,
        value: Optional[str] = None,
        selected_option_id: Optional[UUID] = None,
    ) -> ConversationFormResponse:
        """Persist or update a user's answer for a form field."""

        normalized_value = self._normalize_value(value)
        now = utcnow()

        async with self.db_provider.get_session() as session:
            stmt = (
                select(ConversationFormResponse)
                .where(ConversationFormResponse.form_id == form_id)
                .where(ConversationFormResponse.field_id == field_id)
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if existing:
                existing.value = normalized_value
                existing.selected_option_id = selected_option_id
                existing.updated_at = now
                session.add(existing)
                response = existing
            else:
                response = ConversationFormResponse(
                    form_id=form_id,
                    field_id=field_id,
                    value=normalized_value,
                    selected_option_id=selected_option_id,
                    created_at=now,
                    updated_at=now,
                )
                session.add(response)

            form = await session.get(ConversationForm, form_id)
            if form:
                form.updated_at = now
                session.add(form)

            await session.commit()
            await session.refresh(response)
            return response

    async def create_form_with_fields(
        self,
        *,
        session_id: UUID,
        title: str,
        description: Optional[str],
        fields: List[dict],
    ) -> ConversationForm:
        async with self.db_provider.get_session() as session:
            form = ConversationForm(
                session_id=session_id,
                title=title or None,
                description=description,
                status=FormStatus.IN_PROGRESS,
            )
            session.add(form)
            await session.flush()

            for position, field_payload in enumerate(fields):
                input_type_value = field_payload.get("input_type", FormInputType.TEXT.value)
                try:
                    input_type = FormInputType(input_type_value)
                except ValueError:
                    input_type = FormInputType.TEXT

                field = ConversationFormField(
                    form_id=form.id,
                    prompt=field_payload.get("question", ""),
                    input_type=input_type,
                    required=bool(field_payload.get("required", False)),
                    position=position,
                    placeholder=(field_payload.get("placeholder") or None),
                )
                session.add(field)
                await session.flush()

                options_payload = field_payload.get("options") or []
                for option_position, option_payload in enumerate(options_payload):
                    option = ConversationFormFieldOption(
                        field_id=field.id,
                        value=option_payload.get("value", option_payload.get("label", "option")),
                        label=option_payload.get("label", option_payload.get("value", "Option")),
                        position=option_position,
                    )
                    session.add(option)

            await session.commit()
            await session.refresh(form)
            return form

    async def get_form_context(self, session_id: UUID) -> List[dict]:
        """Return a compact snapshot of forms and their answered inputs for AI context."""

        async with self.db_provider.get_session() as session:
            form_stmt = (
                select(ConversationForm)
                .where(ConversationForm.session_id == session_id)
                .order_by(ConversationForm.created_at)
            )
            forms = list((await session.execute(form_stmt)).scalars().all())
            if not forms:
                return []

            form_ids = [form.id for form in forms]

            field_stmt = (
                select(ConversationFormField)
                .where(ConversationFormField.form_id.in_(form_ids))
                .order_by(ConversationFormField.form_id, ConversationFormField.position)
            )
            fields = list((await session.execute(field_stmt)).scalars().all())
            field_ids = [field.id for field in fields]

            options: List[ConversationFormFieldOption] = []
            if field_ids:
                option_stmt = (
                    select(ConversationFormFieldOption)
                    .where(ConversationFormFieldOption.field_id.in_(field_ids))
                    .order_by(ConversationFormFieldOption.field_id, ConversationFormFieldOption.position)
                )
                options = list((await session.execute(option_stmt)).scalars().all())

            responses: List[ConversationFormResponse] = []
            if field_ids:
                response_stmt = (
                    select(ConversationFormResponse)
                    .where(ConversationFormResponse.field_id.in_(field_ids))
                )
                responses = list((await session.execute(response_stmt)).scalars().all())

        option_lookup: Dict[UUID, ConversationFormFieldOption] = {}
        for option in options:
            option_lookup[option.id] = option

        response_by_field: Dict[UUID, ConversationFormResponse] = {
            response.field_id: response for response in responses
        }

        fields_by_form: Dict[UUID, List[ConversationFormField]] = defaultdict(list)
        for field in fields:
            fields_by_form[field.form_id].append(field)

        context: List[dict] = []
        for form in forms:
            inputs: List[dict] = []
            for field in fields_by_form.get(form.id, []):
                response = response_by_field.get(field.id)
                if not response:
                    continue

                answer_value: Optional[str] = None
                if response.selected_option_id:
                    option = option_lookup.get(response.selected_option_id)
                    answer_value = option.label if option else response.value
                else:
                    answer_value = response.value

                if answer_value is None:
                    continue

                inputs.append(
                    {
                        "question": field.prompt,
                        "type": field.input_type.value,
                        "answer": answer_value,
                    }
                )

            context.append(
                {
                    "form_id": str(form.id),
                    "title": form.title or "",
                    "status": form.status.value,
                    "updated_at": self._format_timestamp(form.updated_at),
                    "submitted_at": self._format_timestamp(form.submitted_at),
                    "rejected_at": self._format_timestamp(form.rejected_at),
                    "rejection_reason": form.rejection_reason,
                    "inputs": inputs,
                }
            )

        return [
            item
            for item in context
            if item["inputs"]
            or item["status"] in (FormStatus.REJECTED.value, FormStatus.SUBMITTED.value)
        ]

    @staticmethod
    def _normalize_value(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, bool):
            return "yes" if value else "no"
        text = str(value).strip()
        return text or None

    @staticmethod
    def _format_timestamp(timestamp) -> Optional[str]:
        if not timestamp:
            return None
        return timestamp.replace(microsecond=0).isoformat()