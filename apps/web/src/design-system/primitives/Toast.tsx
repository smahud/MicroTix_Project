import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from './Icon';
import { useT } from '../../i18n/useT';

type ToastTone = 'info' | 'success' | 'warning' | 'danger';

interface ToastItem {
  id: number;
  tone: ToastTone;
  message: string;
}

interface ToastContextValue {
  toast: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => undefined });

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const t = useT();

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, tone: ToastTone = 'info') => {
      const id = nextId++;
      setItems((prev) => [...prev.slice(-3), { id, tone, message }]);
      window.setTimeout(() => dismiss(id), 5000);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {createPortal(
        <div className="mt-toasts" aria-live="polite" aria-relevant="additions">
          {items.map((i) => (
            <div key={i.id} className={`mt-toast mt-toast-${i.tone}`} role="status">
              <Icon
                name={i.tone === 'success' ? 'checkCircle' : i.tone === 'danger' ? 'alertCircle' : i.tone === 'warning' ? 'alertTriangle' : 'info'}
                size={18}
                style={{ flexShrink: 0, marginTop: 1 }}
              />
              <span style={{ flex: 1 }}>{i.message}</span>
              <button type="button" className="mt-toast-close" onClick={() => dismiss(i.id)}>
                <Icon name="x" size={16} />
                <span className="mt-visually-hidden">{t('common.dismiss')}</span>
              </button>
            </div>
          ))}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  return useContext(ToastContext);
}
