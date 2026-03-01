# Gap Analysis — Copilot Adapter (this repo) vs Agent Framework GitHub Copilot

## 1. Purpose & Output Format

| Dimension | **This Repo** (`azure-ai-agentserver-copilot`) | **Agent Framework** (`agent_framework_github_copilot`) |
|---|---|---|
| **Goal** | Run Copilot as a Foundry hosted agent, exposing the **OpenAI Responses API (RAPI)** over HTTP/SSE | Wrap Copilot as an `agent_framework.BaseAgent`, exposing the **Agent Framework's `AgentResponse`/`AgentResponseUpdate`** abstractions |
| **Wire format** | RAPI SSE events (`response.created`, `response.output_text.delta`, `response.completed`, etc.) | Framework-native `AgentResponseUpdate` with `Content.from_text()` items |
| **Server** | Built-in FastAPI/uvicorn HTTP server on `:8088` | No server — it's a library; users embed it in their own application |

## 2. Copilot Event Handling — The Core Difference

### Events the **Agent Framework** processes (streaming):

| Copilot Event | Action |
|---|---|
| `ASSISTANT_MESSAGE_DELTA` | Yields `AgentResponseUpdate` with `delta_content` → `Content.from_text()` |
| `SESSION_IDLE` | Pushes `None` sentinel to stop the stream |
| `SESSION_ERROR` | Pushes `AgentException` to raise in the consumer |

**That's it — only 3 event types.** Everything else (`ASSISTANT_TURN_START`, `ASSISTANT_USAGE`, `ASSISTANT_MESSAGE`, `ASSISTANT_TURN_END`, `TOOL_EXECUTION_*`, `ASSISTANT_REASONING`, `SUBAGENT_*`, `SESSION_*`) is **silently discarded**.

For non-streaming, it uses `send_and_wait()` which only returns the final `ASSISTANT_MESSAGE` event.

### Events the **Copilot Adapter** (this repo) processes:

| Copilot Event | RAPI Output | Notes |
|---|---|---|
| `ASSISTANT_TURN_START` | `response.created`, `response.in_progress`, `response.output_item.added`, `response.content_part.added` | Tracks turn count, generates unique item IDs per turn |
| `ASSISTANT_MESSAGE_DELTA` | `response.output_text.delta` | Accumulates text for done events |
| `ASSISTANT_USAGE` | *(stored for `response.completed`)* | Extracts `input_tokens`, `output_tokens`, `total_tokens` |
| `ASSISTANT_MESSAGE` | Synthetic delta if no deltas arrived; stores pending text for deferred done-events | **Authoritative text source** |
| `ASSISTANT_TURN_END` | `response.output_text.done`, `response.content_part.done`, `response.output_item.done`, `response.completed` | Done-events **deferred** here to avoid proxy flush race |
| `SESSION_IDLE` | Safety-net `response.completed` if not already emitted | Prevents client hangs |
| `SESSION_ERROR` | `response.failed` with error details | |
| `ASSISTANT_REASONING` | *(logged at DEBUG)* | |
| `TOOL_EXECUTION_START` | *(OTel child span opened)* | MCP semconv attributes |
| `TOOL_EXECUTION_COMPLETE` | *(OTel child span closed)* | Result captured in span |

**9+ event types handled**, with a full streaming state machine.

## 3. Detailed Feature Gap Matrix

| Feature | This Repo | Agent Framework | Gap Direction |
|---|---|---|---|
| **Streaming state machine** | Full RAPI SSE lifecycle (created→in_progress→deltas→done→completed) | Flat delta stream, no lifecycle events | AF missing |
| **Turn tracking** | Multi-turn aware (tracks turn count, per-turn item IDs) | No turn awareness; deltas are flat | AF missing |
| **Usage/token data** | Extracted from `ASSISTANT_USAGE`, included in `response.completed` | **Completely discarded** | AF missing |
| **Non-streaming** | Iterates all events, extracts text from `ASSISTANT_MESSAGE` | Uses `send_and_wait()` (SDK does the work) | Equivalent (different mechanism) |
| **Tool execution OTel** | `TOOL_EXECUTION_START`/`COMPLETE` → OTel child spans with MCP semconv | **Not handled at all** | AF missing |
| **Tool execution events forwarded to client** | No (logged + traced, not in RAPI) | No | Both missing |
| **Reasoning events** | Logged at DEBUG level | **Discarded** | AF missing |
| **Session error handling** | `SESSION_ERROR` → `response.failed` event + logging | `SESSION_ERROR` → raises `AgentException` | Both handle, different mechanism |
| **Session management** | `Dict[conversation_id, CopilotSession]` in-memory cache | `AgentSession.service_session_id` with `resume_session()` | AF uses proper resume; this repo holds live sessions |
| **BYOK / Azure Foundry** | Full support (API key + Managed Identity + token refresh) | None — uses default GitHub Copilot auth only | This repo ahead |
| **Tool ACL** | Full YAML-based regex ACL (`ToolAcl`) with kind-specific rules | Callback-based `on_permission_request` handler | Different design; ACL is more declarative |
| **Permission handling** | ACL auto-evaluates; no user interaction | Callback — user provides handler; **default denies all** | AF more flexible but harder to use |
| **Custom tools** | Not supported — relies on Copilot's built-in tools | `FunctionTool` → `CopilotTool` conversion with `ToolInvocation`/`ToolResult` | AF significantly ahead |
| **MCP servers** | Not supported | Full `mcp_servers` config passthrough | AF ahead |
| **System message** | Not configurable (default Copilot system prompt) | `SystemMessageConfig` with `append`/`replace` modes | AF ahead |
| **File/image attachments** | Full support — base64 decoding, temp file materialisation, data URI parsing | Not supported | This repo ahead |
| **Event deduplication** | Yes — consecutive duplicate detection in `_iter_copilot_events` | No | This repo ahead |
| **Observability** | Full OTel spans (invoke_agent + tools/call child spans) + structured logging | Basic `logging` only | This repo significantly ahead |
| **Context providers** | Not supported | Full `BaseContextProvider` support | AF ahead |
| **Middleware** | Not supported | Full `AgentMiddlewareTypes` support | AF ahead |
| **Async context manager** | No (long-lived server) | Yes (`__aenter__`/`__aexit__` with start/stop) | AF cleaner lifecycle |
| **Settings resolution** | Env vars only (`AZURE_AI_FOUNDRY_*`, `COPILOT_*`) | `load_settings()` with env vars + .env files + explicit kwargs | AF more flexible |
| **Sub-agent events** | Documented as a gap (not in RAPI), silently dropped | **Completely ignored** | Both missing |
| **Session lifecycle events** | Documented as a gap, silently dropped | **Completely ignored** | Both missing |
| **Rich content types** | Documented as a gap (terminal, resource, resource_link collapse to text) | Only text content in `Content.from_text()` | Both limited |

