import { getStoredUser } from "./auth";

const LEGACY_TASK_KEY = "oracle:last_task_id";
const TASK_KEY_PREFIX = "oracle:last_task_id:v2";

const resolveTaskKey = () => {
  const user = getStoredUser();
  const userId = user?.id;
  if (!userId) {
    return LEGACY_TASK_KEY;
  }
  return `${TASK_KEY_PREFIX}:${userId}`;
};

const migrateLegacyIfNeeded = () => {
  const currentKey = resolveTaskKey();
  if (currentKey === LEGACY_TASK_KEY) {
    return;
  }
  const scoped = window.localStorage.getItem(currentKey);
  if (scoped) {
    window.localStorage.removeItem(LEGACY_TASK_KEY);
    return;
  }
  const legacy = window.localStorage.getItem(LEGACY_TASK_KEY);
  if (!legacy) {
    return;
  }
  window.localStorage.setItem(currentKey, legacy);
  window.localStorage.removeItem(LEGACY_TASK_KEY);
};

export const getLastTaskId = () => {
  migrateLegacyIfNeeded();
  return window.localStorage.getItem(resolveTaskKey()) || "";
};

export const setLastTaskId = (taskId: string) => {
  if (!taskId) {
    return;
  }
  migrateLegacyIfNeeded();
  window.localStorage.setItem(resolveTaskKey(), taskId);
};

export const clearLastTaskId = () => {
  window.localStorage.removeItem(resolveTaskKey());
  window.localStorage.removeItem(LEGACY_TASK_KEY);
};

