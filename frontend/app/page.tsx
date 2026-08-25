import { redirect } from "next/navigation";

// OQ-3 (decisions 2026-08-26): root luôn về dashboard.
export default function Page() {
  redirect("/dashboard");
}
