import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import ReactECharts from "echarts-for-react";

import { getAdminDashboard, getAdminLogs, getAdminUsers } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import type { AdminDashboardData, SystemLogItem, UserProfile } from "../types";


interface TrendMetricConfig {
  key: keyof AdminDashboardData["trend"][number];
  label: string;
  color: string;
}

const TREND_METRICS: TrendMetricConfig[] = [
  { key: "analysis_tasks", label: "分析任务", color: "#b75843" },
  { key: "chat_turns", label: "Chat轮次", color: "#cb8b49" },
  { key: "kline_updates", label: "人生K线", color: "#67813f" },
  { key: "calendar_updates", label: "日历更新", color: "#4f8a8c" },
  { key: "ziwei_runs", label: "紫微求签", color: "#8d73b8" },
  { key: "meihua_runs", label: "梅花求签", color: "#b9668f" },
];
const RANGE_OPTIONS: Array<{ id: "24h" | "7d" | "30d"; label: string }> = [
  { id: "24h", label: "24小时" },
  { id: "7d", label: "7天" },
  { id: "30d", label: "30天" },
];

/**
 * 把数值格式化为千分位字符串，提升大屏可读性。
 */
const fmt = (value: number) => value.toLocaleString("zh-CN");

export default function AdminDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<AdminDashboardData | null>(null);
  const [logs, setLogs] = useState<SystemLogItem[]>([]);
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [trendRange, setTrendRange] = useState<"24h" | "7d" | "30d">("24h");

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboardRes, logsRes, usersRes] = await Promise.all([
        getAdminDashboard(trendRange),
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
  }, [trendRange]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void loadAll();
    }, 30_000);
    return () => {
      window.clearInterval(timer);
    };
  }, [trendRange]);

  const trendChartOption = useMemo<EChartsOption | null>(() => {
    if (!dashboard) {
      return null;
    }
    const labels = dashboard.trend.map((point) => point.label);
    const series = TREND_METRICS.map((metric) => ({
      ...(() => {
        const values = dashboard.trend.map((point) => Number(point[metric.key]) || 0);
        const avg = values.reduce((sum, current) => sum + current, 0) / Math.max(values.length, 1);
        const threshold = Math.max(3, Math.ceil(avg * 1.8));
        return {
          markLine: {
            symbol: "none",
            silent: true,
            lineStyle: {
              type: "dashed" as const,
              color: "rgba(157, 43, 29, 0.45)",
              width: 1,
            },
            label: {
              formatter: `${metric.label}阈值`,
              color: "#8b655b",
            },
            data: [{ yAxis: threshold }],
          },
        };
      })(),
      name: metric.label,
      type: "line" as const,
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2, color: metric.color },
      itemStyle: { color: metric.color },
      areaStyle: {
        opacity: 0.12,
        color: metric.color,
      },
      data: dashboard.trend.map((point) => Number(point[metric.key]) || 0),
    }));

    return {
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(37, 29, 26, 0.9)",
        borderColor: "rgba(204, 169, 140, 0.45)",
        textStyle: { color: "#f6e9db" },
      },
      legend: {
        top: 4,
        textStyle: { color: "#6f574d", fontSize: 12 },
      },
      grid: {
        left: 12,
        right: 12,
        bottom: 14,
        top: 34,
        containLabel: true,
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: labels,
        axisLabel: { color: "#8a7268", fontSize: 11 },
        axisLine: { lineStyle: { color: "rgba(157, 43, 29, 0.2)" } },
      },
      yAxis: {
        type: "value",
        minInterval: 1,
        axisLabel: { color: "#8a7268", fontSize: 11 },
        splitLine: { lineStyle: { color: "rgba(157, 43, 29, 0.12)" } },
      },
      series,
    };
  }, [dashboard]);

  const runtimePieOption = useMemo<EChartsOption | null>(() => {
    if (!dashboard) {
      return null;
    }
    const data = [
      { name: "Chat轮次", value: dashboard.runtime_metrics.chat.turns_last_24h, itemStyle: { color: "#cb8b49" } },
      {
        name: "人生K线",
        value: dashboard.runtime_metrics.insight.kline_updates_last_24h,
        itemStyle: { color: "#67813f" },
      },
      {
        name: "日历更新",
        value: dashboard.runtime_metrics.insight.calendar_updates_last_24h,
        itemStyle: { color: "#4f8a8c" },
      },
      {
        name: "紫微求签",
        value: dashboard.runtime_metrics.divination.ziwei_runs_last_24h,
        itemStyle: { color: "#8d73b8" },
      },
      {
        name: "梅花求签",
        value: dashboard.runtime_metrics.divination.meihua_runs_last_24h,
        itemStyle: { color: "#b9668f" },
      },
    ];

    return {
      tooltip: {
        trigger: "item",
        formatter: "{b}<br/>24h: {c} ({d}%)",
        backgroundColor: "rgba(37, 29, 26, 0.9)",
        borderColor: "rgba(204, 169, 140, 0.45)",
        textStyle: { color: "#f6e9db" },
      },
      legend: {
        orient: "vertical",
        right: 8,
        top: "middle",
        textStyle: { color: "#6f574d", fontSize: 12 },
      },
      series: [
        {
          name: "运行占比",
          type: "pie",
          radius: ["44%", "70%"],
          center: ["34%", "50%"],
          label: { color: "#6f574d", formatter: "{b}\n{c}" },
          labelLine: { lineStyle: { color: "rgba(157, 43, 29, 0.25)" } },
          data,
        },
      ],
    };
  }, [dashboard]);

  return (
    <div className="admin-page admin-page--screen fade-in">
      <InkCard title="管理员后台" icon="管">
        {loading ? <p className="loading-state-text">正在加载后台数据...</p> : null}
        {error ? <p className="error-text">{error}</p> : null}

        <div className="actions-row admin-screen__toolbar">
          <span className="admin-screen__realtime">自动刷新：30s</span>
          <div className="insights-segmented" role="tablist" aria-label="趋势范围切换">
            {RANGE_OPTIONS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={trendRange === item.id ? "active" : ""}
                onClick={() => setTrendRange(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <InkButton type="button" kind="ghost" onClick={() => void loadAll()} disabled={loading}>
            刷新面板
          </InkButton>
        </div>
      </InkCard>

      {dashboard ? (
        <>
          <InkCard title="核心指标大屏" icon="览">
            <div className="admin-kpi-grid">
              <div className="admin-kpi-card">
                <p className="admin-kpi-card__label">Token签发(24h)</p>
                <p className="admin-kpi-card__value">{fmt(dashboard.token_metrics.issued_last_24h)}</p>
                <p className="admin-kpi-card__meta">
                  失效401：{fmt(dashboard.token_metrics.invalid_last_24h)} · 登出：{fmt(dashboard.token_metrics.logout_last_24h)}
                </p>
              </div>
              <div className="admin-kpi-card">
                <p className="admin-kpi-card__label">活跃用户(24h)</p>
                <p className="admin-kpi-card__value">{fmt(dashboard.user_metrics.active_users_last_24h)}</p>
                <p className="admin-kpi-card__meta">
                  总用户：{fmt(dashboard.user_metrics.total_users)} · 管理员：{fmt(dashboard.user_metrics.admin_users)}
                </p>
              </div>
              <div className="admin-kpi-card">
                <p className="admin-kpi-card__label">任务运行</p>
                <p className="admin-kpi-card__value">{fmt(dashboard.analysis_metrics.total_tasks)}</p>
                <p className="admin-kpi-card__meta">
                  queued {fmt(dashboard.analysis_metrics.queued_tasks)} · running {fmt(dashboard.analysis_metrics.running_tasks)}
                </p>
              </div>
              <div className="admin-kpi-card">
                <p className="admin-kpi-card__label">模型Token总量</p>
                <p className="admin-kpi-card__value">{fmt(dashboard.analysis_metrics.total_tokens)}</p>
                <p className="admin-kpi-card__meta">24h新增：{fmt(dashboard.analysis_metrics.tokens_last_24h)}</p>
              </div>
              <div className="admin-kpi-card">
                <p className="admin-kpi-card__label">Chat运行</p>
                <p className="admin-kpi-card__value">{fmt(dashboard.runtime_metrics.chat.turns_last_24h)}</p>
                <p className="admin-kpi-card__meta">
                  总轮次：{fmt(dashboard.runtime_metrics.chat.total_turns)} · 会话：{fmt(dashboard.runtime_metrics.chat.total_conversations)}
                </p>
              </div>
              <div className="admin-kpi-card">
                <p className="admin-kpi-card__label">人生K线/日历(24h)</p>
                <p className="admin-kpi-card__value">
                  {fmt(dashboard.runtime_metrics.insight.kline_updates_last_24h + dashboard.runtime_metrics.insight.calendar_updates_last_24h)}
                </p>
                <p className="admin-kpi-card__meta">
                  K线 {fmt(dashboard.runtime_metrics.insight.kline_updates_last_24h)} · 日历 {fmt(dashboard.runtime_metrics.insight.calendar_updates_last_24h)}
                </p>
              </div>
              <div className="admin-kpi-card">
                <p className="admin-kpi-card__label">紫微求签(24h)</p>
                <p className="admin-kpi-card__value">{fmt(dashboard.runtime_metrics.divination.ziwei_runs_last_24h)}</p>
                <p className="admin-kpi-card__meta">总次数：{fmt(dashboard.runtime_metrics.divination.total_ziwei_runs)}</p>
              </div>
              <div className="admin-kpi-card">
                <p className="admin-kpi-card__label">梅花求签(24h)</p>
                <p className="admin-kpi-card__value">{fmt(dashboard.runtime_metrics.divination.meihua_runs_last_24h)}</p>
                <p className="admin-kpi-card__meta">总次数：{fmt(dashboard.runtime_metrics.divination.total_meihua_runs)}</p>
              </div>
            </div>
          </InkCard>

          <InkCard title="24小时运行趋势" icon="势">
            <div className="admin-chart-grid">
              <div className="admin-chart-panel admin-chart-panel--wide">
                {trendChartOption ? (
                  <ReactECharts
                    option={trendChartOption}
                    style={{ height: 320, width: "100%" }}
                    notMerge
                    lazyUpdate
                  />
                ) : null}
              </div>
              <div className="admin-chart-panel">
                {runtimePieOption ? (
                  <ReactECharts
                    option={runtimePieOption}
                    style={{ height: 320, width: "100%" }}
                    notMerge
                    lazyUpdate
                  />
                ) : null}
              </div>
            </div>
            {dashboard ? (
              <div className="admin-alert-row">
                {TREND_METRICS.map((metric) => {
                  const values = dashboard.trend.map((point) => Number(point[metric.key]) || 0);
                  const latest = values[values.length - 1] || 0;
                  const avg = values.reduce((sum, current) => sum + current, 0) / Math.max(values.length, 1);
                  const threshold = Math.max(3, Math.ceil(avg * 1.8));
                  const isAlert = latest >= threshold;
                  return (
                    <span key={`alert-${metric.key}`} className={`admin-alert-chip ${isAlert ? "admin-alert-chip--hot" : ""}`}>
                      {metric.label}：当前 {latest} / 阈值 {threshold}
                    </span>
                  );
                })}
              </div>
            ) : null}
          </InkCard>
        </>
      ) : null}

      {dashboard ? (
        <InkCard title="系统概览细节" icon="表">
          <div className="meta-grid">
            <div className="meta-item">
              <p className="meta-item__label">任务成功率</p>
              <p className="meta-item__value">
                {dashboard.analysis_metrics.total_tasks > 0
                  ? `${Math.round((dashboard.analysis_metrics.succeeded_tasks / dashboard.analysis_metrics.total_tasks) * 100)}%`
                  : "0%"}
              </p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">失败任务数</p>
              <p className="meta-item__value">{fmt(dashboard.analysis_metrics.failed_tasks)}</p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">24h 分析结果</p>
              <p className="meta-item__value">{fmt(dashboard.analysis_metrics.results_last_24h)}</p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">日志总量</p>
              <p className="meta-item__value">{fmt(dashboard.log_metrics.total_logs)}</p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">24h 错误日志</p>
              <p className="meta-item__value">{fmt(dashboard.log_metrics.error_logs)}</p>
            </div>
            <div className="meta-item">
              <p className="meta-item__label">24h 日志量</p>
              <p className="meta-item__value">{fmt(dashboard.log_metrics.logs_last_24h)}</p>
            </div>
          </div>
          <div className="admin-top-paths">
            <p className="admin-top-paths__title">高频接口 Top</p>
            <div className="admin-top-paths__list">
              {(dashboard.log_metrics.top_paths || []).slice(0, 6).map((item) => (
                <div key={`${item.path}-${item.total}`} className="admin-top-paths__item">
                  <span>{item.path || "-"}</span>
                  <strong>{fmt(item.total)}</strong>
                </div>
              ))}
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
