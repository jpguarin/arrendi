import { AppShell } from "@/components/shell/AppShell";

// The signed-in screens that share the navigation.
export default function ShellLayout({ children }: LayoutProps<"/">) {
  return <AppShell>{children}</AppShell>;
}
