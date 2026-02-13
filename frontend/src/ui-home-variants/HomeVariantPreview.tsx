import type { HomeVariantSpec } from "./variants";

interface HomeVariantPreviewProps {
  variant: HomeVariantSpec;
}

const SAMPLE_FIELDS = [
  "历法",
  "性别",
  "出生年",
  "出生月",
  "出生日",
  "出生时（24小时）",
  "出生分",
];

export function HomeVariantPreview({ variant }: HomeVariantPreviewProps) {
  return (
    <section className={`variant-preview ${variant.className}`}>
      <div className="variant-preview__texture" aria-hidden="true" />
      <header className="variant-preview__header">
        <p className="variant-preview__badge">天衍 Oracle · 首页草案</p>
        <h2>{variant.name}</h2>
        <p className="variant-preview__tagline">{variant.tagline}</p>
      </header>

      <div className="variant-preview__hero">
        <div className="variant-preview__hero-copy">
          <p className="variant-preview__lead">东方命理分析入口</p>
          <p className="variant-preview__text">
            先录入出生信息，再进入推演流程。该风格用于首页视觉方向筛选，不影响业务流程。
          </p>
        </div>
        <div className="variant-preview__chips">
          <span>占法：紫微 / 梅花 / 心学</span>
          <span>目标：年轻用户</span>
          <span>语气：安抚 + 可执行</span>
        </div>
      </div>

      <div className="variant-preview__form-grid">
        {SAMPLE_FIELDS.map((field) => (
          <div key={field} className="variant-preview__field">
            <p>{field}</p>
            <div className="variant-preview__input" />
          </div>
        ))}
      </div>

      <footer className="variant-preview__footer">
        <button type="button" className="variant-preview__button variant-preview__button--primary">
          开始分析
        </button>
        <button type="button" className="variant-preview__button">
          转到咨询对话
        </button>
      </footer>
    </section>
  );
}
