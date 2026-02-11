import { useEffect, useState } from "react";

import { getAdminDashboard, getAdminLogs, getAdminUsers } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import type { AdminDashboardData, SystemLogItem, UserProfile } from "../types";


export default function AdminDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<AdminDashboardData | null>(null);
  const [logs, setLogs] = useState<SystemLogItem[]>([]);
  const [users, setUsers] = useState<UserProfile[]>([]);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboardRes, logsRes, usersRes] = await Promise.all([
        getAdminDashboard(),
        getAdminLogs(1, 20),
        getAdminUsers(1, 20),
      ]);

      setDashboard(dashboardRes.data || null);
      setLogs(logsRes.data?.items || []);
      setUsers(usersRes.data?.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载后台数据失败。");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
  }, []);

  return (
    <div className="admin-page fade-in">
      <InkCard title="管理员后台" icon="管">
        {loading ? <p className="loading-state-text">正在加载后台数据...</p> : null}
        {error ? <p className="error-text">{error}</p> : null}

        <div className="actions-row">
          <InkButton type="button" kind="ghost" onClick={() => void loadAll()} disabled={loading}>
            刷新面板
          </InkButton>
        </div>
      </InkCard>

      {dashboard ? (
        <InkCard title="系统概览" icon="览">
          <div className="meta-grid">
            <div className="meta-item">
              <p className="meta-item__label">用户总数</p>
              <p className="meta-item__value">{dashboard.user_metrics.total_users}</p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">管理员数量</p>
              <p className="meta-item__value">{dashboard.user_metrics.admin_users}</p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">任务总数</p>
              <p className="meta-item__value">{dashboard.analysis_metrics.total_tasks}</p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">成功任务</p>
              <p className="meta-item__value">{dashboard.analysis_metrics.succeeded_tasks}</p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">失败任务</p>
              <p className="meta-item__value">{dashboard.analysis_metrics.failed_tasks}</p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">24h 日志量</p>
              <p className="meta-item__value">{dashboard.log_metrics.logs_last_24h}</p>
            </div>
          </div>
        </InkCard>
      ) : null}

      <InkCard title="最近系统日志" icon="志">
        <div className="admin-log-list">
          {logs.length === 0 ? <p className="loading-state-text">暂无日志数据。</p> : null}
          {logs.map((log) => (
            <div key={log.id} className="admin-log-item">
              <p className="admin-log-item__title">
                [{log.level}] {log.method || "-"} {log.path || "-"} · {log.status_code ?? "-"}
              </p>
              <p className="admin-log-item__meta">
                {log.created_at} · {log.duration_ms ?? "-"}ms · {log.user_email || "anonymous"} · {log.ip || "-"}
              </p>
              <p className="admin-log-item__meta">{log.message || "-"}</p>
            </div>
          ))}
        </div>
      </InkCard>

      <InkCard title="最近注册/登录用户" icon="户">
        <div className="admin-user-list">
          {users.length === 0 ? <p className="loading-state-text">暂无用户数据。</p> : null}
          {users.map((user) => (
            <div key={user.id} className="admin-user-item">
              <p className="admin-user-item__title">{user.email}</p>
              <p className="admin-user-item__meta">
                role={user.role} · active={String(user.is_active)} · created={user.created_at}
              </p>
              <p className="admin-user-item__meta">last_login={user.last_login_at || "-"}</p>
            </div>
          ))}
        </div>
      </InkCard>
    </div>
  );
}
