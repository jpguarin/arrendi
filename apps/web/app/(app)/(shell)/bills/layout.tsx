import { Suspense } from "react";

import { BillsScreen } from "@/components/bills/BillsScreen";
import { ListDetail } from "@/components/shell/ListDetail";

// The list of bills stays in view while one of them, or a payment, is open next to it.
export default function BillsLayout({ children }: LayoutProps<"/bills">) {
  return (
    <ListDetail
      root="/bills"
      list={
        // The list reads its unit filter from the address.
        <Suspense>
          <BillsScreen />
        </Suspense>
      }
    >
      {children}
    </ListDetail>
  );
}
