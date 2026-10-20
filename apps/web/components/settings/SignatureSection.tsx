"use client";

import { PenLine, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { FormMessage } from "@/components/FormMessage";
import { SignaturePad } from "@/components/settings/SignaturePad";
import { Button } from "@/components/ui/button";
import { SIGNATURE_TYPES, uploadSignature } from "@/lib/api/documents";
import { errorMessage } from "@/lib/api/errors";
import { useDeleteSignature, useRefreshSignature, useSignatureUrl } from "@/lib/api/queries";
import { cn } from "@/lib/utils";

/**
 * The signature that closes every bill: see it, upload it, draw it or take it away.
 * Without `heading`, the screen around it already says what it is for.
 */
export function SignatureSection({
  hasSignature,
  heading = true,
  onSavingChange,
}: {
  hasSignature: boolean;
  heading?: boolean;
  /** Told while a signature goes up, for a screen whose next step needs it. */
  onSavingChange?: (saving: boolean) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [drawing, setDrawing] = useState(false);
  const [saving, setSaving] = useState(false);
  // Set at once, before the screen is drawn again: two taps in a row send one signature.
  const sending = useRef(false);
  const [problem, setProblem] = useState<string>();
  const { data: link } = useSignatureUrl(hasSignature);
  const refresh = useRefreshSignature();
  const remove = useDeleteSignature();

  async function save(file: File) {
    if (sending.current) return;
    sending.current = true;
    setSaving(true);
    onSavingChange?.(true);
    clearProblems();
    const failed = await uploadSignature(file);
    if (!failed) {
      await refresh();
      setDrawing(false);
    }
    setProblem(failed);
    setSaving(false);
    onSavingChange?.(false);
    sending.current = false;
  }

  /** What went wrong before says nothing about what is tried next. */
  function clearProblems() {
    setProblem(undefined);
    remove.reset();
  }

  function pick(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0];
    // Lets the owner pick the same file again.
    event.target.value = "";
    if (picked) save(picked);
  }

  const error = problem ?? (remove.error ? errorMessage(remove.error) : undefined);
  const busy = saving || remove.isPending;

  return (
    <section aria-labelledby="signature" className={cn("flex flex-col gap-3", heading && "pt-4")}>
      <div className={cn("flex flex-col gap-0.5", !heading && "sr-only")}>
        <h2 id="signature" className="text-section font-semibold">
          Firma
        </h2>
        <p className="text-support text-muted-foreground">
          {hasSignature
            ? "Va al final de cada cuenta de cobro que generes, sobre tu nombre y tu documento. Las que ya generaste no cambian."
            : "Súbela o dibújala y saldrá al final de cada cuenta de cobro, sobre tu nombre y tu documento. Sin firma, la cuenta deja una línea para firmar a mano."}
        </p>
      </div>
      {error && <FormMessage tone="error">{error}</FormMessage>}
      <input
        ref={input}
        type="file"
        accept={SIGNATURE_TYPES.join(",")}
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={pick}
      />
      {drawing ? (
        <SignaturePad saving={saving} onCancel={() => setDrawing(false)} onDone={save} />
      ) : (
        <>
          {hasSignature && (
            // On paper in both themes: the ink is dark, as it goes on the PDF.
            <div className="flex h-28 items-center justify-center rounded-xl border border-border bg-paper p-4">
              {link && (
                // A temporary link to a private file: nothing for the image optimizer to keep.
                // eslint-disable-next-line @next/next/no-img-element
                <img src={link.url} alt="Tu firma" className="max-h-full max-w-full" />
              )}
            </div>
          )}
          <div className="grid grid-cols-2 gap-2">
            <Button
              type="button"
              variant="outline"
              size="md"
              disabled={busy}
              onClick={() => input.current?.click()}
            >
              <Upload aria-hidden />
              {saving ? "Subiendo…" : "Subir imagen"}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="md"
              disabled={busy}
              onClick={() => {
                clearProblems();
                setDrawing(true);
              }}
            >
              <PenLine aria-hidden />
              Dibujar firma
            </Button>
          </div>
          {hasSignature && (
            <Button
              type="button"
              variant="ghost"
              size="md"
              className="text-muted-foreground"
              disabled={busy}
              onClick={() => {
                clearProblems();
                remove.mutate({});
              }}
            >
              <Trash2 aria-hidden />
              {remove.isPending ? "Quitando…" : "Quitar firma"}
            </Button>
          )}
        </>
      )}
    </section>
  );
}
