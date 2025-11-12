# Services V2 - Refactored Architecture

This folder contains the new simplified service architecture with clear separation of concerns.

## Architecture Overview

```
User Request
     ↓
UnifiedWorkflowService (orchestration only)
     ↓
UnifiedClassifierService (ALL decisions)
     ↓
UnifiedResponseService (text generation only)
     ↓
Response with Forms
```

## Key Principles

### 1. Clear Responsibilities
- **Classifier**: Makes ALL decisions (intent, actions, problems, solutions, forms)
- **Response**: ONLY generates user-friendly text
- **Workflow**: ONLY orchestrates (no decision logic)

### 2. No Duplicate Data
- Classification result is the single source of truth
- Minimal metadata in responses
- No `knowledge_hits` (Chroma removed)

### 3. Intent-Based Flow
Instead of complex branching, we detect user intent:
- `new_problem` - Fresh issue to diagnose
- `clarifying` - Answering our question
- `feedback_positive` - Solution worked
- `feedback_negative` - Solution didn't work
- `contradictory` - Text conflicts with image
- `out_of_scope` - Not dishwasher-related
- etc.

## Files

### `unified_classifier.py`
**Purpose**: Analyze input and make all decisions

**What it does**:
- Detects user intent from text + context + images
- Determines what to do next (suggest solution, ask question, show form, etc.)
- Identifies problem/cause/solution
- Provides detailed reasoning
- Handles edge cases (contradictions, out-of-scope, etc.)

**What it returns**: `ClassificationResult` with all decisions

**Key features**:
- Tracks attempted solutions (no repeats)
- Handles empty text + image analysis
- Detects contradictions (e.g., says "dirty" but image shows clean)
- One solution at a time strategy

### `unified_response.py`
**Purpose**: Generate friendly user-facing text

**What it does**:
- Takes classification decisions
- Generates appropriate response text
- Different instructions per action type
- NO decision-making

**What it returns**: `ResponseResult` with just text

**Key features**:
- Action-specific prompts
- Always explains WHY before WHAT
- Short 2-3 sentence responses
- Natural varied language

### `unified_workflow.py`
**Purpose**: Orchestrate the flow

**What it does**:
- Calls classifier → response generator
- Attaches forms based on classifier decisions
- Persists messages
- Tracks usage
- Updates session status

**Key features**:
- No complex branching logic
- Form attachment based on `next_action`
- Automatic solution tracking
- Usage logging for all AI calls

## Forms

Forms are attached based on `next_action`:
- `present_feedback_form` → "Did that help?" form
- `present_resolution_form` → "Is it resolved?" form
- `present_escalation_form` → "Escalate to human?" form

## Usage Tracking

All AI calls are automatically logged:
- Classification calls
- Response generation calls
- Image analysis calls

Tracked data:
- Model used
- Input/output tokens
- Cost estimates
- Request type

## Migration Path

To use the new services:

1. **Import from services_v2**:
   ```python
   from app.services_v2 import UnifiedWorkflowService
   ```

2. **Wire up dependencies** (see dependencies.py)

3. **Replace old endpoint handler**:
   ```python
   async def send_message(payload: AssistantMessageRequest):
       return await unified_workflow_service.handle_message(payload)
   ```

## Comparison with Old Services

### Old Architecture (services/)
- Multiple decision points spread across services
- Complex branching logic in workflow
- Duplicate data in metadata
- Form logic scattered
- Hard to trace decisions

### New Architecture (services_v2/)
- All decisions in one place (classifier)
- Simple linear flow
- Minimal metadata
- Form logic centralized
- Easy to trace and debug

## Debugging

Check logs for:
- `[UnifiedClassifier]` - Classification decisions
- `[UnifiedResponse]` - Response generation

All decisions include `reasoning` field explaining why.

## Testing Strategy

1. **Test classifier separately** - Does it make correct decisions?
2. **Test response separately** - Does it generate good text?
3. **Test workflow integration** - Does it orchestrate correctly?

## Future Improvements

- [ ] Better cause tracking (not just solutions)
- [ ] Support for multi-turn clarifications
- [ ] More sophisticated escalation logic
- [ ] A/B testing framework
