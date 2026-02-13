import { divinateZiwei } from "../api";
import type { BirthInfo, ZiweiDivinationRequest, ZiweiDivinationResponse } from "../types";

export interface ZiweiFortuneFormState {
  question: string;
  calendar: BirthInfo["calendar"];
  year: string;
  month: string;
  day: string;
  hour: string;
  minute: string;
  gender: BirthInfo["gender"];
}

export interface ZiweiFortuneSessionState {
  form: ZiweiFortuneFormState;
  loading: boolean;
  error: string | null;
  result: ZiweiDivinationResponse | null;
  activeRequestId: string | null;
}

type Listener = (state: ZiweiFortuneSessionState) => void;

const STORAGE_KEY_BASE = "oracle:fortune:ziwei:v2";
const LEGACY_STORAGE_KEY = "oracle:fortune:ziwei:v1";
const USER_KEY = "oracle:current_user";
const listeners = new Set<Listener>();

const defaultState: ZiweiFortuneSessionState = {
  form: {
    question: "请结合我的命盘，给我近期与中长期的趋势建议。",
    calendar: "lunar",
    year: "2000",
    month: "1",
    day: "1",
    hour: "0",
    minute: "1",
    gender: "男",
  },
  loading: false,
  error: null,
  result: null,
  activeRequestId: null,
};

const resolveStorageKey = (): string => {
  if (typeof window === "undefined") {
    return STORAGE_KEY_BASE;
  }
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    if (!raw) {
      return STORAGE_KEY_BASE;
    }
    const user = JSON.parse(raw) as { id?: number | string };
    const userId = String(user?.id || "").trim();
    if (!userId) {
      return STORAGE_KEY_BASE;
    }
    return `${STORAGE_KEY_BASE}:${userId}`;
  } catch {
    return STORAGE_KEY_BASE;
  }
};

const normalizeForm = (value: Partial<ZiweiFortuneFormState> | null | undefined): ZiweiFortuneFormState => ({
  question: typeof value?.question === "string" ? value.question : defaultState.form.question,
  calendar: value?.calendar === "solar" ? "solar" : "lunar",
  year: typeof value?.year === "string" ? value.year : defaultState.form.year,
  month: typeof value?.month === "string" ? value.month : defaultState.form.month,
  day: typeof value?.day === "string" ? value.day : defaultState.form.day,
  hour: typeof value?.hour === "string" ? value.hour : defaultState.form.hour,
  minute: typeof value?.minute === "string" ? value.minute : defaultState.form.minute,
  gender: value?.gender === "女" ? "女" : "男",
});

const parsePersistedForm = (): ZiweiFortuneFormState | null => {
  if (typeof window === "undefined") {
    return null;
  }
  const storageKey = resolveStorageKey();
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      const legacyRaw = window.localStorage.getItem(LEGACY_STORAGE_KEY);
      if (!legacyRaw) {
        return null;
      }
      const legacyParsed = JSON.parse(legacyRaw) as { form?: Partial<ZiweiFortuneFormState> };
      const legacyForm = normalizeForm(legacyParsed?.form);
      window.localStorage.setItem(storageKey, JSON.stringify({ form: legacyForm }));
      window.localStorage.removeItem(LEGACY_STORAGE_KEY);
      return legacyForm;
    }
    const parsed = JSON.parse(raw) as { form?: Partial<ZiweiFortuneFormState> };
    if (!parsed || typeof parsed !== "object" || !parsed.form) {
      return null;
    }
    return normalizeForm(parsed.form);
  } catch {
    return null;
  }
};

const persistState = (state: ZiweiFortuneSessionState) => {
  if (typeof window === "undefined") {
    return;
  }
  try {
    const storageKey = resolveStorageKey();
    window.localStorage.setItem(
      storageKey,
      JSON.stringify({
        form: state.form,
      })
    );
  } catch {
    // Ignore persistence failures.
  }
};

const persistedForm = parsePersistedForm();

let sessionState: ZiweiFortuneSessionState = {
  ...defaultState,
  form: persistedForm || defaultState.form,
  result: null,
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

const setSessionState = (patch: Partial<ZiweiFortuneSessionState>) => {
  sessionState = { ...sessionState, ...patch };
  emit();
};

const createRequestId = () =>
  `ziwei_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

export const getZiweiFortuneSessionState = () => sessionState;

export const subscribeZiweiFortuneSession = (listener: Listener) => {
  listeners.add(listener);
  listener(sessionState);
  return () => {
    listeners.delete(listener);
  };
};

export const updateZiweiFortuneForm = (patch: Partial<ZiweiFortuneFormState>) => {
  setSessionState({
    form: {
      ...sessionState.form,
      ...patch,
    },
  });
};

export const clearZiweiFortuneError = () => {
  if (!sessionState.error) {
    return;
  }
  setSessionState({ error: null });
};

export const setZiweiFortuneError = (message: string | null) => {
  setSessionState({ error: message });
};

export const clearZiweiFortuneSession = (options?: { keepForm?: boolean }) => {
  if (sessionState.loading) {
    return;
  }
  sessionState = {
    ...defaultState,
    form: options?.keepForm ? sessionState.form : defaultState.form,
  };
  emit();
};

export const startZiweiDivinationTask = async (payload: ZiweiDivinationRequest) => {
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
    const response = await divinateZiwei(payload);
    if (sessionState.activeRequestId !== requestId) {
      return;
    }
    const data = response.data || null;
    if (!data) {
      throw new Error("紫微求签返回为空，请稍后重试。");
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
