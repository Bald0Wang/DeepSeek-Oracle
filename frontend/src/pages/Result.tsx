import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { exportReport, getResult } from "../api";
import { ExecutionTimeChart } from "../components/ExecutionTimeChart";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LoadingAnimation } from "../components/LoadingAnimation";
import type { AnalysisResult } from "../types";


const ANALYSIS_CONFIG: Record<string, { label: string; icon: string; desc: string }> = {
  marriage_path: {
    label: "婚姻道路",
    icon: "💍",
    desc: "解读夫妻宫星曜，分析感情走向与婚姻运势",
  },
  challenges: {
    label: "困难挑战",
    icon: "⚡",
    desc: "洞察人生波折，提供紫微斗数视角的应对之策",
  },
  partner_character: {
    label: "伴侣性格",
    icon: "🤝",
    desc: "推演另一半的性格特质与相处模式",
  },
};


export default function ResultPage() {
  const { id = "" } = useParams();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const response = await getResult(Number(id));
        if (!response.data) throw new Error("result not found");
        setResult(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "获取结果失败");
      }
    })();
  }, [id]);

  const download = async (scope: string) => {
    if (!id) return;
    const response = await exportReport(Number(id), scope);
    const blob = new Blob([response.data], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `analysis_${id}_${scope}.md`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <InkCard title="结果读取失败" icon="⚠">
        <p className="error-text">{error}</p>
      </InkCard>
    );
  }

  if (!result) {
    return (
      <div className="loading-container" style={{ paddingTop: 80 }}>
        <LoadingAnimation size="large" />
        <p style={{ color: "var(--text-muted)", marginTop: 16 }}>正在加载命盘结果…</p>
      </div>
    );
  }

  const calendarLabel = result.birth_info.calendar === "solar" ? "阳历" : "阴历";

  return (
    <div className="fade-in">
      {/* Overview Card */}
      <InkCard title="命盘结果总览" icon="📜">
        <div className="meta-grid">
          <div className="meta-item">
            <div className="meta-item__label">出生日期</div>
            <div className="meta-item__value">{result.birth_info.date}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">时辰</div>
            <div className="meta-item__value">第 {result.birth_info.timezone} 时</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">性别</div>
            <div className="meta-item__value">{result.birth_info.gender}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">历法</div>
            <div className="meta-item__value">{calendarLabel}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">AI 模型</div>
            <div className="meta-item__value">{result.model}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">总耗时</div>
            <div className="meta-item__value">{result.total_execution_time.toFixed(1)}s</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">总 Token</div>
            <div className="meta-item__value">{result.total_token_count.toLocaleString()}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">供应商</div>
            <div className="meta-item__value">{result.provider}</div>
          </div>
        </div>

        {/* Star Chart Description */}
        {result.text_description && (
          <>
            <hr className="ink-divider" />
            <details>
              <summary
                style={{
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: 14,
                  color: "var(--text-soft)",
                  marginBottom: 8,
                }}
              >
                展开命盘描述
              </summary>
              <div className="pre-wrap">{result.text_description}</div>
            </details>
          </>
        )}

        <div className="actions-row" style={{ marginTop: 16 }}>
          <InkButton type="button" onClick={() => download("full")}>
            下载完整报告
          </InkButton>
          <Link to="/history">
            <InkButton type="button" kind="ghost">
              查看历史
            </InkButton>
          </Link>
        </div>
      </InkCard>

      <InkCard title="推理耗时分析" icon="⏱">
        <ExecutionTimeChart
          rows={Object.entries(result.analysis).map(([analysisType, item]) => ({
            key: analysisType,
            label: ANALYSIS_CONFIG[analysisType]?.label || analysisType,
            seconds: Number(item.execution_time || 0),
          }))}
        />
      </InkCard>

      {/* Analysis Cards */}
      {Object.entries(result.analysis).map(([analysisType, item], idx) => {
        const config = ANALYSIS_CONFIG[analysisType] || {
          label: analysisType,
          icon: "📋",
          desc: "",
        };
        return (
          <div
            key={analysisType}
            className={`analysis-card fade-in-up fade-in-delay-${idx + 1}`}
            style={{ marginTop: 20 }}
          >
            <div className="analysis-card__header">
              <div className="analysis-card__title">
                <span className="analysis-card__icon">{config.icon}</span>
                {config.label}
              </div>
              <div className="analysis-card__stats">
                <span className="analysis-card__stat">⏱ {item.execution_time.toFixed(1)}s</span>
                <span className="analysis-card__stat">📊 {item.token_count.toLocaleString()} token</span>
              </div>
            </div>

            {config.desc && (
              <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 12 }}>
                {config.desc}
              </p>
            )}

            {/* Placeholder image */}
            <div className="placeholder-image placeholder-image--sm" style={{ marginBottom: 12 }}>
              <div className="placeholder-image__icon">{config.icon}</div>
              <div className="placeholder-image__text">{config.label}配图</div>
            </div>

            <div className="analysis-card__actions">
              <Link to={`/result/${id}/${analysisType}`}>
                <InkButton type="button" kind="primary">
                  查看详情
                </InkButton>
              </Link>
              <InkButton type="button" kind="ghost" onClick={() => download(analysisType)}>
                下载此分析
              </InkButton>
            </div>
          </div>
        );
      })}
    </div>
  );
}
