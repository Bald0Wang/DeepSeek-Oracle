import type { PropsWithChildren, ReactNode } from "react";


interface InkCardProps extends PropsWithChildren {
  title?: ReactNode;
  icon?: ReactNode;
  className?: string;
}


export function InkCard({ title, icon, children, className = "" }: InkCardProps) {
  return (
    <section className={`ink-card ${className}`}>
      <div className="ink-card__corner ink-card__corner--tl" />
      <div className="ink-card__corner ink-card__corner--br" />
      {title ? (
        <h3 className="ink-card__title">
          {icon && <span className="ink-card__title-icon">{icon}</span>}
          {title}
        </h3>
      ) : null}
      <div className="ink-card__content">{children}</div>
    </section>
  );
}
