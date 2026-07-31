export function MembershipMark({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 18 14" aria-hidden="true" focusable="false">
      <path fill="currentColor" d="M2.3 2h13.4c.78 0 1.2.9.72 1.52l-6.1 7.9a1.17 1.17 0 0 1-1.84 0l-6.1-7.9C1.9 2.9 2.34 2 3.1 2h-.8Z" />
      <path fill="#6d4b17" d="M5.78 4.75h6.44L9 8.8 5.78 4.75Z" />
    </svg>
  );
}
