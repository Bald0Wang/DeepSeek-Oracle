import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getHistory } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LoadingAnimation } from "../components/LoadingAnimation";
import type { HistoryResponseData } from "../types";


const CALENDAR_LABEL: Record<string, string> = {
  solar: "阳历",
  lunar: "阴历",
};


export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<HistoryResponseData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const response = await getHistory(page, 20);
        if (!response.data) throw new Error("history is empty");
        setData(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "获取历史记录失败");
      }
    })();
  }, [page]);

  if (error) {
    return (
      <InkCard title="历史卷宗" icon="📚">
        <p className="error-text">{error}</p>
      </InkCard>
    );
  }

  return (
    <div className="fade-in">
      <InkCard title="历史卷宗" icon="📚">
        {!data ? (
          <div className="loading-container">
            <LoadingAnimation size="large" />
            <p style={{ color: "var(--text-muted)", marginTop: 12 }}>加载中…</p>
          </div>
        ) : data.items.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon">📭</div>
            <p className="empty-state__text">尚无历史推演记录</p>
            <Link to="/" style={{ marginTop: 16, display: "inline-block" }}>
              <InkButton type="button">开始第一次推演</InkButton>
            </Link>
          </div>
        ) : (
          <>
            <div className="history-list">
              {data.items.map((item) => (
                <article key={item.id} className="history-item">
                  <div className="history-item__info">
                    <div className="history-item__date">
                      {item.date}
                      <span className="tag tag--primary" style={{ marginLeft: 8 }}>
                        {item.gender}
                      </span>
                      <span className="tag tag--gold" style={{ marginLeft: 6 }}>
                        {CALENDAR_LABEL[item.calendar] || item.calendar}
                      </span>
                    </div>
                    <div className="history-item__meta">
                      时辰 {item.timezone} · {item.provider} / {item.model} · {item.created_at}
                    </div>
                  </div>
                  <div className="history-item__action">
                    <Link to={`/result/${item.id}`}>
                      <InkButton type="button" kind="ghost">
                        查看结果 →
                      </InkButton>
                    </Link>
                  </div>
                </article>
              ))}
            </div>

            <div className="pagination">
              <InkButton
                type="button"
                kind="secondary"
                disabled={page <= 1}
                onClick={() => setPage((prev) => prev - 1)}
              >
                上一页
              </InkButton>
              <span className="pagination__info">
                第 {data.pagination.page} 页 · 共 {data.pagination.total} 条
              </span>
              <InkButton
                type="button"
                kind="secondary"
                disabled={!data.pagination.has_next}
                onClick={() => setPage((prev) => prev + 1)}
              >
                下一页
              </InkButton>
            </div>
          </>
        )}
      </InkCard>
    </div>
  );
}
