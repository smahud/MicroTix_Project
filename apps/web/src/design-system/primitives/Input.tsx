import { forwardRef, useId } from 'react';
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';
import { Icon } from './Icon';

/**
 * Form: label permanen, helper sebelum error, validasi server sebagai otoritas
 * (UI_UX.md §2). FieldError terasosiasi via aria-describedby.
 */
interface BaseFieldProps {
  label: ReactNode;
  htmlFor?: string;
  helper?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  children: (id: string, describedBy: string | undefined) => ReactNode;
}

export function Field({ label, helper, error, required, children }: BaseFieldProps) {
  const id = useId();
  const helperId = helper ? `${id}-helper` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helperId, errorId].filter(Boolean).join(' ') || undefined;
  return (
    <div className="mt-field">
      <label className="mt-label" htmlFor={id}>
        {label}
        {required ? (
          <span aria-hidden="true" style={{ color: 'var(--mt-danger-fg)' }}>
            *
          </span>
        ) : (
          <span className="mt-label-optional" />
        )}
      </label>
      {children(id, describedBy)}
      {helper && !error ? (
        <p className="mt-helper" id={helperId}>
          {helper}
        </p>
      ) : null}
      {error ? (
        <p className="mt-field-error" id={errorId} role="alert">
          <Icon name="alertCircle" size={16} style={{ flexShrink: 0, marginTop: 3 }} />
          <span>{error}</span>
        </p>
      ) : null}
    </div>
  );
}

export interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: ReactNode;
  helper?: ReactNode;
  error?: ReactNode;
  icon?: string;
}

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(function TextInput(
  { label, helper, error, icon, required, className, ...rest },
  ref,
) {
  return (
    <Field label={label} helper={helper} error={error} required={required}>
      {(id, describedBy) =>
        icon ? (
          <div className="mt-input-wrap">
            <span className="mt-input-icon">
              <Icon name={icon} size={18} />
            </span>
            <input
              ref={ref}
              id={id}
              className={`mt-input ${className ?? ''}`}
              aria-describedby={describedBy}
              aria-invalid={error ? true : undefined}
              required={required}
              {...rest}
            />
          </div>
        ) : (
          <input
            ref={ref}
            id={id}
            className={`mt-input ${className ?? ''}`}
            aria-describedby={describedBy}
            aria-invalid={error ? true : undefined}
            required={required}
            {...rest}
          />
        )
      }
    </Field>
  );
});

export interface SelectInputProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: ReactNode;
  helper?: ReactNode;
  error?: ReactNode;
  options: Array<{ value: string; label: string; disabled?: boolean }>;
  placeholderOption?: string;
}

export const SelectInput = forwardRef<HTMLSelectElement, SelectInputProps>(function SelectInput(
  { label, helper, error, options, placeholderOption, required, className, ...rest },
  ref,
) {
  return (
    <Field label={label} helper={helper} error={error} required={required}>
      {(id, describedBy) => (
        <select
          ref={ref}
          id={id}
          className={`mt-select ${className ?? ''}`}
          aria-describedby={describedBy}
          aria-invalid={error ? true : undefined}
          required={required}
          {...rest}
        >
          {placeholderOption ? (
            <option value="">{placeholderOption}</option>
          ) : null}
          {options.map((o) => (
            <option key={o.value} value={o.value} disabled={o.disabled}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  );
});

export interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: ReactNode;
  helper?: ReactNode;
  error?: ReactNode;
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  { label, helper, error, required, className, ...rest },
  ref,
) {
  return (
    <Field label={label} helper={helper} error={error} required={required}>
      {(id, describedBy) => (
        <textarea
          ref={ref}
          id={id}
          className={`mt-textarea ${className ?? ''}`}
          aria-describedby={describedBy}
          aria-invalid={error ? true : undefined}
          required={required}
          {...rest}
        />
      )}
    </Field>
  );
});

export function Checkbox({
  label,
  hint,
  ...rest
}: InputHTMLAttributes<HTMLInputElement> & { label: ReactNode; hint?: ReactNode }) {
  const id = useId();
  return (
    <span className="mt-check">
      <input type="checkbox" id={id} {...rest} />
      <span>
        <label htmlFor={id} style={{ cursor: 'inherit' }}>
          {label}
        </label>
        {hint ? (
          <span className="mt-helper" style={{ display: 'block' }}>
            {hint}
          </span>
        ) : null}
      </span>
    </span>
  );
}
