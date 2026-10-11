import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";

type TextareaFieldProps = React.ComponentProps<typeof Textarea> & {
  id: string;
  label: string;
  description?: string;
  error?: string;
};

/** Like FormField, for a text of several lines. */
export function TextareaField({
  id,
  label,
  description,
  error,
  ...textareaProps
}: TextareaFieldProps) {
  const descriptionId = description ? `${id}-description` : undefined;
  const errorId = error ? `${id}-error` : undefined;

  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Textarea
        id={id}
        aria-invalid={Boolean(error)}
        aria-describedby={[descriptionId, errorId].filter(Boolean).join(" ") || undefined}
        {...textareaProps}
      />
      {description && !error && (
        <FieldDescription id={descriptionId}>{description}</FieldDescription>
      )}
      {error && <FieldError id={errorId}>{error}</FieldError>}
    </Field>
  );
}
