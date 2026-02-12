import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { loginByEmail } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import type { UserProfile } from "../types";
import { setAuthData } from "../utils/auth";

interface LoginPageProps {
  onAuthSuccess?: (user: UserProfile) => void;
}

export default function LoginPage({ onAuthSuccess }: LoginPageProps) {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (!email.trim() || !password.trim()) {
      setError("请输入邮箱和密码。");
      return;
    }

    setLoading(true);
    try {
      const res = await loginByEmail({
        email: email.trim(),
        password: password.trim(),
      });
      if (!res.data) {
        throw new Error("登录失败");
      }
      setAuthData(res.data.token, res.data.user);
      onAuthSuccess?.(res.data.user);
      navigate(res.data.user.role === "admin" ? "/admin/dashboard" : "/oracle", { replace: true });
    } catch (err) {
      const apiMessage = (err as { response?: { data?: { message?: string } } })?.response?.data?.message;
      setError(apiMessage || (err instanceof Error ? err.message : "登录失败，请稍后重试。"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page fade-in">
      <InkCard title="用户登录" icon="登">
        <form className="stack" onSubmit={onSubmit}>
          <div className="field">
            <label className="field__label" htmlFor="login-email">邮箱</label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </div>

          <div className="field">
            <label className="field__label" htmlFor="login-password">密码</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="请输入密码"
            />
          </div>

          {error ? <p className="error-text">{error}</p> : null}

          <div className="actions-row">
            <InkButton type="submit" disabled={loading}>{loading ? "登录中..." : "登录"}</InkButton>
            <Link to="/register">
              <InkButton type="button" kind="ghost">去注册</InkButton>
            </Link>
            <Link to="/forgot-password">
              <InkButton type="button" kind="ghost">忘记密码</InkButton>
            </Link>
          </div>
        </form>
      </InkCard>
    </div>
  );
}
