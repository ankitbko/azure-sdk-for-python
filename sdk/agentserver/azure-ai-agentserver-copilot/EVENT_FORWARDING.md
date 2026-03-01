# Copilot Event Forwarding — Frontend Integration Guide

This document describes the event structure that the Copilot adapter sends
to clients via the OpenAI Responses API (RAPI) streaming protocol.  Use it
to implement rendering for Copilot-specific events that have no native RAPI
equivalent.

---

## How It Works

The adapter streams events as standard **Server-Sent Events (SSE)**.  Most
events follow the normal RAPI protocol (`response.created`,
`response.output_text.delta`, `response.completed`, etc.).

Copilot-specific events — tool execution, sub-agent delegation, reasoning,
session lifecycle — are embedded as **JSON payloads inside
`response.output_text.delta` events**.

```
data: {"type":"response.output_text.delta","delta":"{\"copilot_event\":\"TOOL_EXECUTION_START\",\"data\":{...}}"}
```

## Identifying Copilot Events

Every `response.output_text.delta` event carries a `delta` string field.

**Regular text deltas** contain plain text (the assistant's response):
```json
{"type": "response.output_text.delta", "delta": "Here is my answer..."}
```

**Copilot event deltas** contain a JSON string with a `copilot_event` key:
```json
{"type": "response.output_text.delta", "delta": "{\"copilot_event\":\"TOOL_EXECUTION_START\",\"data\":{...}}"}
```

### Detection Logic (pseudocode)

```typescript
function onDelta(delta: string) {
  // Fast check: copilot events always start with '{"copilot_event"'
  if (delta.startsWith('{"copilot_event"')) {
    const event = JSON.parse(delta);
    handleCopilotEvent(event.copilot_event, event.data);
  } else {
    // Regular text — append to message display
    appendText(delta);
  }
}
```

---

## Copilot Event Payload Format

Every copilot event delta has this structure:

```json
{
  "copilot_event": "EVENT_TYPE_NAME",
  "data": { ... }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `copilot_event` | `string` | The Copilot SDK event type name (e.g. `TOOL_EXECUTION_START`) |
| `data` | `object` | Event-specific data. Fields with `null` values are omitted. |

---

## Event Categories & Payloads

### 1. Tool Execution Events

These let you show "Running tool…" indicators, tool arguments, progress, and results.

#### `TOOL_EXECUTION_START`

Fired when the agent begins executing a tool.

```json
{
  "copilot_event": "TOOL_EXECUTION_START",
  "data": {
    "tool_name": "shell",
    "tool_call_id": "call_abc123",
    "mcp_server_name": "filesystem",
    "mcp_tool_name": "read_file",
    "arguments": {
      "path": "/tmp/foo.txt"
    }
  }
}
```

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| `tool_name` | `string` | Yes | Tool identifier (e.g. `shell`, `read`, `write`, `url`) |
| `tool_call_id` | `string` | Yes | Unique ID linking start/progress/complete events |
| `mcp_server_name` | `string` | No | MCP server name (for MCP tools only) |
| `mcp_tool_name` | `string` | No | MCP tool name (for MCP tools only) |
| `arguments` | `object` | No | Arguments passed to the tool |

**Suggested UI:** Show a spinner with the tool name, e.g. "⏳ Running shell…"

#### `TOOL_EXECUTION_PROGRESS`

Fired during long-running tool operations with status updates.

```json
{
  "copilot_event": "TOOL_EXECUTION_PROGRESS",
  "data": {
    "tool_name": "shell",
    "tool_call_id": "call_abc123",
    "progress_message": "Searching files..."
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `progress_message` | `string` | Human-readable progress text |

**Suggested UI:** Update the spinner text: "⏳ Searching files…"

#### `TOOL_EXECUTION_PARTIAL_RESULT`

Fired when a tool produces intermediate output before completion.

```json
{
  "copilot_event": "TOOL_EXECUTION_PARTIAL_RESULT",
  "data": {
    "tool_name": "shell",
    "tool_call_id": "call_abc123",
    "partial_output": "Found 3 matches in src/..."
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `partial_output` | `string` | Intermediate tool output |

**Suggested UI:** Show partial results in a collapsible panel below the spinner.

#### `TOOL_EXECUTION_COMPLETE`

Fired when tool execution finishes.

```json
{
  "copilot_event": "TOOL_EXECUTION_COMPLETE",
  "data": {
    "tool_name": "shell",
    "tool_call_id": "call_abc123",
    "success": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | `boolean` | Whether the tool executed successfully |
| `result` | `object` | Tool result (may be large; structure varies by tool) |

**Suggested UI:** Replace spinner with ✅ or ❌ indicator.

#### `TOOL_USER_REQUESTED`

Fired when a tool invocation was explicitly requested by the user.

```json
{
  "copilot_event": "TOOL_USER_REQUESTED",
  "data": {
    "tool_name": "shell",
    "tool_call_id": "call_abc123",
    "is_user_requested": true
  }
}
```

---

### 2. Sub-Agent / Delegation Events

These let you show which sub-agent is handling the request.

#### `SUBAGENT_SELECTED`

```json
{
  "copilot_event": "SUBAGENT_SELECTED",
  "data": {
    "agent_name": "code-search",
    "agent_description": "Searches code across the repository"
  }
}
```

**Suggested UI:** Show a label like "🤖 Delegated to code-search"

#### `SUBAGENT_STARTED`

```json
{
  "copilot_event": "SUBAGENT_STARTED",
  "data": {
    "agent_name": "code-search"
  }
}
```

#### `SUBAGENT_COMPLETED`

```json
{
  "copilot_event": "SUBAGENT_COMPLETED",
  "data": {
    "agent_name": "code-search"
  }
}
```

#### `SUBAGENT_FAILED`

```json
{
  "copilot_event": "SUBAGENT_FAILED",
  "data": {
    "agent_name": "code-search",
    "message": "timeout"
  }
}
```

**Suggested UI:** Show ❌ with failure reason.

---

### 3. Reasoning & Intent Events

These let you show chain-of-thought reasoning.

#### `ASSISTANT_REASONING`

Full reasoning text (non-streaming).

```json
{
  "copilot_event": "ASSISTANT_REASONING",
  "data": {
    "content": "Let me analyze this step by step. First, I need to find the file..."
  }
}
```

**Suggested UI:** Show in a collapsible "Thinking…" section with lighter text.

#### `ASSISTANT_REASONING_DELTA`

Streaming reasoning chunks (same as text deltas but for reasoning).

```json
{
  "copilot_event": "ASSISTANT_REASONING_DELTA",
  "data": {
    "delta_content": "thinking about the approach..."
  }
}
```

**Suggested UI:** Stream into the "Thinking…" section incrementally.

#### `ASSISTANT_INTENT`

Classified user intent.

```json
{
  "copilot_event": "ASSISTANT_INTENT",
  "data": {
    "intent": "code_search"
  }
}
```

---

### 4. Session Lifecycle Events

These let you react to session-level state changes.

#### `SESSION_MODEL_CHANGE`

```json
{
  "copilot_event": "SESSION_MODEL_CHANGE",
  "data": {
    "new_model": "o3",
    "previous_model": "gpt-4.1"
  }
}
```

**Suggested UI:** Show a subtle notice: "Model switched to o3"

#### `SESSION_MODE_CHANGED`

```json
{
  "copilot_event": "SESSION_MODE_CHANGED",
  "data": {
    "new_mode": "agent",
    "previous_mode": "ask"
  }
}
```

#### `SESSION_TITLE_CHANGED`

```json
{
  "copilot_event": "SESSION_TITLE_CHANGED",
  "data": {
    "title": "Fix authentication bug"
  }
}
```

**Suggested UI:** Update the conversation title in the sidebar.

#### `SESSION_PLAN_CHANGED`

```json
{
  "copilot_event": "SESSION_PLAN_CHANGED",
  "data": {
    "content": "1. Read the auth module\n2. Fix the token refresh\n3. Add tests"
  }
}
```

**Suggested UI:** Show/update a plan panel with checkable items.

#### `SESSION_CONTEXT_CHANGED`

```json
{
  "copilot_event": "SESSION_CONTEXT_CHANGED",
  "data": {
    "cwd": "/workspace/project",
    "git_root": "/workspace/project",
    "branch": "main"
  }
}
```

#### `SESSION_TRUNCATION`

```json
{
  "copilot_event": "SESSION_TRUNCATION",
  "data": {
    "messages_removed_during_truncation": 5,
    "tokens_removed_during_truncation": 2048,
    "token_limit": 128000
  }
}
```

**Suggested UI:** Subtle warning: "Context was truncated (2048 tokens removed)"

#### Other session events

`SESSION_START`, `SESSION_RESUME`, `SESSION_SHUTDOWN`, `SESSION_HANDOFF`,
`SESSION_SNAPSHOT_REWIND`, `SESSION_COMPACTION_START`,
`SESSION_COMPACTION_COMPLETE`, `SESSION_INFO`, `SESSION_WARNING`,
`SESSION_USAGE_INFO`, `SESSION_WORKSPACE_FILE_CHANGED`

These follow the same `{"copilot_event": "...", "data": {...}}` format.
Render or ignore based on your UI needs.

---

### 5. Hooks & Skills

#### `HOOK_START` / `HOOK_END`

```json
{
  "copilot_event": "HOOK_START",
  "data": {
    "hook_type": "pre_tool",
    "hook_invocation_id": "hook_123"
  }
}
```

#### `SKILL_INVOKED`

```json
{
  "copilot_event": "SKILL_INVOKED",
  "data": {
    "name": "code-review"
  }
}
```

---

## Complete Event Type Reference

All possible `copilot_event` values:

| Event Type | Category | Priority |
|-----------|----------|----------|
| `TOOL_EXECUTION_START` | Tool Execution | **High** — show to user |
| `TOOL_EXECUTION_PROGRESS` | Tool Execution | **High** — update progress |
| `TOOL_EXECUTION_PARTIAL_RESULT` | Tool Execution | Medium |
| `TOOL_EXECUTION_COMPLETE` | Tool Execution | **High** — close indicator |
| `TOOL_USER_REQUESTED` | Tool Execution | Low |
| `SUBAGENT_SELECTED` | Sub-Agent | **High** — show delegation |
| `SUBAGENT_STARTED` | Sub-Agent | Medium |
| `SUBAGENT_COMPLETED` | Sub-Agent | Medium |
| `SUBAGENT_FAILED` | Sub-Agent | **High** — show error |
| `ASSISTANT_REASONING` | Reasoning | **High** — show thinking |
| `ASSISTANT_REASONING_DELTA` | Reasoning | **High** — stream thinking |
| `ASSISTANT_INTENT` | Reasoning | Low |
| `SESSION_MODEL_CHANGE` | Session | Medium |
| `SESSION_MODE_CHANGED` | Session | Low |
| `SESSION_TITLE_CHANGED` | Session | Medium |
| `SESSION_PLAN_CHANGED` | Session | **High** — show plan |
| `SESSION_CONTEXT_CHANGED` | Session | Low |
| `SESSION_TRUNCATION` | Session | Medium |
| `SESSION_COMPACTION_START` | Session | Low |
| `SESSION_COMPACTION_COMPLETE` | Session | Low |
| `SESSION_START` | Session | Low |
| `SESSION_RESUME` | Session | Low |
| `SESSION_SHUTDOWN` | Session | Low |
| `SESSION_HANDOFF` | Session | Medium |
| `SESSION_SNAPSHOT_REWIND` | Session | Medium |
| `SESSION_INFO` | Session | Low |
| `SESSION_WARNING` | Session | Medium |
| `SESSION_USAGE_INFO` | Session | Low |
| `SESSION_WORKSPACE_FILE_CHANGED` | Session | Low |
| `HOOK_START` | Hooks | Low |
| `HOOK_END` | Hooks | Low |
| `SKILL_INVOKED` | Hooks | Medium |
| `PENDING_MESSAGES_MODIFIED` | System | Low |
| `SYSTEM_MESSAGE` | System | Low |
| `USER_MESSAGE` | System | Low |
| `ABORT` | System | Medium |
| `UNKNOWN` | System | Low |

---

## Implementation Example (TypeScript)

```typescript
interface CopilotEvent {
  copilot_event: string;
  data: Record<string, any>;
}

// Track active tool executions
const activeTools = new Map<string, { name: string; startTime: number }>();

function handleStreamDelta(delta: string) {
  if (delta.startsWith('{"copilot_event"')) {
    const event: CopilotEvent = JSON.parse(delta);
    handleCopilotEvent(event);
  } else {
    appendToMessage(delta);
  }
}

function handleCopilotEvent(event: CopilotEvent) {
  switch (event.copilot_event) {
    case 'TOOL_EXECUTION_START':
      activeTools.set(event.data.tool_call_id, {
        name: event.data.tool_name,
        startTime: Date.now(),
      });
      showToolSpinner(event.data.tool_call_id, event.data.tool_name);
      break;

    case 'TOOL_EXECUTION_PROGRESS':
      updateToolSpinner(event.data.tool_call_id, event.data.progress_message);
      break;

    case 'TOOL_EXECUTION_COMPLETE':
      const tool = activeTools.get(event.data.tool_call_id);
      const duration = tool ? Date.now() - tool.startTime : 0;
      hideToolSpinner(event.data.tool_call_id, event.data.success, duration);
      activeTools.delete(event.data.tool_call_id);
      break;

    case 'ASSISTANT_REASONING':
      showReasoningBlock(event.data.content);
      break;

    case 'ASSISTANT_REASONING_DELTA':
      appendToReasoningBlock(event.data.delta_content);
      break;

    case 'SUBAGENT_SELECTED':
      showSubAgentBadge(event.data.agent_name, event.data.agent_description);
      break;

    case 'SUBAGENT_FAILED':
      showSubAgentError(event.data.agent_name, event.data.message);
      break;

    case 'SESSION_TITLE_CHANGED':
      updateConversationTitle(event.data.title);
      break;

    case 'SESSION_PLAN_CHANGED':
      showPlanPanel(event.data.content);
      break;

    case 'SESSION_MODEL_CHANGE':
      showModelNotice(event.data.previous_model, event.data.new_model);
      break;

    default:
      console.debug('Unhandled copilot event:', event.copilot_event, event.data);
  }
}
```

---

## Important Notes

1. **These events do NOT appear in the final text.** The JSON deltas are not
   accumulated into `response.output_text.done` or `response.completed`.
   The final text only contains the assistant's actual response.

2. **Event ordering is guaranteed.** Events arrive in the order the Copilot
   SDK emits them. `TOOL_EXECUTION_START` always arrives before
   `TOOL_EXECUTION_COMPLETE` for the same `tool_call_id`.

3. **New event types may be added.** The Copilot SDK may add new event types
   in future versions. Your frontend should gracefully handle unknown
   `copilot_event` values (log and ignore).

4. **Data fields are optional.** Not all fields listed are always present.
   Only non-null values are included in the `data` object. Always use
   optional chaining or null checks.

5. **Tool call correlation.** Use `tool_call_id` to correlate
   `TOOL_EXECUTION_START` → `TOOL_EXECUTION_PROGRESS` →
   `TOOL_EXECUTION_COMPLETE` events for the same tool invocation.

6. **Standard RAPI events are unchanged.** `response.created`,
   `response.in_progress`, `response.output_text.done`,
   `response.completed`, etc. work exactly as documented in the
   OpenAI Responses API spec.
