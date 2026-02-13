import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { registerByEmail, sendRegisterCode } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import type { UserProfile } from "../types";
import { setAuthData } from "../utils/auth";

interface RegisterPageProps {
  onAuthSuccess?: (user: UserProfile) => void;
}

export default function RegisterPage({ onAuthSuccess }: RegisterPageProps) {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailCode, setEmailCode] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (countdown <= 0) {
      return;
    }
    const timer = window.setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [countdown]);

  const handleSendCode = async () => {
    setError(null);
    setMessage(null);
    const normalizedEmail = email.trim();
    if (!normalizedEmail) {
      setError("请先输入邮箱。");
      return;
    }

    setSendingCode(true);
    try {
      const res = await sendRegisterCode({ email: normalizedEmail });
      const expireMinutes = res.data?.expire_minutes || 10;
      setMessage(`验证码已发送，请在 ${expireMinutes} 分钟内完成注册。`);
      setCountdown(60);
    } catch (err) {
      const apiMessage = (err as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setError(apiMessage || (err instanceof Error ? err.message : "发送验证码失败，请稍后重试。"));
    } finally {
      setSendingCode(false);
    }
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (!email.trim() || !password.trim() || !emailCode.trim()) {
      setError("请输入邮箱、验证码和密码。");
      return;
    }

    setLoading(true);
    try {
      const res = await registerByEmail({
        email: email.trim(),
        password: password.trim(),
        email_code: emailCode.trim(),
        invite_code: inviteCode.trim() || undefined,
      });
      if (!res.data) {
        throw new Error("注册失败");
      }
      setAuthData(res.data.token, res.data.user);
      onAuthSuccess?.(res.data.user);
      navigate(res.data.user.role === "admin" ? "/admin/dashboard" : "/start-analysis", { replace: true });
    } catch (err) {
      const apiMessage = (err as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setError(apiMessage || (err instanceof Error ? err.message : "注册失败，请稍后重试。"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page fade-in">
      <InkCard title="邮箱注册" icon="注">
        <form className="stack" onSubmit={onSubmit}>
          <div className="field">
            <label className="field__label" htmlFor="register-email">邮箱</label>
            <input
              id="register-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="register-code">邮箱验证码</label>
            <input
              id="register-code"
              type="text"
              value={emailCode}
              onChange={(event) => setEmailCode(event.target.value)}
              placeholder="请输入邮箱验证码"
            />
            <div className="actions-row">
              <InkButton
                type="button"
                kind="ghost"
                onClick={() => void handleSendCode()}
                disabled={sendingCode || countdown > 0}
              >
                {sendingCode ? "发送中..." : countdown > 0 ? `${countdown}s 后重发` : "发送验证码"}
              </InkButton>
            </div>
          </div>
          <div className="field">
            <label className="field__label" htmlFor="register-password">密码</label>
            <input
              id="register-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="至少 6 位"
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="register-invite">邀请码（按配置可选）</label>
            <input
              id="register-invite"
              type="text"
              value={inviteCode}
              onChange={(event) => setInviteCode(event.target.value)}
              placeholder="例如 ORACLE-TRIAL-2026"
            />
          </div>

          {error ? <p className="error-text">{error}</p> : null}
          {message ? <p className="success-text">{message}</p> : null}

          <div className="actions-row">
            <InkButton type="submit" disabled={loading}>{loading ? "注册中..." : "注册并登录"}</InkButton>
            <Link to="/login">
              <InkButton type="button" kind="ghost">去登录</InkButton>
            </Link>
          </div>
        </form>
      </InkCard>
    </div>
  );
}
