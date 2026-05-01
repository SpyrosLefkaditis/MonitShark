// Chat protocol types — mirror the WebSocket envelope from backend/app/agent/*.

export type ServerFrame =
  | { type: "token"; text: string }
  | { type: "tool_call"; id: string; name: string; args: unknown }
  | { type: "tool_result"; id: string; name: string; output: unknown; ok: boolean }
  | {
      type: "confirm_request";
      request_id: string;
      action: string;
      args: unknown;
      summary: string;
      risk: string;
    }
  | { type: "final"; text: string }
  | { type: "error"; message: string };

export type ClientFrame =
  | { type: "user"; text: string }
  | { type: "confirm"; request_id: string; decision: "approve" | "deny" };

// Internal UI message shapes.
export type UserMessage = {
  kind: "user";
  id: string;
  text: string;
};

export type AssistantMessage = {
  kind: "assistant";
  id: string;
  text: string;
  /** True while we're still streaming tokens; false after `final` (or once another bubble starts). */
  streaming: boolean;
};

export type ToolCallMessage = {
  kind: "tool_call";
  id: string;
  name: string;
  args: unknown;
  status: "running" | "done";
  ok?: boolean;
  output?: unknown;
};

export type ConfirmationMessage = {
  kind: "confirmation";
  id: string;
  request_id: string;
  action: string;
  args: unknown;
  summary: string;
  risk: string;
  /** "pending" until user clicks Allow/Deny. */
  decision: "pending" | "approve" | "deny";
};

export type ErrorMessage = {
  kind: "error";
  id: string;
  text: string;
};

export type ChatMessage =
  | UserMessage
  | AssistantMessage
  | ToolCallMessage
  | ConfirmationMessage
  | ErrorMessage;

export type ChatState = {
  messages: ChatMessage[];
  /** Index into `messages` of the currently-streaming assistant bubble (so tokens append fast). */
  activeAssistantIndex: number | null;
  /** True while a confirm_request is unresolved — input is locked. */
  awaitingConfirmation: boolean;
};

export const initialChatState: ChatState = {
  messages: [],
  activeAssistantIndex: null,
  awaitingConfirmation: false,
};
