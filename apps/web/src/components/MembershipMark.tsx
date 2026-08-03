export function MembershipMark({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 18 16" aria-hidden="true" focusable="false">
      <path fill="currentColor" d="M5.1 1.5h7.8c.4 0 .77.18 1.02.5l2.42 3.04c.36.45.33 1.1-.07 1.52l-6.4 6.83a1.2 1.2 0 0 1-1.74 0l-6.4-6.83a1.15 1.15 0 0 1-.07-1.52L4.08 2c.25-.32.62-.5 1.02-.5Z" />
      <path fill="#765016" d="m6.35 5.35 2.65 3 2.65-3h-5.3Z" />
    </svg>
  );
}
