"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";

const OPTIONS = [
  { value: "light", label: "Claro", Icon: Sun },
  { value: "dark", label: "Oscuro", Icon: Moon },
  { value: "system", label: "Sistema", Icon: Monitor },
] as const;

const subscribe = () => () => {};

/** Light, dark, or the same as the system. The choice is saved on the device. */
export function ThemeSelector() {
  const { theme, setTheme } = useTheme();
  // The saved choice is only known in the browser; mark none until then.
  const mounted = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );

  return (
    <div role="radiogroup" aria-label="Apariencia" className="grid grid-cols-3 gap-2">
      {OPTIONS.map(({ value, label, Icon }) => (
        <Button
          key={value}
          type="button"
          role="radio"
          aria-checked={mounted && theme === value}
          variant="outline"
          size="md"
          className="aria-checked:border-primary aria-checked:bg-primary aria-checked:text-primary-foreground"
          onClick={() => setTheme(value)}
        >
          <Icon aria-hidden />
          {label}
        </Button>
      ))}
    </div>
  );
}
