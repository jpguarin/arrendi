"use client";

import { FileText, Upload, X } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field";
import { DOCUMENT_TYPES, documentProblem } from "@/lib/api/documents";

type DocumentPickerProps = {
  file: File | null;
  onChange: (file: File | null) => void;
  /** What the button says. By default, it asks for the signed lease. */
  label?: string;
};

/** Picks a document from the camera or the files of the phone. It is optional. */
export function DocumentPicker({
  file,
  onChange,
  label = "Subir contrato firmado (opcional)",
}: DocumentPickerProps) {
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string>();

  function pick(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0];
    // Lets the owner pick the same file again after removing it.
    event.target.value = "";
    if (!picked) return;
    const problem = documentProblem(picked);
    setError(problem);
    onChange(problem ? null : picked);
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={input}
        type="file"
        accept={DOCUMENT_TYPES.join(",")}
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        onChange={pick}
      />
      {file ? (
        <div className="flex items-center gap-3 rounded-xl border border-border bg-card py-2 pr-2 pl-4">
          <FileText aria-hidden className="size-5 shrink-0 text-primary" />
          <span className="min-w-0 flex-1 truncate text-section font-semibold">{file.name}</span>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="text-muted-foreground"
            aria-label={`Quitar ${file.name}`}
            onClick={() => onChange(null)}
          >
            <X aria-hidden />
          </Button>
        </div>
      ) : (
        <Button type="button" variant="dashed" size="md" onClick={() => input.current?.click()}>
          <Upload aria-hidden />
          {label}
        </Button>
      )}
      {error && <FieldError>{error}</FieldError>}
    </div>
  );
}
