import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect } from "react";

import { UI_VARIANT_LABELS, UI_VARIANTS, type UiVariant } from "@/config/ui";

interface Props {
  value: UiVariant;
  onChange: (value: UiVariant) => void;
}

export function PrototypeSwitcher({ value, onChange }: Props) {
  useEffect(() => {
    if (!import.meta.env.DEV) return;

    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable
      ) {
        return;
      }
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;

      event.preventDefault();
      const current = UI_VARIANTS.indexOf(value);
      const direction = event.key === "ArrowRight" ? 1 : -1;
      onChange(UI_VARIANTS[(current + direction + UI_VARIANTS.length) % UI_VARIANTS.length]);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onChange, value]);

  if (!import.meta.env.DEV) return null;

  const current = UI_VARIANTS.indexOf(value);
  const cycle = (direction: number) => {
    onChange(UI_VARIANTS[(current + direction + UI_VARIANTS.length) % UI_VARIANTS.length]);
  };

  return (
    <div className="prototype-switcher" aria-label="UI prototype variants">
      <button type="button" onClick={() => cycle(-1)} aria-label="Previous UI variant" title="Previous variant">
        <ArrowLeft className="size-4" />
      </button>
      <span>
        <small>Prototype</small>
        {UI_VARIANT_LABELS[value]}
      </span>
      <button type="button" onClick={() => cycle(1)} aria-label="Next UI variant" title="Next variant">
        <ArrowRight className="size-4" />
      </button>
    </div>
  );
}
