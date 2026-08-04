import { Check, ChevronDown } from "lucide-react";
import { createPortal } from "react-dom";
import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";

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
  const [activeIndex, setActiveIndex] = useState(0);
  const [menuStyle, setMenuStyle] = useState<React.CSSProperties>({});
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const listboxId = useId();
  const selected = useMemo(() => options.find((option) => option.value === value) ?? options[0], [options, value]);
  const selectedIndex = Math.max(0, options.findIndex((option) => option.value === selected?.value));

  const closeMenu = (restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) window.requestAnimationFrame(() => triggerRef.current?.focus());
  };

  const updateMenuPosition = () => {
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const viewportGap = 8;
    const controlGap = 5;
    const estimatedHeight = Math.min(290, options.length * 34 + 10);
    const roomBelow = window.innerHeight - rect.bottom - viewportGap;
    const roomAbove = rect.top - viewportGap;
    const opensUp = roomBelow < Math.min(estimatedHeight, 150) && roomAbove > roomBelow;
    const availableHeight = Math.max(88, Math.min(290, (opensUp ? roomAbove : roomBelow) - controlGap));
    const menuHeight = Math.min(estimatedHeight, availableHeight);
    const width = Math.max(rect.width, 120);
    const left = Math.min(Math.max(viewportGap, rect.left), Math.max(viewportGap, window.innerWidth - width - viewportGap));
    setMenuStyle({
      left,
      top: opensUp ? Math.max(viewportGap, rect.top - controlGap - menuHeight) : rect.bottom + controlGap,
      width,
      maxHeight: availableHeight,
      transformOrigin: opensUp ? "bottom center" : "top center",
    });
  };

  const focusOption = (index: number) => {
    if (!options.length) return;
    const nextIndex = (index + options.length) % options.length;
    setActiveIndex(nextIndex);
    window.requestAnimationFrame(() => optionRefs.current[nextIndex]?.focus());
  };

  const commitOption = (index: number) => {
    const option = options[index];
    if (!option) return;
    onChange(option.value);
    closeMenu(true);
  };

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!rootRef.current?.contains(target) && !menuRef.current?.contains(target)) closeMenu();
    };
    const onViewportChange = () => updateMenuPosition();
    document.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("resize", onViewportChange);
    window.addEventListener("scroll", onViewportChange, true);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("resize", onViewportChange);
      window.removeEventListener("scroll", onViewportChange, true);
    };
  }, [open, options.length]);

  useLayoutEffect(() => {
    if (!open) return;
    setActiveIndex(selectedIndex);
    updateMenuPosition();
    window.requestAnimationFrame(() => optionRefs.current[selectedIndex]?.focus());
  }, [open, selectedIndex]);

  return (
    <div
      className={open ? "app-select is-open" : "app-select"}
      ref={rootRef}
      onKeyDown={(event) => {
        if (event.key === "Escape" && open) {
          event.preventDefault();
          event.stopPropagation();
          closeMenu(true);
        }
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
          setActiveIndex(selectedIndex);
          setOpen(true);
        }}
      >
        <span>{selected?.label ?? value}</span>
        <ChevronDown size={15} aria-hidden="true" />
      </button>
      {open && createPortal(
        <div
          className="app-select-menu"
          id={listboxId}
          ref={menuRef}
          role="listbox"
          aria-label={ariaLabel}
          style={menuStyle}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              focusOption(activeIndex + 1);
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              focusOption(activeIndex - 1);
            } else if (event.key === "Home") {
              event.preventDefault();
              focusOption(0);
            } else if (event.key === "End") {
              event.preventDefault();
              focusOption(options.length - 1);
            } else if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              commitOption(activeIndex);
            } else if (event.key === "Escape") {
              event.preventDefault();
              closeMenu(true);
            } else if (event.key === "Tab") {
              closeMenu();
            }
          }}
        >
          {options.map((option) => (
            <button
              key={option.value}
              id={`${listboxId}-${option.value}`}
              ref={(element) => { optionRefs.current[options.indexOf(option)] = element; }}
              className={`app-select-option${option.value === value ? " is-selected" : ""}${options[activeIndex]?.value === option.value ? " is-active" : ""}`}
              type="button"
              role="option"
              tabIndex={options[activeIndex]?.value === option.value ? 0 : -1}
              aria-selected={option.value === value}
              onFocus={() => setActiveIndex(options.indexOf(option))}
              onPointerMove={() => setActiveIndex(options.indexOf(option))}
              onClick={() => commitOption(options.indexOf(option))}
            >
              <span>{option.label}</span>
              <Check size={14} aria-hidden="true" />
            </button>
          ))}
        </div>,
        document.body,
      )}
    </div>
  );
}
