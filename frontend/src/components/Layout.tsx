import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { CONSTELLATION_INFOS, CONSTELLATION_SWITCH_INTERVAL_MS } from "../constants/constellations";
import type { UserProfile } from "../types";
import { InkButton } from "./InkButton";
import { ConstellationInfoBar } from "./ConstellationInfoBar";
import { ZiweiBackground } from "./ZiweiBackground";

interface LayoutProps {
  user: UserProfile | null;
  authReady: boolean;
  onLogout: () => Promise<void> | void;
}

export function Layout({ user, authReady, onLogout }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isHome = location.pathname === "/";
  const isPublicRoute = location.pathname === "/login"
    || location.pathname === "/register"
    || location.pathname === "/forgot-password";

  const [activeConstellationIndex, setActiveConstellationIndex] = useState(0);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    if (!isHome) {
      setActiveConstellationIndex(0);
      return;
    }

    const timer = window.setInterval(() => {
      setActiveConstellationIndex((prev) => (prev + 1) % CONSTELLATION_INFOS.length);
    }, CONSTELLATION_SWITCH_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [isHome]);

  const handleLogoutClick = async () => {
    if (isLoggingOut) {
      return;
    }
    setIsLoggingOut(true);
    try {
      await onLogout();
      navigate("/login", { replace: true });
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
        <Link to="/" className="top-nav__brand">
          <span className="top-nav__brand-icon" aria-hidden="true" />
          天衍 Oracle
        </Link>
        <nav className="top-nav__links">
          {user ? (
            <>
              <NavLink to="/" end className={({ isActive }) => isActive ? "active" : ""}>
                开始分析
              </NavLink>
              <NavLink to="/oracle" className={({ isActive }) => isActive ? "active" : ""}>
                咨询对话
              </NavLink>
              <NavLink to="/history" className={({ isActive }) => isActive ? "active" : ""}>
                历史记录
              </NavLink>
              {user.role === "admin" ? (
                <NavLink to="/admin" className={({ isActive }) => isActive ? "active" : ""}>
                  管理后台
                </NavLink>
              ) : null}
            </>
          ) : (
            <NavLink to="/login" className={({ isActive }) => isActive ? "active" : ""}>
              后台登录
            </NavLink>
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

      <main className="app-main">
        <Outlet />
      </main>

      {isHome && !isPublicRoute ? <ConstellationInfoBar activeIndex={activeConstellationIndex} /> : null}

      <footer className="app-footer">
        天衍 Oracle · 东方命理咨询与行动建议
      </footer>
    </div>
  );
}
