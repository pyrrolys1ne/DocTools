export const UI_VARIANTS = ["workspace", "rail", "focus"] as const;

export type UiVariant = (typeof UI_VARIANTS)[number];

export const UI_VARIANT_LABELS: Record<UiVariant, string> = {
  workspace: "Wide workspace",
  rail: "Three-column rail",
  focus: "Focused form",
};

export function isUiVariant(value: string | null): value is UiVariant {
  return value !== null && UI_VARIANTS.includes(value as UiVariant);
}
