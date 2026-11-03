import { HomeScreen } from "@/components/HomeScreen";
import { monthParam } from "@/lib/bills";

export default async function HomePage({ searchParams }: PageProps<"/">) {
  const { month } = await searchParams;
  return <HomeScreen month={monthParam(month)} />;
}
