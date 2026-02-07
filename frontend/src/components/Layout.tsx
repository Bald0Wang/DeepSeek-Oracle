import { Link, NavLink, Outlet } from "react-router-dom";


export function Layout() {
  return (
    <div className="app-shell">
      <header className="top-nav">
        <Link to="/" className="top-nav__brand">
          <span className="top-nav__brand-icon">紫</span>
          紫微神算
        </Link>
        <nav className="top-nav__links">
          <NavLink to="/" end className={({ isActive }) => isActive ? "active" : ""}>
            命盘推演
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => isActive ? "active" : ""}>
            历史卷宗
          </NavLink>
        </nav>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        紫微神算 · DeepSeek Oracle &nbsp;—&nbsp; 以紫微斗数为骨，大语言模型为魂
      </footer>
    </div>
  );
}
