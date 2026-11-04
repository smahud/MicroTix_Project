import { forwardRef } from 'react';
import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from './Icon';
import type { IconName } from './Icon';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size = 'md' | 'sm' | 'icon';

interface BaseProps {
  variant?: Variant;
  size?: Size;
  icon?: IconName;
  iconRight?: IconName;
  loading?: boolean;
  /** Alasan disabled ditampilkan dekat kontrol (UI_UX.md §2). */
  disabledReason?: ReactNode;
  children?: ReactNode;
}

export type ButtonProps = BaseProps & ButtonHTMLAttributes<HTMLButtonElement>;

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', icon, iconRight, loading = false, disabled, disabledReason, children, className = '', ...rest },
  ref,
) {
  const cls = [
    'mt-btn',
    `mt-btn-${variant}`,
    size === 'sm' ? 'mt-btn-sm' : '',
    size === 'icon' ? 'mt-btn-icon' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <>
      <button
        ref={ref}
        type={rest.type ?? 'button'}
        className={cls}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...rest}
      >
        {loading ? <Icon name="spinner" size={18} className="mt-spinner" /> : icon ? <Icon name={icon} size={18} /> : null}
        {children}
        {iconRight && !loading ? <Icon name={iconRight} size={18} /> : null}
      </button>
      {disabled && disabledReason ? (
        <span className="mt-btn-disabled-note">
          <Icon name="info" size={14} />
          {disabledReason}
        </span>
      ) : null}
    </>
  );
});

/** Tautan untuk navigasi, tombol untuk aksi (UI_UX.md §2). */
export function ButtonLink({
  to,
  variant = 'secondary',
  size = 'md',
  icon,
  iconRight,
  children,
  className = '',
  ...rest
}: BaseProps & { to: string } & Record<string, unknown>) {
  const cls = [
    'mt-btn',
    `mt-btn-${variant}`,
    size === 'sm' ? 'mt-btn-sm' : '',
    size === 'icon' ? 'mt-btn-icon' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <Link to={to} className={cls} {...rest}>
      {icon ? <Icon name={icon} size={18} /> : null}
      {children}
      {iconRight ? <Icon name={iconRight} size={18} /> : null}
    </Link>
  );
}
