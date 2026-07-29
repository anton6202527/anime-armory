export function BrandIcon() {
  return (
    <svg className="labutv-mark" viewBox="0 0 48 48" aria-hidden="true">
      <defs>
        <linearGradient id="labutv-brand-gradient" x1="7" y1="5" x2="42" y2="44" gradientUnits="userSpaceOnUse">
          <stop stopColor="#9b8cff" />
          <stop offset=".52" stopColor="#736dff" />
          <stop offset="1" stopColor="#536df6" />
        </linearGradient>
      </defs>
      <rect className="labutv-mark__tile" x="2" y="2" width="44" height="44" rx="13" />
      <path className="labutv-mark__l" d="M15 13.5v17.8c0 2.4 1.9 4.2 4.2 4.2H34" />
      <path className="labutv-mark__play" d="m23 17.5 12 7.2-12 7.2z" />
    </svg>
  );
}
