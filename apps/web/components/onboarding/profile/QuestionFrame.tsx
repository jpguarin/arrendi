import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { ActionFooter } from "@/components/ActionFooter";
import { FormMessage } from "@/components/FormMessage";
import { Button } from "@/components/ui/button";

import { type Question, profileHref, QUESTIONS } from "./steps";

type QuestionFrameProps = {
  question: Question;
  title: string;
  description: string;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  saving: boolean;
  error?: string;
  children: React.ReactNode;
};

/**
 * One question of "Tus datos": its progress, the way back, the question in large type and
 * the action. Enter continues, as a form does. On a phone the action is fixed at the
 * bottom; from the tablet up it sits under the question.
 */
export function QuestionFrame({
  question,
  title,
  description,
  onSubmit,
  saving,
  error,
  children,
}: QuestionFrameProps) {
  const position = QUESTIONS.indexOf(question);
  const formId = `question-${question}`;
  const label = saving ? "Guardando…" : "Continuar";

  return (
    <>
      <main className="mx-auto flex w-full max-w-xl flex-col gap-6 px-4 pt-6 pb-8 md:px-6 md:pt-14">
        <div className="flex flex-col gap-1.5">
          <div
            role="progressbar"
            aria-label="Avance de tus datos"
            aria-valuemin={0}
            aria-valuemax={QUESTIONS.length}
            aria-valuenow={position}
            className="h-1.5 overflow-hidden rounded-full bg-muted"
          >
            <div
              className="h-full rounded-full bg-positive transition-[width]"
              style={{ width: `${(position / QUESTIONS.length) * 100}%` }}
            />
          </div>
          <p className="text-support text-muted-foreground">
            Pregunta {position + 1} de {QUESTIONS.length}
          </p>
        </div>
        {position > 0 && (
          <Link
            href={profileHref(QUESTIONS[position - 1])}
            className="-my-2 inline-flex min-h-11 items-center gap-1 self-start font-semibold text-muted-foreground underline-offset-4 hover:underline"
          >
            <ArrowLeft aria-hidden className="size-4.5" />
            Anterior
          </Link>
        )}
        <div className="flex flex-col gap-2">
          <h1 className="font-heading text-title-onboarding leading-tight font-extrabold">
            {title}
          </h1>
          <p className="text-section text-muted-foreground">{description}</p>
        </div>
        {error && <FormMessage tone="error">{error}</FormMessage>}
        <form id={formId} onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
          {children}
        </form>
        <div className="flex items-center gap-3.5 max-md:hidden">
          <Button type="submit" form={formId} disabled={saving}>
            {label}
          </Button>
          <span className="text-support text-muted-foreground">
            o pulsa{" "}
            <kbd className="rounded-md border border-border bg-card px-1.5 font-sans font-semibold">
              Enter
            </kbd>
          </span>
        </div>
      </main>
      <ActionFooter className="md:hidden">
        <Button type="submit" form={formId} disabled={saving}>
          {label}
        </Button>
      </ActionFooter>
    </>
  );
}
