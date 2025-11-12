"""Services V2 - Refactored architecture with clear separation of concerns.

This package contains the new simplified service architecture:
- unified_classifier: Makes ALL decisions (intent, actions, forms, solutions)
- unified_response: Just generates friendly text based on decisions
- unified_workflow: Orchestrates the new flow
- form_builder_service: Builds forms based on next action
- session_manager_service: Handles session listing, history, and feedback

Old services remain in /services for comparison.
"""

from .unified_classifier import UnifiedClassifierService
from .unified_response import UnifiedResponseService
from .unified_workflow import UnifiedWorkflowService
from .form_builder_service import FormBuilderService
from .session_manager_service import SessionManagerService

__all__ = [
    "UnifiedClassifierService",
    "UnifiedResponseService",
    "UnifiedWorkflowService",
    "FormBuilderService",
    "SessionManagerService",
]
