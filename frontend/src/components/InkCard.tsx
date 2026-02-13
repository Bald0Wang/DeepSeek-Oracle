import type { PropsWithChildren, ReactNode } from "react";


interface InkCardProps extends PropsWithChildren {
  title?: ReactNode;
  icon?: ReactNode;
  className?: string;
}


export function InkCard({ title, icon, children, className = "" }: InkCardProps) {
  const cardClassName = ["ink-card", "ink-card--ornate", className].filter(Boolean).join(" ");

  return (
    <section className={cardClassName}>
      {title ? (
        <header className="ink-card__header">
          <h3 className="ink-card__title">
            {icon && <span className="ink-card__title-icon">{icon}</span>}
            {title}
          </h3>
        </header>
      ) : null}
      <div className="ink-card__content">{children}</div>
    </section>
  );
}
