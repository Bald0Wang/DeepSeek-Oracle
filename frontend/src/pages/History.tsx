import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getDivinationHistory, getHistory, getOracleConversations } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LoadingAnimation } from "../components/LoadingAnimation";
import type { DivinationHistoryData, HistoryResponseData, OracleConversationSummary } from "../types";


const CALENDAR_LABEL: Record<string, string> = {
  solar: "阳历",
  lunar: "阴历",
};


export default function HistoryPage() {
  const [bucket, setBucket] = useState<"analysis" | "divination">("analysis");
  const [page, setPage] = useState(1);
  const [analysisData, setAnalysisData] = useState<HistoryResponseData | null>(null);
  const [conversationData, setConversationData] = useState<OracleConversationSummary[] | null>(null);
  const [divinationData, setDivinationData] = useState<DivinationHistoryData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        if (bucket === "analysis") {
          const [historyResponse, conversationResponse] = await Promise.all([
            getHistory(page, 20),
            getOracleConversations(60),
          ]);
          if (!historyResponse.data) {
            throw new Error("history is empty");
          }
          setAnalysisData(historyResponse.data);
          setConversationData(conversationResponse.data?.items || []);
          return;
        }
        const response = await getDivinationHistory(page, 20, "all");
        if (!response.data) {
          throw new Error("divination history is empty");
        }
        setDivinationData(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "获取历史记录失败");
      }
    })();
  }, [bucket, page]);

  useEffect(() => {
    setPage(1);
    setError(null);
  }, [bucket]);

  if (error) {
    return (
      <InkCard title="历史记录">
        <p className="error-text">{error}</p>
      </InkCard>
    );
  }

  return (
    <div className="history-page fade-in">
      <InkCard title="历史记录">
        <div className="insights-segmented" role="tablist" aria-label="历史桶切换">
          <button
            type="button"
            className={bucket === "analysis" ? "active" : ""}
            onClick={() => setBucket("analysis")}
          >
            分析记录
          </button>
          <button
            type="button"
            className={bucket === "divination" ? "active" : ""}
            onClick={() => setBucket("divination")}
          >
            占卜存储桶
          </button>
        </div>

        {(bucket === "analysis" && (!analysisData || !conversationData)) || (bucket === "divination" && !divinationData) ? (
          <div className="loading-container">
            <LoadingAnimation size="large" />
            <p className="loading-state-text">加载中...</p>
          </div>
        ) : bucket === "analysis" && analysisData && conversationData && analysisData.items.length === 0 && conversationData.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state__title">暂无历史记录</p>
            <p className="empty-state__text">完成一次分析或咨询后，你的历史记录会出现在这里。</p>
            <Link to="/" className="empty-state__action">
              <InkButton type="button">开始第一次分析</InkButton>
            </Link>
          </div>
        ) : bucket === "divination" && divinationData && divinationData.items.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state__title">暂无占卜记录</p>
            <p className="empty-state__text">完成一次梅花或紫微求签后，会自动存入这里，方便持续回看。</p>
            <div className="actions-row">
              <Link to="/ziwei" className="empty-state__action">
                <InkButton type="button">去紫微求签</InkButton>
              </Link>
              <Link to="/meihua" className="empty-state__action">
                <InkButton type="button" kind="ghost">去梅花求签</InkButton>
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="history-list">
              {bucket === "analysis" && analysisData
                ? analysisData.items.map((item) => (
                    <article key={`analysis-${item.id}`} className="history-item">
                      <div className="history-item__info">
                        <div className="history-item__date">{item.date}</div>
                        <div className="history-item__tags">
                          <span className="tag tag--primary">{item.gender}</span>
                          <span className="tag">{CALENDAR_LABEL[item.calendar] || item.calendar}</span>
                        </div>
                        <div className="history-item__meta">
                          时辰 {item.timezone} · {item.provider} / {item.model} · {item.created_at}
                        </div>
                      </div>
                      <div className="history-item__action">
                        <Link to={`/result/${item.id}`}>
                          <InkButton type="button" kind="ghost">
                            查看结果
                          </InkButton>
                        </Link>
                      </div>
                    </article>
                  ))
                : null}
              {bucket === "analysis" && conversationData
                ? conversationData.map((conversation) => (
                    <article key={`conversation-${conversation.id}`} className="history-item">
                      <div className="history-item__info">
                        <div className="history-item__date">{conversation.title || "咨询对话"}</div>
                        <div className="history-item__tags">
                          <span className="tag tag--primary">咨询对话</span>
                          <span className="tag">{conversation.turn_count || 0} 轮</span>
                        </div>
                        <div className="history-item__meta">
                          最新更新 {conversation.updated_at} · 最近问题 {conversation.last_query || "暂无"}
                        </div>
                      </div>
                      <div className="history-item__action">
                        <Link to={`/oracle-chat?conversation_id=${conversation.id}`}>
                          <InkButton type="button" kind="ghost">
                            继续咨询
                          </InkButton>
                        </Link>
                      </div>
                    </article>
                  ))
                : null}

              {bucket === "divination" && divinationData
                ? divinationData.items.map((item) => (
                    <article key={`divination-${item.id}`} className="history-item">
                      <div className="history-item__info">
                        <div className="history-item__date">{item.title}</div>
                        <div className="history-item__tags">
                          <span className="tag tag--primary">{item.type === "ziwei" ? "紫微斗数" : "梅花易数"}</span>
                          {item.occurred_at ? <span className="tag">{item.occurred_at}</span> : null}
                        </div>
                        <div className="history-item__meta">
                          {item.provider} / {item.model} · {item.created_at}
                        </div>
                      </div>
                      <div className="history-item__action">
                        <Link to={`/history/divination/${item.id}`}>
                          <InkButton type="button" kind="ghost">
                            查看解读
                          </InkButton>
                        </Link>
                      </div>
                    </article>
                  ))
                : null}
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
                {bucket === "analysis" && analysisData
                  ? `第 ${analysisData.pagination.page} 页 · 分析 ${analysisData.pagination.total} 条`
                  : null}
                {bucket === "analysis" && conversationData
                  ? ` · 咨询 ${conversationData.length} 条`
                  : null}
                {bucket === "divination" && divinationData
                  ? `第 ${divinationData.pagination.page} 页 · 共 ${divinationData.pagination.total} 条`
                  : null}
              </span>
              <InkButton
                type="button"
                kind="secondary"
                disabled={
                  bucket === "analysis"
                    ? !(analysisData?.pagination.has_next)
                    : !(divinationData?.pagination.has_next)
                }
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
