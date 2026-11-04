import { useCallback, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import type { ReactNode } from 'react';
import { Icon } from './Icon';
import { useT } from '../../i18n/useT';

/**
 * Dialog mengunci fokus, bernama jelas, mengembalikan fokus ke pemicu (UI_UX.md §12).
 */
interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  width?: number;
}

export function Dialog({ open, onClose, title, children, footer, width }: DialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const restoreFocus = useRef<HTMLElement | null>(null);
  const t = useT();

  useEffect(() => {
    if (open) {
      restoreFocus.current = document.activeElement as HTMLElement | null;
      const first = panelRef.current?.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      first?.focus();
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prevOverflow;
        restoreFocus.current?.focus?.();
      };
    }
    return undefined;
  }, [open]);

  const onKey = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
      if (e.key === 'Tab' && panelRef.current) {
        const focusables = Array.from(
          panelRef.current.querySelectorAll<HTMLElement>(
            'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
          ),
        );
        if (focusables.length === 0) return;
        const first = focusables[0]!;
        const last = focusables[focusables.length - 1]!;
        if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        } else if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      }
    },
    [onClose],
  );

  if (!open) return null;
  return createPortal(
    <div
      className="mt-overlay"
      onKeyDown={onKey}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className="mt-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === 'string' ? title : undefined}
        style={width ? { width: `min(${width}px, 100%)` } : undefined}
      >
        <div className="mt-dialog-header">
          <h2 className="mt-dialog-title">{title}</h2>
          <button type="button" className="mt-btn mt-btn-ghost mt-btn-sm mt-btn-icon" onClick={onClose}>
            <Icon name="x" size={18} />
            <span className="mt-visually-hidden">{t('common.close_dialog')}</span>
          </button>
        </div>
        {children ? <div className="mt-dialog-body">{children}</div> : null}
        {footer ? <div className="mt-dialog-footer">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
}

export function Drawer({ open, onClose, title, children, footer }: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const t = useT();
  useEffect(() => {
    if (open) {
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prevOverflow;
      };
    }
    return undefined;
  }, [open]);

  if (!open) return null;
  return createPortal(
    <div
      className="mt-overlay"
      style={{ justifyContent: 'flex-end', padding: 0 }}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose();
      }}
    >
      <div ref={panelRef} className="mt-drawer mt-drawer-right" role="dialog" aria-modal="true" aria-label={typeof title === 'string' ? title : undefined}>
        <div className="mt-dialog-header">
          <h2 className="mt-dialog-title">{title}</h2>
          <button type="button" className="mt-btn mt-btn-ghost mt-btn-sm mt-btn-icon" onClick={onClose}>
            <Icon name="x" size={18} />
            <span className="mt-visually-hidden">{t('common.close_panel')}</span>
          </button>
        </div>
        <div className="mt-dialog-body">{children}</div>
        {footer ? <div className="mt-dialog-footer">{footer}</div> : null}
      </div>
    </div>,
    document.body,
  );
}
