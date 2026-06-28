import { redirect } from "next/navigation";

type SP = Record<string, string | string[] | undefined>;

export default async function VedicastroPage({
  searchParams,
}: {
  searchParams: Promise<SP>;
}) {
  const sp = await searchParams;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) {
    if (typeof v === "string") qs.set(k, v);
    else if (Array.isArray(v)) v.forEach((val) => qs.append(k, val));
  }
  redirect(qs.toString() ? `/chart?${qs.toString()}` : "/chart");
}
