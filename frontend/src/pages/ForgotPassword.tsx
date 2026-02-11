import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { resetPasswordByEmail, sendForgotPasswordCode } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";


export default function ForgotPasswordPage() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
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
      const res = await sendForgotPasswordCode({ email: normalizedEmail });
      const expireMinutes = res.data?.expire_minutes || 10;
      setMessage(`验证码已发送，请在 ${expireMinutes} 分钟内完成重置。`);
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

    if (!email.trim() || !resetCode.trim() || !newPassword.trim()) {
      setError("请输入邮箱、验证码和新密码。");
      return;
    }

    setLoading(true);
    try {
      await resetPasswordByEmail({
        email: email.trim(),
        reset_code: resetCode.trim(),
        new_password: newPassword.trim(),
      });
      setMessage("密码重置成功，请使用新密码登录。");
      window.setTimeout(() => {
        navigate("/login", { replace: true });
      }, 800);
    } catch (err) {
      const apiMessage = (err as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setError(apiMessage || (err instanceof Error ? err.message : "重置密码失败，请稍后重试。"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page fade-in">
      <InkCard title="找回密码" icon="密">
        <form className="stack" onSubmit={onSubmit}>
          <div className="field">
            <label className="field__label" htmlFor="forgot-email">邮箱</label>
            <input
              id="forgot-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <div className="field">
            <label className="field__label" htmlFor="forgot-code">验证码</label>
            <input
              id="forgot-code"
              type="text"
              value={resetCode}
              onChange={(event) => setResetCode(event.target.value)}
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
            <label className="field__label" htmlFor="forgot-new-password">新密码</label>
            <input
              id="forgot-new-password"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="至少 6 位"
            />
          </div>

          {error ? <p className="error-text">{error}</p> : null}
          {message ? <p className="success-text">{message}</p> : null}

          <div className="actions-row">
            <InkButton type="submit" disabled={loading}>{loading ? "提交中..." : "重置密码"}</InkButton>
            <Link to="/login">
              <InkButton type="button" kind="ghost">返回登录</InkButton>
            </Link>
          </div>
        </form>
      </InkCard>
    </div>
  );
}
