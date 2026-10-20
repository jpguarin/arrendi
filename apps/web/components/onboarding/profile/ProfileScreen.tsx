"use client";

import { Check, ListChecks } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { LoadError, Loading } from "@/components/LoadState";
import { errorMessage } from "@/lib/api/errors";
import { useSettings, useSignatureUrl } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { DOCUMENT_TYPE_LABELS } from "@/lib/labels";
import { cn } from "@/lib/utils";

import { DocumentQuestion } from "./DocumentQuestion";
import { PaymentQuestion } from "./PaymentQuestion";
import { ProfileReview } from "./ProfileReview";
import { SendDayQuestion } from "./SendDayQuestion";
import { SignatureQuestion } from "./SignatureQuestion";
import {
  canOpen,
  firstUnanswered,
  PROFILE_STEPS,
  type ProfileStep,
  profileHref,
  type Question,
} from "./steps";

type Settings = components["schemas"]["SettingsResponse"];

const LABELS: Record<ProfileStep, string> = {
  document: "Quién cobra",
  payment: "Cómo te pagan",
  signature: "Tu firma",
  "send-day": "Día de envío",
  review: "Revisar",
};

/** From the desktop up, on the left: every question, what was answered, and a way back. */
function ProfileIndex({ settings, step }: { settings: Settings; step: ProfileStep }) {
  const { data: signature } = useSignatureUrl(settings.has_signature);
  // What each question holds once answered. The send day always has a value, so it only
  // counts as answered once the owner went past it.
  const answers: Record<Question, React.ReactNode> = {
    document:
      settings.document_number &&
      `${settings.name}\n${DOCUMENT_TYPE_LABELS[settings.document_type]} ${settings.document_number}`,
    payment: settings.payment_details,
    signature: signature && (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={signature.url} alt="" className="mt-0.5 h-7 rounded bg-paper px-1.5 py-0.5" />
    ),
    "send-day": step === "review" && `El ${settings.send_day} de cada mes`,
  };

  return (
    <nav
      aria-label="Tus datos"
      className="flex flex-col gap-1 border-r border-border bg-card px-5 py-8 max-lg:hidden"
    >
      <p className="px-3 pb-2.5 font-heading text-section font-extrabold text-muted-foreground">
        Tus datos
      </p>
      {PROFILE_STEPS.map((item, index) => {
        const answer = item === "review" ? null : answers[item];
        const open = canOpen(item, settings);
        return (
          <Link
            key={item}
            href={profileHref(item)}
            aria-current={item === step ? "step" : undefined}
            aria-disabled={!open || undefined}
            tabIndex={open ? undefined : -1}
            className={cn(
              "grid grid-cols-[1.75rem_minmax(0,1fr)] items-start gap-2.5 rounded-lg px-3 py-2.5 hover:bg-muted aria-[current=step]:bg-accent",
              !open && "pointer-events-none opacity-55",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "grid size-7 place-items-center rounded-full text-support font-bold",
                answer ? "bg-positive-tint text-positive-ink" : "bg-muted text-muted-foreground",
              )}
            >
              {item === "review" ? (
                <ListChecks className="size-4" />
              ) : answer ? (
                <Check className="size-4" />
              ) : (
                index + 1
              )}
            </span>
            <span className="flex min-w-0 flex-col">
              <span className="text-section font-semibold">{LABELS[item]}</span>
              {answer && (
                <span className="line-clamp-2 text-support whitespace-pre-line text-muted-foreground">
                  {answer}
                </span>
              )}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}

/**
 * "Tus datos": the question of the route, and, from the desktop up, the index of all of
 * them. A question opens only once the ones before it are answered.
 */
export function ProfileScreen({ step }: { step: ProfileStep }) {
  const router = useRouter();
  const { data: settings, error, refetch } = useSettings();
  const missing = settings ? firstUnanswered(settings) : null;
  const blocked = settings !== undefined && !canOpen(step, settings);

  useEffect(() => {
    if (blocked && missing) router.replace(profileHref(missing));
  }, [blocked, missing, router]);

  if (!settings) {
    return (
      <main className="mx-auto flex w-full max-w-xl flex-1 flex-col px-4 pt-8">
        {error ? (
          <LoadError message={errorMessage(error)} onRetry={refetch} />
        ) : (
          <Loading label="Cargando tus datos" />
        )}
      </main>
    );
  }
  if (blocked) return null;

  return (
    <div className="grid flex-1 lg:grid-cols-[20rem_minmax(0,1fr)]">
      <ProfileIndex settings={settings} step={step} />
      <div className="flex min-w-0 flex-col">
        {step === "document" && <DocumentQuestion settings={settings} />}
        {step === "payment" && <PaymentQuestion settings={settings} />}
        {step === "signature" && <SignatureQuestion settings={settings} />}
        {step === "send-day" && <SendDayQuestion settings={settings} />}
        {step === "review" && <ProfileReview settings={settings} />}
      </div>
    </div>
  );
}
