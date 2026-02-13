import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { getMe, logout } from "./api";
import { Layout } from "./components/Layout";
import type { UserProfile } from "./types";
import { clearAuthData, getAccessToken, getStoredUser, setAuthData } from "./utils/auth";
import AdminDashboardPage from "./pages/AdminDashboard";
import AdminLoginPage from "./pages/AdminLogin";
import DetailPage from "./pages/Detail";
import ForgotPasswordPage from "./pages/ForgotPassword";
import HistoryPage from "./pages/History";
import HomePage from "./pages/Home";
import InsightsPage from "./pages/Insights";
import LoginPage from "./pages/Login";
import LoadingPage from "./pages/Loading";
import MeihuaFortunePage from "./pages/MeihuaFortune";
import OracleChatPage from "./pages/OracleChat";
import RegisterPage from "./pages/Register";
import ResultPage from "./pages/Result";
import ZiweiFortunePage from "./pages/ZiweiFortune";

interface GuardProps {
  authReady: boolean;
  user: UserProfile | null;
}

const hasSession = (user: UserProfile | null) => Boolean(getAccessToken()) && Boolean(user);

function LoadingGate() {
  return (
    <div className="auth-page fade-in">
      <p className="loading-state-text">正在校验登录状态...</p>
    </div>
  );
}

function RequireAuth({ authReady, user }: GuardProps) {
  if (!authReady) {
    return <LoadingGate />;
  }
  if (!hasSession(user)) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

function RequireAdmin({ authReady, user }: GuardProps) {
  const currentUser = hasSession(user) ? user : null;
  if (!authReady) {
    return <LoadingGate />;
  }
  if (!currentUser) {
    return <Navigate to="/admin" replace />;
  }
  if (currentUser.role !== "admin") {
    return <Navigate to="/oracle" replace />;
  }
  return <Outlet />;
}

function PublicOnly({ authReady, user }: GuardProps) {
  const currentUser = hasSession(user) ? user : null;
  if (!authReady) {
    return <LoadingGate />;
  }
  if (currentUser) {
    return <Navigate to={currentUser.role === "admin" ? "/admin/dashboard" : "/oracle"} replace />;
  }
  return <Outlet />;
}


export default function App() {
  const [user, setUser] = useState<UserProfile | null>(getStoredUser());
  const [authReady, setAuthReady] = useState(false);
  const activeUser = hasSession(user) ? user : null;

  useEffect(() => {
    let cancelled = false;

    const syncAuth = async () => {
      const token = getAccessToken();
      if (!token) {
        clearAuthData();
        if (!cancelled) {
          setUser(null);
          setAuthReady(true);
        }
        return;
      }

      try {
        const res = await getMe();
        const me = res.data?.user || null;
        if (!me) {
          clearAuthData();
          if (!cancelled) {
            setUser(null);
          }
          return;
        }
        setAuthData(token, me);
        if (!cancelled) {
          setUser(me);
        }
      } catch {
        clearAuthData();
        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setAuthReady(true);
        }
      }
    };

    void syncAuth();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleAuthSuccess = (nextUser: UserProfile) => {
    setUser(nextUser);
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // Ignore remote logout failures and clear local auth state anyway.
    }
    clearAuthData();
    setUser(null);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout user={activeUser} authReady={authReady} onLogout={handleLogout} />}>
          <Route element={<PublicOnly authReady={authReady} user={activeUser} />}>
            <Route path="/admin" element={<AdminLoginPage onAuthSuccess={handleAuthSuccess} />} />
            <Route path="/login" element={<LoginPage onAuthSuccess={handleAuthSuccess} />} />
            <Route path="/register" element={<RegisterPage onAuthSuccess={handleAuthSuccess} />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          </Route>

          <Route element={<RequireAuth authReady={authReady} user={activeUser} />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/oracle" element={<OracleChatPage />} />
            <Route path="/ziwei" element={<ZiweiFortunePage />} />
            <Route path="/meihua" element={<MeihuaFortunePage />} />
            <Route path="/loading/:taskId" element={<LoadingPage />} />
            <Route path="/result/:id" element={<ResultPage />} />
            <Route path="/result/:id/:type" element={<DetailPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/insights" element={<InsightsPage />} />
          </Route>

          <Route element={<RequireAdmin authReady={authReady} user={activeUser} />}>
            <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
          </Route>

          <Route
            path="*"
            element={
              <Navigate
                to={activeUser ? (activeUser.role === "admin" ? "/admin/dashboard" : "/") : "/login"}
                replace
              />
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
