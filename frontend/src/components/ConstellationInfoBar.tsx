import { CONSTELLATION_INFOS, ELEMENT_METAS, ELEMENT_SEQUENCE } from "../constants/constellations";


interface ConstellationInfoBarProps {
  activeIndex: number;
}


export function ConstellationInfoBar({ activeIndex }: ConstellationInfoBarProps) {
  const safeIndex = ((activeIndex % CONSTELLATION_INFOS.length) + CONSTELLATION_INFOS.length) % CONSTELLATION_INFOS.length;
  const info = CONSTELLATION_INFOS[safeIndex];
  const activeElement = ELEMENT_METAS[info.element];

  return (
    <section className="constellation-bar" aria-live="polite">
      <div className="constellation-bar__inner fade-in-up" key={info.nameEn}>
        <header className="constellation-bar__title">
          <span className="constellation-bar__name">{info.nameCn}</span>
          <span className="constellation-bar__latin">{info.nameEn}</span>
        </header>

        <p className="constellation-bar__summary">{info.summary}</p>

        <div className="constellation-bar__meta">
          <span className={`constellation-chip constellation-chip--${activeElement.key}`}>
            <span className="constellation-chip__icon" aria-hidden="true">{activeElement.icon}</span>
            五行 · {activeElement.label}
          </span>
          <span className="constellation-verse">{info.verse}</span>
        </div>

        <div className="element-legend" aria-label="五行对应标签">
          {ELEMENT_SEQUENCE.map((elementKey) => {
            const element = ELEMENT_METAS[elementKey];
            return (
              <span key={element.key} className={`element-legend__item element-legend__item--${element.key}`}>
                <span className="element-legend__icon" aria-hidden="true">{element.icon}</span>
                {element.label}
              </span>
            );
          })}
        </div>
      </div>
    </section>
  );
}
