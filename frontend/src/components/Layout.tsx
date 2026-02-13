import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import type { UserProfile } from "../types";
import { InkButton } from "./InkButton";
import { ZiweiBackground } from "./ZiweiBackground";

interface LayoutProps {
  user: UserProfile | null;
  authReady: boolean;
  onLogout: () => Promise<void> | void;
}

export function Layout({ user, authReady, onLogout }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isHome = location.pathname === "/oracle";

  const [activeConstellationIndex, setActiveConstellationIndex] = useState(0);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    if (!isHome) {
      setActiveConstellationIndex(0);
      return;
    }
    // Keep background static in chat page to reduce visual fatigue.
    setActiveConstellationIndex(0);
  }, [isHome]);

  const handleLogoutClick = async () => {
    if (isLoggingOut) {
      return;
    }
    setIsLoggingOut(true);
    try {
      await onLogout();
      navigate(user?.role === "admin" ? "/admin" : "/login", { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="app-shell">
      <ZiweiBackground activeIndex={activeConstellationIndex} />
      <div className="app-chroma-line" aria-hidden="true">
        <span />
      </div>
      <div className="app-observation-label" aria-hidden="true">
        天衍星历观测
      </div>

      <header className="top-nav">
        <Link to="/oracle" className="top-nav__brand">
          <span className="top-nav__brand-icon" aria-hidden="true" />
          天衍 Oracle
        </Link>
        <nav className="top-nav__links">
          {user ? (
            <>
              <NavLink to="/oracle" className={({ isActive }) => isActive ? "active" : ""}>
                咨询对话
              </NavLink>
              <NavLink to="/history" className={({ isActive }) => isActive ? "active" : ""}>
                历史记录
              </NavLink>
              <NavLink to="/insights" className={({ isActive }) => isActive ? "active" : ""}>
                人生线/日历
              </NavLink>
              <NavLink to="/ziwei" className={({ isActive }) => isActive ? "active" : ""}>
                紫微求签
              </NavLink>
              <NavLink to="/meihua" className={({ isActive }) => isActive ? "active" : ""}>
                梅花求签
              </NavLink>
              {user.role === "admin" ? (
                <NavLink to="/admin/dashboard" className={({ isActive }) => isActive ? "active" : ""}>
                  管理后台
                </NavLink>
              ) : null}
            </>
          ) : (
            <>
              <NavLink to="/login" className={({ isActive }) => isActive ? "active" : ""}>
                用户登录
              </NavLink>
              <NavLink to="/register" className={({ isActive }) => isActive ? "active" : ""}>
                邮箱注册
              </NavLink>
            </>
          )}
        </nav>
        <div className="top-nav__auth">
          {!authReady ? <span className="top-nav__hint">校验中</span> : null}
          {user ? (
            <>
              <span className="top-nav__user">{user.email}</span>
              <InkButton type="button" kind="ghost" onClick={() => void handleLogoutClick()} disabled={isLoggingOut}>
                {isLoggingOut ? "退出中..." : "退出"}
              </InkButton>
            </>
          ) : null}
        </div>
      </header>

      <main className={`app-main ${location.pathname === "/oracle" ? "app-main--oracle" : ""}`}>
        <Outlet />
      </main>

      <footer className="app-footer">
        天衍 Oracle · 东方命理咨询与行动建议
      </footer>
    </div>
  );
}
