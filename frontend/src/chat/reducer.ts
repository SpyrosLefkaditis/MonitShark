import type {
  AssistantMessage,
  ChatMessage,
  ChatState,
  ConfirmationMessage,
  ServerFrame,
  ToolCallMessage,
} from "./types";

let idCounter = 0;
function nextId(prefix: string): string {
  idCounter += 1;
  return `${prefix}-${Date.now()}-${idCounter}`;
}

export type ChatAction =
  | { type: "send_user"; text: string }
  | { type: "server_frame"; frame: ServerFrame }
  | { type: "resolve_confirmation"; request_id: string; decision: "approve" | "deny" }
  | { type: "clear" };

function appendOrUpdate(
  messages: ChatMessage[],
  predicate: (m: ChatMessage) => boolean,
  next: (m?: ChatMessage) => ChatMessage,
): ChatMessage[] {
  const idx = messages.findIndex(predicate);
  if (idx === -1) return [...messages, next()];
  const copy = messages.slice();
  copy[idx] = next(messages[idx]);
  return copy;
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "send_user": {
      const messages = state.messages.concat({
        kind: "user",
        id: nextId("u"),
        text: action.text,
      });
      return { ...state, messages, activeAssistantIndex: null };
    }

    case "server_frame": {
      const frame = action.frame;
      switch (frame.type) {
        case "token": {
          if (state.activeAssistantIndex !== null) {
            const messages = state.messages.slice();
            const cur = messages[state.activeAssistantIndex] as AssistantMessage;
            messages[state.activeAssistantIndex] = {
              ...cur,
              text: cur.text + frame.text,
              streaming: true,
            };
            return { ...state, messages };
          }
          const newMsg: AssistantMessage = {
            kind: "assistant",
            id: nextId("a"),
            text: frame.text,
            streaming: true,
          };
          const messages = state.messages.concat(newMsg);
          return { ...state, messages, activeAssistantIndex: messages.length - 1 };
        }

        case "final": {
          if (state.activeAssistantIndex !== null) {
            const messages = state.messages.slice();
            const cur = messages[state.activeAssistantIndex] as AssistantMessage;
            messages[state.activeAssistantIndex] = {
              ...cur,
              text: frame.text,
              streaming: false,
            };
            return { ...state, messages, activeAssistantIndex: null };
          }
          const newMsg: AssistantMessage = {
            kind: "assistant",
            id: nextId("a"),
            text: frame.text,
            streaming: false,
          };
          return {
            ...state,
            messages: state.messages.concat(newMsg),
            activeAssistantIndex: null,
          };
        }

        case "tool_call": {
          // Close out any in-progress assistant bubble so subsequent tokens start a new one.
          let messages = state.messages;
          if (state.activeAssistantIndex !== null) {
            messages = messages.slice();
            const cur = messages[state.activeAssistantIndex] as AssistantMessage;
            messages[state.activeAssistantIndex] = { ...cur, streaming: false };
          }
          const tc: ToolCallMessage = {
            kind: "tool_call",
            id: frame.id,
            name: frame.name,
            args: frame.args,
            status: "running",
          };
          return {
            ...state,
            messages: messages.concat(tc),
            activeAssistantIndex: null,
          };
        }

        case "tool_result": {
          const messages = appendOrUpdate(
            state.messages,
            (m) => m.kind === "tool_call" && m.id === frame.id,
            (existing) =>
              existing
                ? {
                    ...(existing as ToolCallMessage),
                    status: "done",
                    ok: frame.ok,
                    output: frame.output,
                  }
                : {
                    kind: "tool_call",
                    id: frame.id,
                    name: frame.name,
                    args: undefined,
                    status: "done",
                    ok: frame.ok,
                    output: frame.output,
                  },
          );
          return { ...state, messages };
        }

        case "confirm_request": {
          const conf: ConfirmationMessage = {
            kind: "confirmation",
            id: nextId("c"),
            request_id: frame.request_id,
            action: frame.action,
            args: frame.args,
            summary: frame.summary,
            risk: frame.risk,
            decision: "pending",
          };
          let messages = state.messages;
          if (state.activeAssistantIndex !== null) {
            messages = messages.slice();
            const cur = messages[state.activeAssistantIndex] as AssistantMessage;
            messages[state.activeAssistantIndex] = { ...cur, streaming: false };
          }
          return {
            ...state,
            messages: messages.concat(conf),
            activeAssistantIndex: null,
            awaitingConfirmation: true,
          };
        }

        case "error": {
          return {
            ...state,
            messages: state.messages.concat({
              kind: "error",
              id: nextId("e"),
              text: frame.message,
            }),
            activeAssistantIndex: null,
          };
        }
      }
      return state;
    }

    case "resolve_confirmation": {
      const messages = state.messages.map((m) => {
        if (m.kind !== "confirmation") return m;
        if (m.request_id !== action.request_id) return m;
        return { ...m, decision: action.decision };
      });
      return { ...state, messages, awaitingConfirmation: false };
    }

    case "clear":
      return { messages: [], activeAssistantIndex: null, awaitingConfirmation: false };

    default:
      return state;
  }
}
