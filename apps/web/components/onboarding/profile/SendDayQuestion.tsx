"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { SelectField } from "@/components/SelectField";
import { FieldDescription, FieldLegend, FieldSet } from "@/components/ui/field";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { errorMessage } from "@/lib/api/errors";
import { useUpdateSettings } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";

import { QuestionFrame } from "./QuestionFrame";
import { nextStep, profileHref } from "./steps";

type Settings = components["schemas"]["SettingsResponse"];

// The days most owners pick, a tap away; any other one is in the list.
const QUICK_DAYS = ["1", "5", "10", "15", "25"];
const SUGGESTED_DAY = "1";
const OTHER_DAYS = Array.from({ length: 28 }, (_, index) => String(index + 1))
  .filter((day) => !QUICK_DAYS.includes(day))
  .map((day) => ({ value: day, label: `Día ${day}` }));

/** The day of the month the bills go out. It always has one; here the owner picks it. */
export function SendDayQuestion({ settings }: { settings: Settings }) {
  const router = useRouter();
  const update = useUpdateSettings();
  const [day, setDay] = useState(String(settings.send_day));

  return (
    <QuestionFrame
      question="send-day"
      title="¿Qué día salen tus cuentas?"
      description="Ese día Arrendi genera las cuentas del mes y las envía solas."
      saving={update.isPending}
      error={update.error ? errorMessage(update.error) : undefined}
      onSubmit={(event) => {
        event.preventDefault();
        update.mutate(
          { body: { send_day: Number(day) } },
          { onSuccess: () => router.push(profileHref(nextStep("send-day"))) },
        );
      }}
    >
      <FieldSet>
        <FieldLegend variant="label">Día de envío</FieldLegend>
        <ToggleGroup
          type="single"
          className="flex flex-wrap"
          value={QUICK_DAYS.includes(day) ? day : ""}
          onValueChange={(value) => value && setDay(value)}
        >
          {QUICK_DAYS.map((quick) => (
            <ToggleGroupItem key={quick} value={quick} className="h-11 rounded-full px-4">
              Día {quick}
              {quick === SUGGESTED_DAY && (
                // On the picked day it takes the button's colors, which keep their contrast.
                <span className="rounded-full bg-positive-tint px-1.5 text-badge text-positive-ink in-data-[state=on]:bg-primary-foreground/15 in-data-[state=on]:text-current">
                  Sugerido
                </span>
              )}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </FieldSet>
      <SelectField
        id="other_day"
        label="Otro día"
        placeholder="Elige otro día"
        options={OTHER_DAYS}
        // Empty, not undefined: the select stays controlled while a quick day is picked.
        value={QUICK_DAYS.includes(day) ? "" : day}
        onChange={setDay}
      />
      <FieldDescription>
        El día {day} de cada mes se generan las cuentas y se envían a los contratos con envío
        automático.
      </FieldDescription>
    </QuestionFrame>
  );
}
