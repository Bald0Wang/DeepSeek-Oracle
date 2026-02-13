import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { HomeVariantPreview } from "../ui-home-variants/HomeVariantPreview";
import { DEFAULT_HOME_VARIANT_ID, HOME_VARIANTS } from "../ui-home-variants/variants";
import "../ui-home-variants/home-variants.css";

export default function HomeVariantsPage() {
  const [selectedId, setSelectedId] = useState(DEFAULT_HOME_VARIANT_ID);

  const selected = useMemo(
    () => HOME_VARIANTS.find((item) => item.id === selectedId) ?? HOME_VARIANTS[0],
    [selectedId],
  );

  return (
    <div className="home-variants-page fade-in">
      <header className="home-variants-header">
        <h1>首页风格筛选台</h1>
        <p>已拆分 10 种首页视觉方向，可逐个预览后再确定最终版本。</p>
      </header>

      <div className="home-variants-layout">
        <aside className="home-variants-list" aria-label="首页风格列表">
          {HOME_VARIANTS.map((item) => {
            const isActive = item.id === selected.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`home-variants-item ${isActive ? "home-variants-item--active" : ""}`}
                onClick={() => setSelectedId(item.id)}
              >
                <p className="home-variants-item__name">{item.name}</p>
                <p className="home-variants-item__tagline">{item.tagline}</p>
                <p className="home-variants-item__mood">氛围：{item.mood}</p>
              </button>
            );
          })}
        </aside>

        <section className="home-variants-preview-wrap" aria-label="首页风格预览">
          <HomeVariantPreview variant={selected} />
        </section>
      </div>

      <div className="actions-row">
        <Link to="/start-analysis" className="ink-button ink-button--secondary">
          返回分析首页
        </Link>
      </div>
    </div>
  );
}
