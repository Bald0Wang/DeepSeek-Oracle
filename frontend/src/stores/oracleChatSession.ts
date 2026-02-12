import { oracleChat, oracleChatStream } from "../api";
import type {
  DisclaimerLevel,
  OracleActionItem,
  OracleChatRequest,
  OracleChatResponse,
  OracleToolEvent,
} from "../types";


export interface OracleThinkingItem {
  tool_name: string;
  display_name: string;
  status: "running" | "success" | "error";
  elapsed_ms?: number | null;
}

export interface OracleConversationTurn {
  id: string;
  query: string;
  createdAt: number;
  status: "running" | "succeeded" | "failed";
  planSteps: OracleThinkingItem[];
  answerText: string;
  actionItems: OracleActionItem[];
  followUpQuestions: string[];
  safetyDisclaimerLevel: DisclaimerLevel;
  error: string | null;
}

export interface OracleChatSessionState {
  loading: boolean;
  activeTurnId: string | null;
  error: string | null;
  turns: OracleConversationTurn[];
  startedAt: number | null;
}

type Listener = (state: OracleChatSessionState) => void;

let sessionState: OracleChatSessionState = {
  loading: false,
  activeTurnId: null,
  error: null,
  turns: [],
  startedAt: null,
};

let runVersion = 0;
const listeners = new Set<Listener>();

const emit = () => {
  for (const listener of listeners) {
    listener(sessionState);
  }
};

const setSessionState = (patch: Partial<OracleChatSessionState>) => {
  sessionState = { ...sessionState, ...patch };
  emit();
};

const createTurnId = () =>
  `turn_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

const updateTurn = (turnId: string, updater: (turn: OracleConversationTurn) => OracleConversationTurn) => {
  setSessionState({
    turns: sessionState.turns.map((turn) => (turn.id === turnId ? updater(turn) : turn)),
  });
};

const applyToolEvent = (turnId: string, event: OracleToolEvent) => {
  updateTurn(turnId, (turn) => {
    const nextSteps = [...turn.planSteps];
    const runningIndex = [...nextSteps].reverse().findIndex(
      (item) => item.tool_name === event.tool_name && item.status === "running"
    );

    if (event.status === "running" || runningIndex === -1) {
      nextSteps.push({
        tool_name: event.tool_name,
        display_name: event.display_name,
        status: event.status,
        elapsed_ms: event.elapsed_ms ?? undefined,
      });
      return { ...turn, planSteps: nextSteps };
    }

    const realIndex = nextSteps.length - runningIndex - 1;
    nextSteps[realIndex] = {
      ...nextSteps[realIndex],
      status: event.status,
      elapsed_ms: event.elapsed_ms ?? nextSteps[realIndex].elapsed_ms,
    };
    return { ...turn, planSteps: nextSteps };
  });
};

const applyFinalResult = (turnId: string, result: OracleChatResponse) => {
  updateTurn(turnId, (turn) => ({
    ...turn,
    status: "succeeded",
    answerText: result.answer_text,
    actionItems: result.action_items,
    followUpQuestions: result.follow_up_questions,
    safetyDisclaimerLevel: result.safety_disclaimer_level,
    error: null,
  }));
};

const applyFailure = (turnId: string, message: string) => {
  updateTurn(turnId, (turn) => ({
    ...turn,
    status: "failed",
    error: message,
  }));
};

export const getOracleChatSessionState = () => sessionState;

export const subscribeOracleChatSession = (listener: Listener) => {
  listeners.add(listener);
  listener(sessionState);
  return () => {
    listeners.delete(listener);
  };
};

export const clearOracleChatSession = () => {
  if (sessionState.loading) {
    return;
  }
  sessionState = {
    loading: false,
    activeTurnId: null,
    error: null,
    turns: [],
    startedAt: null,
  };
  emit();
};

export const startOracleChatSession = async (payload: OracleChatRequest) => {
  const currentRun = ++runVersion;
  const turnId = createTurnId();
  const newTurn: OracleConversationTurn = {
    id: turnId,
    query: payload.user_query,
    createdAt: Date.now(),
    status: "running",
    planSteps: [],
    answerText: "",
    actionItems: [],
    followUpQuestions: [],
    safetyDisclaimerLevel: "none",
    error: null,
  };
  setSessionState({
    loading: true,
    activeTurnId: turnId,
    error: null,
    turns: [...sessionState.turns, newTurn],
    startedAt: Date.now(),
  });

  try {
    const streamResult = await oracleChatStream(payload, (streamEvent) => {
      if (runVersion !== currentRun) {
        return;
      }

      if (streamEvent.event === "tool_start") {
        applyToolEvent(turnId, {
          tool_name: streamEvent.data.tool_name,
          display_name: streamEvent.data.display_name,
          status: "running",
        });
      }
      if (streamEvent.event === "tool_end") {
        applyToolEvent(turnId, {
          tool_name: streamEvent.data.tool_name,
          display_name: streamEvent.data.display_name,
          status: "success",
          elapsed_ms: streamEvent.data.elapsed_ms,
        });
      }
      if (streamEvent.event === "tool_error") {
        applyToolEvent(turnId, {
          tool_name: streamEvent.data.tool_name,
          display_name: streamEvent.data.display_name,
          status: "error",
          elapsed_ms: streamEvent.data.elapsed_ms,
        });
      }
    });

    if (runVersion !== currentRun) {
      return;
    }
    applyFinalResult(turnId, streamResult);
    setSessionState({ error: null });
  } catch (streamError) {
    if (runVersion !== currentRun) {
      return;
    }

    try {
      const fallbackResponse = await oracleChat(payload);
      if (runVersion !== currentRun) {
        return;
      }
      const fallbackResult = fallbackResponse.data || null;
      if (fallbackResult?.tool_events) {
        for (const item of fallbackResult.tool_events) {
          applyToolEvent(turnId, item);
        }
      }
      if (fallbackResult) {
        applyFinalResult(turnId, fallbackResult);
      }
      setSessionState({ error: null });
    } catch {
      if (runVersion !== currentRun) {
        return;
      }
      const message = streamError instanceof Error ? streamError.message : "咨询失败，请稍后重试。";
      applyFailure(turnId, message);
      setSessionState({
        error: message,
      });
    }
  } finally {
    if (runVersion === currentRun) {
      setSessionState({
        loading: false,
        activeTurnId: null,
        startedAt: null,
      });
    }
  }
};
