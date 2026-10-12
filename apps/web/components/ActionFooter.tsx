/**
 * The main action of a screen, fixed at the bottom where the thumb reaches it.
 *
 * It sticks to the bottom of the screen while the content scrolls behind it. On a phone
 * it leaves room under the button, so it keeps clear of the edge and of the home
 * indicator.
 */
export function ActionFooter({ children }: { children: React.ReactNode }) {
  return (
    <footer className="sticky bottom-0 mt-auto flex flex-col gap-2 border-t border-border bg-card px-5 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] max-md:pb-[max(1.75rem,calc(env(safe-area-inset-bottom)+0.75rem))]">
      {children}
    </footer>
  );
}
