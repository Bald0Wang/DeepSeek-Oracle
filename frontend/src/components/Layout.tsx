import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { CONSTELLATION_INFOS, CONSTELLATION_SWITCH_INTERVAL_MS } from "../constants/constellations";
import { ConstellationInfoBar } from "./ConstellationInfoBar";
import { ZiweiBackground } from "./ZiweiBackground";


export function Layout() {
  const location = useLocation();
  const isHome = location.pathname === "/";

  const [activeConstellationIndex, setActiveConstellationIndex] = useState(0);

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
          <NavLink to="/" end className={({ isActive }) => isActive ? "active" : ""}>
            开始分析
          </NavLink>
          <NavLink to="/oracle" className={({ isActive }) => isActive ? "active" : ""}>
            咨询对话
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => isActive ? "active" : ""}>
            历史记录
          </NavLink>
        </nav>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      {isHome ? <ConstellationInfoBar activeIndex={activeConstellationIndex} /> : null}

      <footer className="app-footer">
        天衍 Oracle · 东方命理咨询与行动建议
      </footer>
    </div>
  );
}
