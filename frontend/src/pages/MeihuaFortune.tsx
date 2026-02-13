import { FormEvent, useEffect, useMemo, useState } from "react";

import { InkButton } from "../components/InkButton";
import { InkCard } from "../components/InkCard";
import { MarkdownRenderer } from "../components/MarkdownRenderer";
import {
  clearMeihuaFortuneError,
  getMeihuaFortuneSessionState,
  setMeihuaFortuneError,
  startMeihuaDivinationTask,
  subscribeMeihuaFortuneSession,
  updateMeihuaFortuneForm,
} from "../stores/meihuaFortuneSession";

export default function MeihuaFortunePage() {
  const [session, setSession] = useState(getMeihuaFortuneSessionState());

  useEffect(() => {
    const unsubscribe = subscribeMeihuaFortuneSession((state) => {
      setSession(state);
    });
    return unsubscribe;
  }, []);

  const quickTopics = useMemo(
    () => [
      "我这周适合主动推进一次重要沟通吗？",
      "近期换工作机会，该保守还是积极？",
      "这段关系短期应如何相处更稳妥？",
    ],
    []
  );

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearMeihuaFortuneError();
    if (!session.form.topic.trim()) {
      setMeihuaFortuneError("请先输入占题。");
      return;
    }

    await startMeihuaDivinationTask({
      topic: session.form.topic.trim(),
    });
  };

  return (
    <div className="stack fade-in">
      <InkCard title="梅花易数求签" icon="梅">
        <form className="stack" onSubmit={onSubmit}>
          <div className="field">
            <label className="field__label" htmlFor="meihua-topic">占题</label>
            <textarea
              id="meihua-topic"
              className="oracle-chat__textarea"
              value={session.form.topic}
              onChange={(event) => updateMeihuaFortuneForm({ topic: event.target.value })}
              placeholder="例如：我这周是否适合推进一次关键决策？"
              rows={3}
            />
            <div className="oracle-chat__prompt-grid" aria-label="备选占题">
              {quickTopics.map((item, index) => (
                <button
                  key={`${item}-${index}`}
                  type="button"
                  className="oracle-chat__prompt-chip"
                  onClick={() => updateMeihuaFortuneForm({ topic: item })}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <p className="field__hint">
            起卦因子说明：系统会在你点击“开始梅花求签”时，自动使用当前时间起卦（无需手动输入时间）。
          </p>

          {session.error ? <p className="error-text">{session.error}</p> : null}
          {session.loading ? <p className="oracle-chat__tip">任务进行中，切换页面后回来仍会保留状态。</p> : null}
          <div className="actions-row">
            <InkButton type="submit" disabled={session.loading}>
              {session.loading ? "求签中..." : "开始梅花求签"}
            </InkButton>
          </div>
        </form>
      </InkCard>

      {session.result ? (
        <div className="stack fade-in-up">
          <InkCard title="起卦信息" icon="卦">
            <div className="meta-grid">
              <div className="meta-item">
                <p className="meta-item__label">本卦</p>
                <p className="meta-item__value">{session.result.gua.base_gua}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">变卦</p>
                <p className="meta-item__value">{session.result.gua.changed_gua}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">互卦</p>
                <p className="meta-item__value">{session.result.gua.mutual_gua || "-"}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">动爻</p>
                <p className="meta-item__value">{session.result.gua.moving_line_name}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">体/用</p>
                <p className="meta-item__value">{session.result.gua.ti_gua || "-"} / {session.result.gua.yong_gua || "-"}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">体用关系</p>
                <p className="meta-item__value">{session.result.gua.relation || "-"}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">卦象</p>
                <p className="meta-item__value">{session.result.gua.symbol}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">阴阳线（本）</p>
                <p className="meta-item__value">{session.result.gua.base_line_pattern}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">阴阳线（变）</p>
                <p className="meta-item__value">{session.result.gua.changed_line_pattern}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">seed</p>
                <p className="meta-item__value">{session.result.gua.seed}</p>
              </div>
              <div className="meta-item">
                <p className="meta-item__label">模型</p>
                <p className="meta-item__value">{session.result.provider} / {session.result.model}</p>
              </div>
            </div>
          </InkCard>

          <InkCard title="梅花解读结果" icon="解">
            <div className="markdown-body">
              <MarkdownRenderer content={session.result.reading} />
            </div>
          </InkCard>
        </div>
      ) : null}
    </div>
  );
}
