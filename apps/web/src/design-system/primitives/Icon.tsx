import type { CSSProperties } from 'react';

/**
 * Set ikon tunggal, stroke konsisten (24 grid, 1.8px) —
 * mencegah ikon campuran antar modul (UI_UX.md: konsistensi ikon).
 */
const P: Record<string, string> = {
  home: 'M3 10.5 12 3l9 7.5M5 9.5V21h5v-6h4v6h5V9.5',
  users: 'M16 20v-1.5a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4V20M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm11 9v-1.5a4 4 0 0 0-3-3.87M16 3.5a4 4 0 0 1 0 7.5',
  server: 'M4 5h16v5H4zM4 14h16v5H4zM7.5 7.5h.01M7.5 16.5h.01',
  wifi: 'M2.5 9a15 15 0 0 1 19 0M5.5 12.5a10 10 0 0 1 13 0M8.5 16a5.5 5.5 0 0 1 7 0M12 19.5h.01',
  router: 'M3 14h18v6H3zM3 4h18v6H3zM6.5 17h.01M6.5 7h.01M11 17h5',
  database: 'M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3ZM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3',
  activity: 'M3 12h4l2.5-7 4 14L16 12h5',
  list: 'M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01',
  settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7.4-3a7.4 7.4 0 0 0-.1-1.2l2-1.6-2-3.4-2.4 1a7.4 7.4 0 0 0-2-1.2L14.5 3h-4l-.4 2.6a7.4 7.4 0 0 0-2 1.2l-2.4-1-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2.4l-2 1.6 2 3.4 2.4-1a7.4 7.4 0 0 0 2 1.2l.4 2.6h4l.4-2.6a7.4 7.4 0 0 0 2-1.2l2.4 1 2-3.4-2-1.6c.07-.4.1-.8.1-1.2Z',
  shield: 'M12 3 4.5 6v5c0 4.6 3.2 8.6 7.5 10 4.3-1.4 7.5-5.4 7.5-10V6L12 3Zm0 5v5m0 2.5h.01',
  plus: 'M12 5v14M5 12h14',
  search: 'M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15Zm5.8-1.7L21 21',
  filter: 'M4 5h16M7 12h10M10 19h4',
  chevronDown: 'm6 9 6 6 6-6',
  chevronLeft: 'm14 6-6 6 6 6',
  chevronRight: 'm10 6 6 6-6 6',
  chevronUpDown: 'm7 10 5-5 5 5M7 14l5 5 5-5',
  x: 'M6 6l12 12M18 6 6 18',
  copy: 'M9 9V5a1.5 1.5 0 0 1 1.5-1.5h8A1.5 1.5 0 0 1 20 5v8a1.5 1.5 0 0 1-1.5 1.5h-4M5 9h8a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 13 20H5a1.5 1.5 0 0 1-1.5-1.5v-8A1.5 1.5 0 0 1 5 9Z',
  check: 'm4.5 12.5 5 5L19.5 7',
  checkCircle: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-3.5-9 2.5 2.5 5-5',
  alertTriangle: 'M10.3 4.3 2.8 17a1.7 1.7 0 0 0 1.5 2.5h15.4a1.7 1.7 0 0 0 1.5-2.5L13.7 4.3a1.7 1.7 0 0 0-3.4 0ZM12 10v3.5m0 3h.01',
  alertCircle: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13v5m0 3h.01',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13h.01M12 11v5',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13.5V12l3 2',
  download: 'M12 3v12m0 0 4.5-4.5M12 15l-4.5-4.5M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2',
  upload: 'M12 21V9m0 0 4.5 4.5M12 9 7.5 13.5M4 7V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2',
  refresh: 'M20 11a8 8 0 1 0-2.3 6.4M20 5v6h-6',
  ellipsis: 'M6 12h.01M12 12h.01M18 12h.01',
  lock: 'M7 11V8a5 5 0 0 1 10 0v3M6 11h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1Zm6 3.5v2.5',
  key: 'M15 8.5a3.5 3.5 0 1 0-3.4 3.5L7 17l-3 3 2-5-2-1.5L7 14l5.5-5.5a3.5 3.5 0 0 0 2.5 0Z',
  eye: 'M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Zm9.5 2.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z',
  eyeOff: 'M4 4l16 16M9.9 5.9A9.9 9.9 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.6 3.4M6.6 8.1A17 17 0 0 0 2.5 12S6 18.5 12 18.5c.9 0 1.7-.1 2.5-.4M10 10a2.5 2.5 0 0 0 3.4 3.4',
  logout: 'M9 21H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3M16 8l4 4-4 4M20 12H9.5',
  menu: 'M4 7h16M4 12h16M4 17h16',
  arrowRight: 'M4 12h16m0 0-6-6m6 6-6 6',
  arrowLeft: 'M20 12H4m0 0 6-6m-6 6 6 6',
  building: 'M4 21V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v16M15 9h4a1 1 0 0 1 1 1v11M7 8h5M7 12h5M7 16h5M2.5 21h19',
  globe: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-9-9h18M12 3c2.5 2.5 3.5 5.5 3.5 9S14.5 18.5 12 21c-2.5-2.5-3.5-5.5-3.5-9S9.5 5.5 12 3Z',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-8 9c.5-4 4-6 8-6s7.5 2 8 6',
  mail: 'M3 6a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6Zm1 .5 8 6 8-6',
  phone: 'M5 4h3l2 5-2.5 1.5a11 11 0 0 0 5 5L14 13l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z',
  mapPin: 'M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11Zm0-8.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z',
  calendar: 'M4 6a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6Zm4-3v4m8-4v4M4 10h16',
  fileText: 'M6 3h8l4 4v14H6V3Zm8 0v4h4M9 12h6M9 16h6M9 8h2',
  trash: 'M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-9 0 1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13M10 11v6m4-6v6',
  edit: 'M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17v3Zm12-14 3 3',
  zap: 'M13 2 4 14h6l-1 8 9-12h-6l1-8Z',
  trendingUp: 'M3 17 9.5 10.5l4 4L21 7m0 0h-5m5 0v5',
  trendingDown: 'M3 7l6.5 6.5 4-4L21 17m0 0h-5m5 0v-5',
  wallet: 'M3 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v1H3V7Zm0 3h18a1 1 0 0 1 1 1v2.5M3 10v9a1 1 0 0 0 1 1h15a1 1 0 0 0 1-1v-2.5M17 15.5h4',
  gauge: 'M12 21a9 9 0 1 0-9-9m9 9c2.5 0 4.8-1 6.4-2.6L12 12m0 9Z',
  layers: 'm12 3 9 5-9 5-9-5 9-5Zm9 9-9 5-9-5m18 4-9 5-9-5',
  helpCircle: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-2.5-11A2.5 2.5 0 1 1 12 13v.5m0 3.5h.01',
  terminal: 'm5 7 5 5-5 5M12 17h7',
  hash: 'M6 9h13M5 15h13M10 4l-2 16M17 4l-2 16',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 1 0-5.7-5.7l-1.2 1.2M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 1 0 5.7 5.7l1.2-1.2',
  device: 'M6 3h12a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm4 14.5h4',
  spinner: 'M12 3a9 9 0 0 1 9 9',
};

export type IconName = keyof typeof P | string;

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  style?: CSSProperties;
}

export function Icon({ name, size = 20, className, style }: IconProps) {
  const d = P[name] ?? P.info;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden="true"
      focusable="false"
    >
      <path d={d} />
    </svg>
  );
}
