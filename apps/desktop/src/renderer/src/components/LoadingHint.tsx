/** Uniform async placeholder: spinner + text, styled by the caller's container class. */
export function LoadingHint({ className, label }: { className: string; label: string }) {
  return (
    <div className={className}>
      <span className="spinner" aria-hidden="true" /> {label}
    </div>
  );
}
