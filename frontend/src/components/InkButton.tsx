import type { ButtonHTMLAttributes, PropsWithChildren } from "react";


interface InkButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, PropsWithChildren {
  kind?: "primary" | "secondary" | "ghost";
  full?: boolean;
}


export function InkButton({ kind = "primary", full = false, children, className = "", ...rest }: InkButtonProps) {
  const cls = [
    "ink-button",
    `ink-button--${kind}`,
    full ? "ink-button--full" : "",
    className,
  ].filter(Boolean).join(" ");

  return (
    <button className={cls} {...rest}>
      {children}
    </button>
  );
}
