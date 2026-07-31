import { Check, ChevronDown } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

export interface SelectMenuOption<T extends string> {
  value: T;
  label: string;
}

interface SelectMenuProps<T extends string> {
  value: T;
  options: ReadonlyArray<SelectMenuOption<T>>;
  onChange: (value: T) => void;
  ariaLabel: string;
}

export function SelectMenu<T extends string>({ value, options, onChange, ariaLabel }: SelectMenuProps<T>) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listboxId = useId();
  const selected = useMemo(() => options.find((option) => option.value === value) ?? options[0], [options, value]);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open]);

  return (
    <div
      className={open ? "app-select is-open" : "app-select"}
      ref={rootRef}
      onKeyDown={(event) => {
        if (!open || event.key !== "Escape") return;
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
        triggerRef.current?.focus();
      }}
    >
      <button
        ref={triggerRef}
        className="app-select-trigger"
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-controls={listboxId}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
          event.preventDefault();
          setOpen(true);
        }}
      >
        <span>{selected?.label ?? value}</span>
        <ChevronDown size={15} aria-hidden="true" />
      </button>
      {open && (
        <div className="app-select-menu" id={listboxId} role="listbox" aria-label={ariaLabel}>
          {options.map((option) => (
            <button
              key={option.value}
              className={option.value === value ? "app-select-option is-selected" : "app-select-option"}
              type="button"
              role="option"
              aria-selected={option.value === value}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
                triggerRef.current?.focus();
              }}
            >
              <span>{option.label}</span>
              <Check size={14} aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
