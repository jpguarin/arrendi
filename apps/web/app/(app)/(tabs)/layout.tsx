import { BottomNav } from "@/components/BottomNav";

// The top-level screens, the ones the bottom bar moves between.
export default function TabsLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      {children}
      <BottomNav />
    </>
  );
}
