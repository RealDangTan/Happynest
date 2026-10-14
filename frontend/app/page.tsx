import { redirect } from "next/navigation"

// FE-12 (2026-09-15): root goes to the first LISTEN stage — the Importer.
export default function Page() {
  redirect("/importer")
}