## 4. How Each Handles the Copilot Event Stream — Side by Side

```
Copilot SDK emits:
  ASSISTANT_TURN_START
  ASSISTANT_MESSAGE_DELTA × N
  ASSISTANT_USAGE
  ASSISTANT_MESSAGE
  ASSISTANT_TURN_END
  [TOOL_EXECUTION_START / COMPLETE if tools]
  [repeat for multi-turn]
  SESSION_IDLE

┌─────────────────────────┐     ┌──────────────────────────────┐
│   Agent Framework        │     │   This Repo (Copilot Adapter) │
├─────────────────────────┤     ├──────────────────────────────┤
│ TURN_START    → ignore   │     │ TURN_START → response.created │
│                          │     │              response.in_progress │
│                          │     │              output_item.added │
│                          │     │              content_part.added │
│ MSG_DELTA     → yield    │     │ MSG_DELTA  → output_text.delta │
│   AgentResponseUpdate    │     │                               │
│ USAGE         → ignore   │     │ USAGE      → store for later  │
│ MESSAGE       → ignore*  │     │ MESSAGE    → synthetic delta  │
│   (*send_and_wait uses)  │     │              + store pending   │
│ TURN_END      → ignore   │     │ TURN_END   → text_done        │
│                          │     │              content_part.done │
│                          │     │              output_item.done  │
│                          │     │              response.completed│
│ TOOL_START    → ignore   │     │ TOOL_START → OTel span open   │
│ TOOL_COMPLETE → ignore   │     │ TOOL_COMPLETE→OTel span close │
│ SESSION_IDLE  → sentinel │     │ SESSION_IDLE→safety-net close │
│ SESSION_ERROR → exception│     │ SESSION_ERROR→response.failed │
│ REASONING     → ignore   │     │ REASONING  → debug log        │
└─────────────────────────┘     └──────────────────────────────┘
```

## 5. Key Architectural Differences

**Session Management:**
- **This repo**: Holds live `CopilotSession` objects in a `Dict[str, Any]` keyed by `conversation_id`. Sessions are never explicitly closed.
- **Agent Framework**: Uses `AgentSession.service_session_id` and calls `resume_session()` on the SDK. More resilient to process restarts but requires the SDK to support resume.

**Event Collection:**
- **This repo**: Custom `_iter_copilot_events()` async generator with `asyncio.Queue`, dedup, timeout, and proper `unsubscribe()` in `finally`.
- **Agent Framework**: Similar `asyncio.Queue` pattern in `_stream_updates()` but much simpler — no dedup, no timeout, no structured logging of events.

**Error Semantics:**
- **This repo**: Errors produce RAPI `response.failed` events with `ResponseError(code="server_error")`. The stream continues to function (SESSION_IDLE still processed).
- **Agent Framework**: Errors raise `AgentException` which aborts the stream.

## 6. What Each Should Learn from the Other

**Agent Framework should adopt from this repo:**
1. Token usage extraction from `ASSISTANT_USAGE` — currently completely lost
2. OTel tracing for tool executions — zero observability today
3. Event deduplication — reconnect artifacts cause duplicate events
4. `ASSISTANT_MESSAGE` as authoritative text source (not just deltas)
5. Turn-aware streaming (not flat deltas)

**This repo should adopt from Agent Framework:**
1. Custom tool support (`FunctionTool` → `CopilotTool` conversion)
2. MCP server configuration passthrough
3. System message configuration (append/replace modes)
4. Middleware and context provider extensibility
5. Proper session resume (instead of holding live sessions in memory)
6. Settings from .env files (not just env vars)

## 7. Shared Gaps (Neither handles)

Both projects silently discard these Copilot SDK events:
- `SUBAGENT_SELECTED/STARTED/COMPLETED/FAILED`
- `SESSION_CONTEXT_CHANGED`, `SESSION_MODEL_CHANGE`, `SESSION_MODE_CHANGED`
- `SESSION_TITLE_CHANGED`, `SESSION_PLAN_CHANGED`
- `SESSION_TRUNCATION`, `SESSION_COMPACTION_*`, `SESSION_SNAPSHOT_REWIND`
- `TOOL_EXECUTION_PROGRESS`, `TOOL_EXECUTION_PARTIAL_RESULT`
- `MCP_APPROVAL_REQUEST` (this repo uses ACL; AF uses callback — neither forwards to client)
- `HOOK_START/END`, `SKILL_INVOKED`
- Rich content types (terminal, resource, resource_link)
- `cache_read_tokens`, `cache_write_tokens`, `cost` from usage data
