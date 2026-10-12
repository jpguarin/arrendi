import { PropertiesScreen } from "@/components/properties/PropertiesScreen";
import { ListDetail } from "@/components/shell/ListDetail";

// The properties stay in view while a lease, or a form of theirs, is open next to them.
export default function PropertiesLayout({ children }: { children: React.ReactNode }) {
  return (
    <ListDetail root="/properties" list={<PropertiesScreen />}>
      {children}
    </ListDetail>
  );
}
