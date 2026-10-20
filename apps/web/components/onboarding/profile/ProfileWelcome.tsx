"use client";

import { ArrowRight, Clock } from "lucide-react";
import Link from "next/link";

import { LoadError, Loading } from "@/components/LoadState";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/lib/api/errors";
import { useMe, useSettings } from "@/lib/api/queries";

import { SampleBill } from "./SampleBill";
import { firstUnanswered, profileHref } from "./steps";

/** The start of "Tus datos": what is asked, why, and the bill it makes. */
export function ProfileWelcome() {
  const { data: me } = useMe();
  const { data: settings, error, refetch } = useSettings();

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

  // Someone coming back picks up where they left.
  const start = firstUnanswered(settings) ?? "send-day";

  return (
    <main className="mx-auto grid w-full max-w-sheet flex-1 content-center gap-8 px-4 py-8 md:grid-cols-2 md:items-center md:gap-12 md:px-8 md:py-14">
      <div className="flex flex-col gap-4">
        {me && (
          <p className="text-body font-semibold text-foreground-soft">
            Hola, {me.name.split(" ")[0]}
          </p>
        )}
        <h1 className="font-heading text-title-onboarding leading-tight font-extrabold md:text-figure">
          Primero, preséntate con tus arrendatarios
        </h1>
        <p className="text-body text-muted-foreground">
          Cada mes les llega una cuenta de cobro con tu nombre, cómo pagarte y tu firma. Déjala
          lista una vez y Arrendi la envía sola.
        </p>
        <p className="inline-flex items-center gap-1.5 self-start rounded-full bg-positive-tint px-2.5 py-1 text-support font-semibold text-positive-ink">
          <Clock aria-hidden className="size-4" />
          Unos 2 minutos
        </p>
        <Button asChild className="self-start">
          <Link href={profileHref(start)}>
            Empezar
            <ArrowRight aria-hidden />
          </Link>
        </Button>
      </div>
      <SampleBill settings={settings} />
    </main>
  );
}
