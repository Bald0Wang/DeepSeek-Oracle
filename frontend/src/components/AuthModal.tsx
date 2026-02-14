import { FormEvent, useEffect, useState } from "react";

import { loginByEmail, registerByEmail, sendRegisterCode } from "../api";
import type { UserProfile } from "../types";
import { setAuthData } from "../utils/auth";
import { InkButton } from "./InkButton";

type AuthMode = "login" | "register";

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
  onAuthSuccess?: (user: UserProfile) => void;
  initialMode?: AuthMode;
}

export function AuthModal({ open, onClose, onAuthSuccess, initialMode = "login" }: AuthModalProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode);

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginMessage, setLoginMessage] = useState<string | null>(null);

  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerEmailCode, setRegisterEmailCode] = useState("");
  const [registerInviteCode, setRegisterInviteCode] = useState("");
  const [registerLoading, setRegisterLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [registerMessage, setRegisterMessage] = useState<string | null>(null);

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode, open]);

  useEffect(() => {
    if (!open) {
      return () => {};
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose, open]);

  useEffect(() => {
    if (countdown <= 0) {
      return;
    }
    const timer = window.setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [countdown]);

  const handleLoginSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoginError(null);
    setLoginMessage(null);
    if (!loginEmail.trim() || !loginPassword.trim()) {
      setLoginError("请输入邮箱和密码。");
      return;
    }

    setLoginLoading(true);
    try {
      const response = await loginByEmail({
        email: loginEmail.trim(),
        password: loginPassword.trim(),
      });
      if (!response.data) {
        throw new Error("登录失败");
      }
      setAuthData(response.data.token, response.data.user);
      onAuthSuccess?.(response.data.user);
      onClose();
    } catch (error) {
      const apiMessage = (error as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setLoginError(apiMessage || (error instanceof Error ? error.message : "登录失败，请稍后重试。"));
    } finally {
      setLoginLoading(false);
    }
  };

  const handleSendRegisterCode = async () => {
    setRegisterError(null);
    setRegisterMessage(null);
    const email = registerEmail.trim();
    if (!email) {
      setRegisterError("请先输入邮箱。");
      return;
    }

    setSendingCode(true);
    try {
      const response = await sendRegisterCode({ email });
      const expireMinutes = response.data?.expire_minutes || 10;
      setRegisterMessage(`验证码已发送，请在 ${expireMinutes} 分钟内完成注册。`);
      setCountdown(60);
    } catch (error) {
      const apiMessage = (error as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setRegisterError(apiMessage || (error instanceof Error ? error.message : "发送验证码失败，请稍后重试。"));
    } finally {
      setSendingCode(false);
    }
  };

  const handleRegisterSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setRegisterError(null);
    setRegisterMessage(null);
    setLoginMessage(null);
    if (!registerEmail.trim() || !registerPassword.trim() || !registerEmailCode.trim()) {
      setRegisterError("请输入邮箱、验证码和密码。");
      return;
    }

    setRegisterLoading(true);
    try {
      const response = await registerByEmail({
        email: registerEmail.trim(),
        password: registerPassword.trim(),
        email_code: registerEmailCode.trim(),
        invite_code: registerInviteCode.trim() || undefined,
      });
      if (!response.data) {
        throw new Error("注册失败");
      }
      setRegisterPassword("");
      setRegisterEmailCode("");
      setRegisterInviteCode("");
      setCountdown(0);
      setMode("login");
      setLoginEmail(registerEmail.trim());
      setLoginPassword("");
      setLoginMessage("注册成功，请登录。");
    } catch (error) {
      const apiMessage = (error as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setRegisterError(apiMessage || (error instanceof Error ? error.message : "注册失败，请稍后重试。"));
    } finally {
      setRegisterLoading(false);
    }
  };

  if (!open) {
    return null;
  }

  return (
    <div
      className="auth-modal__backdrop"
      role="presentation"
      onClick={() => {
        onClose();
      }}
    >
      <div
        className="auth-modal__shell"
        onClick={(event) => {
          event.stopPropagation();
        }}
      >
        <section
          className="auth-modal"
          role="dialog"
          aria-modal="true"
          aria-label="登录注册弹窗"
        >
          <div className="auth-modal__tabs" role="tablist" aria-label="登录注册切换">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={`auth-modal__tab ${mode === "login" ? "auth-modal__tab--active" : ""}`}
              onClick={() => {
                setMode("login");
              }}
            >
              登录
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={`auth-modal__tab ${mode === "register" ? "auth-modal__tab--active" : ""}`}
              onClick={() => {
                setMode("register");
              }}
            >
              注册
            </button>
          </div>

          {mode === "login" ? (
            <form className="stack auth-modal__form" onSubmit={handleLoginSubmit}>
              <div className="field">
                <label className="field__label" htmlFor="auth-modal-login-email">邮箱</label>
                <input
                  id="auth-modal-login-email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={loginEmail}
                  onChange={(event) => setLoginEmail(event.target.value)}
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="auth-modal-login-password">密码</label>
                <input
                  id="auth-modal-login-password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="请输入密码"
                  value={loginPassword}
                  onChange={(event) => setLoginPassword(event.target.value)}
                />
              </div>
              {loginError ? <p className="error-text">{loginError}</p> : null}
              {loginMessage ? <p className="success-text">{loginMessage}</p> : null}
              <div className="actions-row auth-modal__actions">
                <InkButton 
                  type="button" 
                  kind="secondary" 
                  className="auth-modal__cancel-btn"
                  onClick={() => onClose()}
                  disabled={loginLoading}
                >
                  取消
                </InkButton>
                <InkButton type="submit" disabled={loginLoading}>
                  {loginLoading ? "登录中..." : "登录"}
                </InkButton>
              </div>
            </form>
          ) : (
            <form className="stack auth-modal__form" onSubmit={handleRegisterSubmit}>
              <div className="field">
                <label className="field__label" htmlFor="auth-modal-register-email">邮箱</label>
                <div className="auth-modal__input-with-action">
                  <input
                    id="auth-modal-register-email"
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    value={registerEmail}
                    onChange={(event) => setRegisterEmail(event.target.value)}
                  />
                  <InkButton
                    type="button"
                    kind="ghost"
                    className="auth-modal__inline-send"
                    onClick={() => void handleSendRegisterCode()}
                    disabled={sendingCode || countdown > 0}
                  >
                    {sendingCode ? "发送中..." : countdown > 0 ? `${countdown}s` : "发送验证码"}
                  </InkButton>
                </div>
              </div>
              <div className="field">
                <label className="field__label" htmlFor="auth-modal-register-code">邮箱验证码</label>
                <input
                  id="auth-modal-register-code"
                  type="text"
                  placeholder="请输入邮箱验证码"
                  value={registerEmailCode}
                  onChange={(event) => setRegisterEmailCode(event.target.value)}
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="auth-modal-register-password">密码</label>
                <input
                  id="auth-modal-register-password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="至少 6 位"
                  value={registerPassword}
                  onChange={(event) => setRegisterPassword(event.target.value)}
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="auth-modal-register-invite">邀请码（可选）</label>
                <input
                  id="auth-modal-register-invite"
                  type="text"
                  placeholder="例如 ORACLE-TRIAL-2026"
                  value={registerInviteCode}
                  onChange={(event) => setRegisterInviteCode(event.target.value)}
                />
              </div>
              {registerError ? <p className="error-text">{registerError}</p> : null}
              {registerMessage ? <p className="success-text">{registerMessage}</p> : null}
              <div className="actions-row auth-modal__actions">
                <InkButton 
                  type="button" 
                  kind="secondary" 
                  className="auth-modal__cancel-btn"
                  onClick={() => onClose()}
                  disabled={registerLoading}
                >
                  取消
                </InkButton>
                <InkButton type="submit" disabled={registerLoading}>
                  {registerLoading ? "提交中..." : "确定"}
                </InkButton>
              </div>
            </form>
          )}
        </section>
      </div>
    </div>
  );
}
