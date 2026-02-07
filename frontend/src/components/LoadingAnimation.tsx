interface LoadingAnimationProps {
  size?: "small" | "large";
}

export function LoadingAnimation({ size = "small" }: LoadingAnimationProps) {
  return (
    <div className={`loading-indicator loading-indicator--${size}`} aria-label="loading">
      <span className="loading-indicator__dot" />
      <span className="loading-indicator__dot" />
      <span className="loading-indicator__dot" />
    </div>
  );
}
