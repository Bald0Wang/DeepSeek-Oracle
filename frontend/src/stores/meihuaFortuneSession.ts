import { divinateMeihua } from "../api";
import type { MeihuaDivinationRequest, MeihuaDivinationResponse } from "../types";

const currentLocalDateTime = () => {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mi = String(now.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
};

export interface MeihuaFortuneFormState {
  topic: string;
  occurredAt: string;
}

export interface MeihuaFortuneSessionState {
  form: MeihuaFortuneFormState;
  loading: boolean;
  error: string | null;
  result: MeihuaDivinationResponse | null;
  activeRequestId: string | null;
}

type Listener = (state: MeihuaFortuneSessionState) => void;

const STORAGE_KEY = "oracle:fortune:meihua:v1";
const listeners = new Set<Listener>();

const defaultState: MeihuaFortuneSessionState = {
  form: {
    topic: "这周是否适合推进岗位调整？",
    occurredAt: currentLocalDateTime(),
  },
  loading: false,
  error: null,
  result: null,
  activeRequestId: null,
};

const parsePersistedState = (): Partial<MeihuaFortuneSessionState> | null => {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<MeihuaFortuneSessionState>;
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
};

const persistState = (state: MeihuaFortuneSessionState) => {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        form: state.form,
        result: state.result,
      })
    );
  } catch {
    // Ignore persistence failures.
  }
};

const persistedState = parsePersistedState();

let sessionState: MeihuaFortuneSessionState = {
  ...defaultState,
  ...persistedState,
  form: {
    ...defaultState.form,
    ...(persistedState?.form || {}),
  },
  result: persistedState?.result || null,
  loading: false,
  error: null,
  activeRequestId: null,
};

const emit = () => {
  persistState(sessionState);
  for (const listener of listeners) {
    listener(sessionState);
  }
};

const setSessionState = (patch: Partial<MeihuaFortuneSessionState>) => {
  sessionState = { ...sessionState, ...patch };
  emit();
};

const createRequestId = () =>
  `meihua_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

export const getMeihuaFortuneSessionState = () => sessionState;

export const subscribeMeihuaFortuneSession = (listener: Listener) => {
  listeners.add(listener);
  listener(sessionState);
  return () => {
    listeners.delete(listener);
  };
};

export const updateMeihuaFortuneForm = (patch: Partial<MeihuaFortuneFormState>) => {
  setSessionState({
    form: {
      ...sessionState.form,
      ...patch,
    },
  });
};

export const clearMeihuaFortuneError = () => {
  if (!sessionState.error) {
    return;
  }
  setSessionState({ error: null });
};

export const setMeihuaFortuneError = (message: string | null) => {
  setSessionState({ error: message });
};

export const clearMeihuaFortuneSession = (options?: { keepForm?: boolean }) => {
  if (sessionState.loading) {
    return;
  }
  sessionState = {
    ...defaultState,
    form: options?.keepForm ? sessionState.form : defaultState.form,
  };
  emit();
};

export const startMeihuaDivinationTask = async (payload: MeihuaDivinationRequest) => {
  if (sessionState.loading) {
    return;
  }
  const requestId = createRequestId();
  setSessionState({
    loading: true,
    error: null,
    activeRequestId: requestId,
  });

  try {
    const response = await divinateMeihua(payload);
    if (sessionState.activeRequestId !== requestId) {
      return;
    }
    const data = response.data || null;
    if (!data) {
      throw new Error("梅花求签返回为空，请稍后重试。");
    }
    setSessionState({
      result: data,
      error: null,
    });
  } catch (error) {
    if (sessionState.activeRequestId !== requestId) {
      return;
    }
    const message = error instanceof Error ? error.message : "求签失败，请稍后重试。";
    setSessionState({ error: message });
  } finally {
    if (sessionState.activeRequestId === requestId) {
      setSessionState({
        loading: false,
        activeRequestId: null,
      });
    }
  }
};
