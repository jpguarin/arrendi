/**
 * One phone-sized column, centered: the screens outside the shell (sign-in, onboarding,
 * offline), which are a single task with nothing next to it.
 */
export function Column({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto flex min-h-dvh w-full max-w-app flex-col">{children}</div>;
}
