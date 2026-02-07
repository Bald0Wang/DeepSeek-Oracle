interface LoadingAnimationProps {
  size?: "small" | "large";
}

export function LoadingAnimation({ size = "small" }: LoadingAnimationProps) {
  if (size === "large") {
    return <div className="loading-bagua" aria-label="loading" />;
  }

  return (
    <div className="loading-animation" aria-label="loading">
      <span />
      <span />
      <span />
    </div>
  );
}
