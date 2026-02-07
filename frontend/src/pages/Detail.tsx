import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { exportReport, getResultItem } from "../api";
import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { LoadingAnimation } from "../components/LoadingAnimation";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import type { AnalysisDetailItem } from "../types";


const ANALYSIS_LABEL: Record<string, { label: string; icon: string }> = {
  marriage_path: { label: "婚姻道路", icon: "💍" },
  challenges: { label: "困难挑战", icon: "⚡" },
  partner_character: { label: "伴侣性格", icon: "🤝" },
};


export default function DetailPage() {
  const { id = "", type = "" } = useParams();
  const [item, setItem] = useState<AnalysisDetailItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analysisType =
    type === "marriage_path" || type === "challenges" || type === "partner_character"
      ? type
      : null;

  useEffect(() => {
    if (!id || !analysisType) return;
    (async () => {
      try {
        const response = await getResultItem(Number(id), analysisType);
        if (!response.data) throw new Error("detail not found");
        setItem(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "获取详情失败");
      }
    })();
  }, [analysisType, id]);

  const config = ANALYSIS_LABEL[analysisType || ""] || { label: type, icon: "📋" };

  const onDownload = async () => {
    if (!id || !analysisType) return;
    const response = await exportReport(Number(id), analysisType);
    const blob = new Blob([response.data], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `analysis_${id}_${analysisType}.md`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <InkCard title="详情读取失败" icon="⚠">
        <p className="error-text">{error}</p>
      </InkCard>
    );
  }

  if (!analysisType) {
    return (
      <InkCard title="详情读取失败" icon="⚠">
        <p className="error-text">无效的分析类型</p>
      </InkCard>
    );
  }

  if (!item) {
    return (
      <div className="loading-container" style={{ paddingTop: 80 }}>
        <LoadingAnimation size="large" />
        <p style={{ color: "var(--text-muted)", marginTop: 16 }}>正在加载分析详情…</p>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <Link to={`/result/${id}`} className="back-link">
        ← 返回总览
      </Link>

      <InkCard title={config.label} icon={config.icon}>
        {/* Stats */}
        <div className="meta-grid" style={{ marginBottom: 20 }}>
          <div className="meta-item">
            <div className="meta-item__label">分析耗时</div>
            <div className="meta-item__value">{item.execution_time.toFixed(1)}s</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">总 Token</div>
            <div className="meta-item__value">{item.token_count.toLocaleString()}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">输入 Token</div>
            <div className="meta-item__value">{item.input_tokens.toLocaleString()}</div>
          </div>
          <div className="meta-item">
            <div className="meta-item__label">输出 Token</div>
            <div className="meta-item__value">{item.output_tokens.toLocaleString()}</div>
          </div>
        </div>

        {/* Placeholder image */}
        <div className="placeholder-image placeholder-image--md" style={{ marginBottom: 20 }}>
          <div className="placeholder-image__icon">{config.icon}</div>
          <div className="placeholder-image__text">{config.label}详情配图</div>
        </div>

        <hr className="ink-divider" />

        {/* Content */}
        <div className="markdown-body">
          <MarkdownRenderer content={item.content} />
        </div>

        <hr className="ink-divider" />

        <div className="actions-row">
          <InkButton type="button" onClick={onDownload}>
            下载此分析
          </InkButton>
          <Link to={`/result/${id}`}>
            <InkButton type="button" kind="ghost">
              返回总览
            </InkButton>
          </Link>
        </div>
      </InkCard>
    </div>
  );
}
