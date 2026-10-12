import { Brand } from "@/components/Brand";

type AuthScreenProps = {
  title: string;
  description?: string;
  children: React.ReactNode;
};

/** Frame of the screens for people who are not signed in yet. */
export function AuthScreen({ title, description, children }: AuthScreenProps) {
  return (
    <main className="flex flex-1 flex-col gap-6 px-5 py-10">
      <Brand />
      <div className="flex flex-col gap-1">
        <h1 className="text-title font-bold">{title}</h1>
        {description && <p className="text-support text-muted-foreground">{description}</p>}
      </div>
      {children}
    </main>
  );
}
