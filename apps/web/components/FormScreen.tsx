import { ActionFooter } from "@/components/ActionFooter";
import { FormMessage } from "@/components/FormMessage";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";

type FormScreenProps = {
  title: string;
  subtitle?: string;
  backHref: string;
  /** The form this screen saves; the button in the footer submits it. */
  formId: string;
  submitLabel: string;
  saving: boolean;
  /** What the API answered when saving failed. */
  error?: string;
  children: React.ReactNode;
};

/** Frame of a screen that edits one thing: back, the form, and "save" at the bottom. */
export function FormScreen({
  title,
  subtitle,
  backHref,
  formId,
  submitLabel,
  saving,
  error,
  children,
}: FormScreenProps) {
  return (
    <>
      <Header title={title} subtitle={subtitle} backHref={backHref} />
      <main className="flex flex-1 flex-col gap-5 px-5 pt-2 pb-8">
        {error && <FormMessage tone="error">{error}</FormMessage>}
        {children}
      </main>
      <ActionFooter>
        <Button type="submit" form={formId} disabled={saving}>
          {saving ? "Guardando…" : submitLabel}
        </Button>
      </ActionFooter>
    </>
  );
}

/** The same frame while the thing to edit loads, or when it could not be loaded. */
export function FormScreenFallback({
  title,
  backHref,
  children,
}: {
  title: string;
  backHref: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <Header title={title} backHref={backHref} />
      <main className="flex flex-1 flex-col gap-5 px-5 pt-2 pb-8">{children}</main>
    </>
  );
}
