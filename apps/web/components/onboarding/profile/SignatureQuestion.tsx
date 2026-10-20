"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { SignatureSection } from "@/components/settings/SignatureSection";
import type { components } from "@/lib/api/schema";

import { QuestionFrame } from "./QuestionFrame";
import { nextStep, profileHref } from "./steps";

type Settings = components["schemas"]["SettingsResponse"];

/** The signature, as in Ajustes: it is saved the moment it is drawn or uploaded. */
export function SignatureQuestion({ settings }: { settings: Settings }) {
  const router = useRouter();
  const [missing, setMissing] = useState(false);
  // Until the signature is up, the answer is not there yet: going on waits for it.
  const [saving, setSaving] = useState(false);

  return (
    <QuestionFrame
      question="signature"
      title="Firma una sola vez"
      description="Con el dedo, el mouse o una foto. Sale al pie de todas tus cuentas, sobre tu nombre."
      saving={saving}
      error={
        missing && !settings.has_signature
          ? "Dibuja tu firma o sube una foto de ella para seguir."
          : undefined
      }
      onSubmit={(event) => {
        event.preventDefault();
        if (settings.has_signature) router.push(profileHref(nextStep("signature")));
        else setMissing(true);
      }}
    >
      <SignatureSection
        hasSignature={settings.has_signature}
        heading={false}
        onSavingChange={setSaving}
      />
    </QuestionFrame>
  );
}
