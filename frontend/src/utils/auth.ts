import type { UserProfile } from "../types";


const TOKEN_KEY = "oracle:access_token";
const USER_KEY = "oracle:current_user";


export const getAccessToken = () => window.localStorage.getItem(TOKEN_KEY) || "";

export const setAuthData = (token: string, user: UserProfile) => {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const clearAuthData = () => {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
};

export const getStoredUser = (): UserProfile | null => {
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as UserProfile;
  } catch {
    return null;
  }
};
