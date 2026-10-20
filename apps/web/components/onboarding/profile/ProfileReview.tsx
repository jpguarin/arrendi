"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ActionFooter } from "@/components/ActionFooter";
import { FormMessage } from "@/components/FormMessage";
import { Button } from "@/components/ui/button";
import { useMe, useSignatureUrl } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { DOCUMENT_TYPE_LABELS } from "@/lib/labels";

import { SampleBill } from "./SampleBill";
import { profileHref, type Question } from "./steps";

type Settings = components["schemas"]["SettingsResponse"];

/** Every answer, with the bill they make, before going on to the property. */
export function ProfileReview({ settings }: { settings: Settings }) {
  const router = useRouter();
  const { refetch } = useMe();
  const { data: signature } = useSignatureUrl(settings.has_signature);
  const [leaving, setLeaving] = useState(false);
  const [problem, setProblem] = useState<string>();

  const answers: { question: Question; label: string; answer: React.ReactNode }[] = [
    {
      question: "document",
      label: "Quién cobra",
      answer: `${settings.name}\n${DOCUMENT_TYPE_LABELS[settings.document_type]} ${settings.document_number ?? ""}`,
    },
    { question: "payment", label: "Cómo te pagan", answer: settings.payment_details },
    {
      question: "signature",
      label: "Tu firma",
      answer: signature && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={signature.url} alt="Tu firma" className="h-10 rounded-md bg-paper px-2 py-1" />
      ),
    },
    { question: "send-day", label: "Día de envío", answer: `El ${settings.send_day} de cada mes` },
  ];

  async function goOn() {
    setLeaving(true);
    setProblem(undefined);
    // The property's sheet asks /me whether the data is complete: it must know it is.
    const { data } = await refetch();
    if (data?.profile_complete) router.push("/onboarding/property");
    else {
      setProblem("Falta algo de tus datos. Revisa las respuestas.");
      setLeaving(false);
    }
  }

  const action = (
    <Button type="button" disabled={leaving} onClick={goOn}>
      {leaving ? "Abriendo…" : "Seguir con mi inmueble"}
    </Button>
  );

  return (
    <>
      <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 pt-6 pb-8 md:px-6 md:pt-14">
        <div className="flex flex-col gap-1.5">
          <div className="h-1.5 rounded-full bg-positive" aria-hidden />
          <p className="text-support text-muted-foreground">Revisa antes de seguir</p>
        </div>
        <div className="flex flex-col gap-2">
          <h1 className="font-heading text-title-onboarding leading-tight font-extrabold">
            ¿Todo bien?
          </h1>
          <p className="text-section text-muted-foreground">
            Así quedan tus cuentas. Toca «Cambiar» en lo que quieras.
          </p>
        </div>
        {problem && <FormMessage tone="error">{problem}</FormMessage>}
        <div className="grid items-start gap-5 md:grid-cols-[minmax(0,1fr)_var(--container-pane)]">
          {/* The answers and, right under them, the action: the bill beside them is taller. */}
          <div className="flex flex-col gap-5">
            <ul className="flex flex-col rounded-xl border border-border bg-card">
              {answers.map(({ question, label, answer }) => (
                <li
                  key={question}
                  className="flex items-center justify-between gap-3 border-t border-border px-4 py-3.5 first:border-t-0"
                >
                  <div className="flex min-w-0 flex-col gap-1">
                    <p className="text-support font-semibold text-muted-foreground">{label}</p>
                    <div className="text-section break-words whitespace-pre-line">{answer}</div>
                  </div>
                  <Button asChild variant="ghost" size="sm">
                    <Link href={profileHref(question)}>Cambiar</Link>
                  </Button>
                </li>
              ))}
            </ul>
            <div className="max-md:hidden">{action}</div>
          </div>
          <SampleBill settings={settings} />
        </div>
      </main>
      <ActionFooter className="md:hidden">{action}</ActionFooter>
    </>
  );
}
