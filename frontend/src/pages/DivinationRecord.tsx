import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getDivinationHistoryDetail } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LoadingAnimation } from "../components/LoadingAnimation";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import type { DivinationHistoryDetail, MeihuaDivinationResponse, ZiweiDivinationResponse } from "../types";

export default function DivinationRecordPage() {
  const { id = "" } = useParams();
  const [detail, setDetail] = useState<DivinationHistoryDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      return;
    }
    (async () => {
      try {
        const response = await getDivinationHistoryDetail(Number(id));
        if (!response.data) {
          throw new Error("divination record not found");
        }
        setDetail(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "获取占卜记录失败");
      }
    })();
  }, [id]);

  const ziweiResult = useMemo(() => {
    if (!detail || detail.type !== "ziwei") {
      return null;
    }
    return detail.result as unknown as ZiweiDivinationResponse;
  }, [detail]);

  const meihuaResult = useMemo(() => {
    if (!detail || detail.type !== "meihua") {
      return null;
    }
    return detail.result as unknown as MeihuaDivinationResponse;
  }, [detail]);

  if (error) {
    return (
      <InkCard title="占卜记录读取失败">
        <p className="error-text">{error}</p>
      </InkCard>
    );
  }

  if (!detail) {
    return (
      <div className="loading-container loading-container--page">
        <LoadingAnimation size="large" />
        <p className="loading-state-text">正在加载占卜记录...</p>
      </div>
    );
  }

  return (
    <div className="stack fade-in">
      <InkCard title={detail.type === "ziwei" ? "紫微斗数记录" : "梅花易数记录"}>
        <div className="meta-grid meta-grid--compact">
          <div className="meta-item">
            <p className="meta-item__label">存储时间</p>
            <p className="meta-item__value">{detail.created_at}</p>
          </div>
          <div className="meta-item">
            <p className="meta-item__label">模型</p>
            <p className="meta-item__value">{detail.provider} / {detail.model}</p>
          </div>
          <div className="meta-item">
            <p className="meta-item__label">问题</p>
            <p className="meta-item__value">{detail.question_text}</p>
          </div>
        </div>
        <div className="actions-row">
          <Link to="/history">
            <InkButton type="button" kind="ghost">返回历史记录</InkButton>
          </Link>
        </div>
      </InkCard>

      {detail.type === "ziwei" && ziweiResult ? (
        <>
          <InkCard title="紫微解读">
            <div className="markdown-body">
              <MarkdownRenderer content={ziweiResult.reading || ""} />
            </div>
          </InkCard>
          <InkCard title="命盘摘要">
            <pre className="pre-wrap">{ziweiResult.chart_summary || ""}</pre>
          </InkCard>
        </>
      ) : null}

      {detail.type === "meihua" && meihuaResult ? (
        <>
          <InkCard title="起卦信息">
            <div className="meta-grid">
              <div className="meta-item">
                <p className="meta-item__label">本卦</p>
                <p className="meta-item__value">{meihuaResult.gua?.base_gua || "-"}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">变卦</p>
                <p className="meta-item__value">{meihuaResult.gua?.changed_gua || "-"}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">互卦</p>
                <p className="meta-item__value">{meihuaResult.gua?.mutual_gua || "-"}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">动爻</p>
                <p className="meta-item__value">{meihuaResult.gua?.moving_line_name || "-"}</p>
              </div>
            </div>
          </InkCard>
          <InkCard title="梅花解读">
            <div className="markdown-body">
              <MarkdownRenderer content={meihuaResult.reading || ""} />
            </div>
          </InkCard>
        </>
      ) : null}
    </div>
  );
}
