import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { exportReport, getInsightOverview, getResult } from "../api";
import { ExecutionTimeChart } from "../components/ExecutionTimeChart";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LifeKlineChart } from "../components/LifeKlineChart";
import { LoadingAnimation } from "../components/LoadingAnimation";
import type { AnalysisResult, InsightOverviewData } from "../types";


const ANALYSIS_CONFIG: Record<string, { label: string; desc: string }> = {
  marriage_path: {
    label: "婚姻道路",
    desc: "解读夫妻宫星曜关系，分析感情走向与关键阶段。",
  },
  challenges: {
    label: "困难挑战",
    desc: "识别常见阻力来源，提供更务实的应对建议。",
  },
  partner_character: {
    label: "伴侣性格",
    desc: "分析伴侣可能的性格倾向与相处节奏。",
  },
};


export default function ResultPage() {
  const { id = "" } = useParams();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [insight, setInsight] = useState<InsightOverviewData | null>(null);
  const [insightError, setInsightError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      return;
    }

    (async () => {
      try {
        const response = await getResult(Number(id));
        if (!response.data) {
          throw new Error("result not found");
        }
        setResult(response.data);

        try {
          const insightRes = await getInsightOverview(Number(id));
          setInsight(insightRes.data || null);
        } catch (insightErr) {
          setInsightError(insightErr instanceof Error ? insightErr.message : "获取日历与K线失败");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "获取结果失败");
      }
    })();
  }, [id]);

  const download = async (scope: string) => {
    if (!id) {
      return;
    }
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
      <InkCard title="结果读取失败">
        <p className="error-text">{error}</p>
      </InkCard>
    );
  }

  if (!result) {
    return (
      <div className="loading-container loading-container--page">
        <LoadingAnimation size="large" />
        <p className="loading-state-text">正在加载分析结果...</p>
      </div>
    );
  }

  const calendarLabel = result.birth_info.calendar === "solar" ? "阳历" : "阴历";

  return (
    <div className="fade-in">
      <InkCard title="命盘总览">
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

        {result.text_description && (
          <>
            <hr className="ink-divider" />
            <details>
              <summary className="details-toggle">展开命盘描述</summary>
              <div className="pre-wrap">{result.text_description}</div>
            </details>
          </>
        )}

        <div className="actions-row">
          <InkButton type="button" onClick={() => download("full")}>
            下载完整报告
          </InkButton>
          <Link to="/insights">
            <InkButton type="button" kind="ghost">
              打开人生线/日历模块
            </InkButton>
          </Link>
          <Link to="/history">
            <InkButton type="button" kind="ghost">
              查看历史记录
            </InkButton>
          </Link>
        </div>
      </InkCard>

      <InkCard title="推理耗时分布">
        <ExecutionTimeChart
          rows={Object.entries(result.analysis).map(([analysisType, item]) => ({
            key: analysisType,
            label: ANALYSIS_CONFIG[analysisType]?.label || analysisType,
            seconds: Number(item.execution_time || 0),
          }))}
        />
      </InkCard>

      <InkCard title="近30天紫微日历">
        {insightError ? <p className="error-text">{insightError}</p> : null}
        {!insight ? (
          <p className="loading-state-text">正在生成或读取日历...</p>
        ) : (
          <>
            <p className="home-search__hint">
              当前月：{insight.calendar.current_month.month_key} · 主轴：{insight.calendar.current_month.dominant_focus}
            </p>
            <div className="calendar-grid">
              {insight.calendar.near_30_days.map((day) => (
                <article key={day.date} className="calendar-day-card">
                  <p className="calendar-day-card__date">{day.date}</p>
                  <p className="calendar-day-card__score">{day.level} · {day.score}</p>
                  <p className="calendar-day-card__text">宜：{day.yi.join("、")}</p>
                  <p className="calendar-day-card__text">忌：{day.ji.join("、")}</p>
                  <p className="calendar-day-card__text">{day.note}</p>
                </article>
              ))}
            </div>
          </>
        )}
      </InkCard>

      <InkCard title="人生K线（每5年关键点）">
        {!insight ? (
          <p className="loading-state-text">正在生成或读取人生K线...</p>
        ) : (
          <>
            <div className="meta-grid meta-grid--compact">
              <div className="meta-item">
                <div className="meta-item__label">平均分</div>
                <div className="meta-item__value">{insight.life_kline.summary.averageScore}</div>
              </div>
              <div className="meta-item">
                <div className="meta-item__label">高点年龄</div>
                <div className="meta-item__value">{insight.life_kline.summary.bestYears.join(" / ")}</div>
              </div>
              <div className="meta-item">
                <div className="meta-item__label">低点年龄</div>
                <div className="meta-item__value">{insight.life_kline.summary.worstYears.join(" / ")}</div>
              </div>
            </div>
            <p className="home-search__hint">{insight.life_kline.summary.overallTrend}</p>
            <LifeKlineChart
              points={insight.life_kline.sparse.years}
              bestYears={insight.life_kline.summary.bestYears}
              worstYears={insight.life_kline.summary.worstYears}
            />
            <div className="kline-list">
              {insight.life_kline.sparse.years.map((item) => (
                <article key={`${item.age}-${item.year}`} className="kline-item">
                  <p className="kline-item__title">{item.age}岁 · {item.year} · {item.yearGanZhi}</p>
                  <p className="kline-item__meta">评分 {item.score} · {item.summary} · 大运 {item.daYun}</p>
                </article>
              ))}
            </div>
          </>
        )}
      </InkCard>

      {Object.entries(result.analysis).map(([analysisType, item], idx) => {
        const config = ANALYSIS_CONFIG[analysisType] || {
          label: analysisType,
          desc: "",
        };

        return (
          <section
            key={analysisType}
            className="analysis-card fade-in-up"
            style={{ animationDelay: `${(idx + 1) * 0.06}s` }}
          >
            <div className="analysis-card__header">
              <h2 className="analysis-card__title">{config.label}</h2>
              <div className="analysis-card__stats">
                <span className="analysis-card__stat">{item.execution_time.toFixed(1)}s</span>
                <span className="analysis-card__stat">{item.token_count.toLocaleString()} tokens</span>
              </div>
            </div>

            {config.desc && <p className="analysis-card__summary">{config.desc}</p>}

            <div className="analysis-card__actions">
              <Link to={`/result/${id}/${analysisType}`}>
                <InkButton type="button">查看详情</InkButton>
              </Link>
              <InkButton type="button" kind="ghost" onClick={() => download(analysisType)}>
                下载此分析
              </InkButton>
            </div>
          </section>
        );
      })}
    </div>
  );
}
