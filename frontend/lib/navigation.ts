import {
  FileText,
  Inbox,
  LayoutGrid,
  Upload,
  Users,
  Waypoints,
  type LucideIcon,
} from "lucide-react";

/** The six-screen journey, grouped by stage — single source for panel, breadcrumb
 * and command palette (FE-13). */
export const STAGES: {
  group: string;
  items: { href: string; label: string; icon: LucideIcon }[];
}[] = [
  {
    group: "LISTEN",
    items: [
      { href: "/importer", label: "Importer", icon: Upload },
      { href: "/vault", label: "Feedback Vault", icon: Inbox },
    ],
  },
  {
    group: "UNDERSTAND",
    items: [
      { href: "/data-graph", label: "Data Graph", icon: Waypoints },
      { href: "/reports", label: "Reports", icon: FileText },
    ],
  },
  {
    group: "ACT",
    items: [
      { href: "/matrix", label: "Priority Matrix", icon: LayoutGrid },
      { href: "/stakeholders", label: "Stakeholders", icon: Users },
    ],
  },
];

export function findStage(pathname: string):
  | { group: string; label: string; href: string }
  | { group: string; label: string; href: null } {
  for (const group of STAGES) {
    for (const item of group.items) {
      if (item.href === pathname) {
        return { group: group.group, label: item.label, href: item.href };
      }
    }
  }
  // Chat is a panel tab in the dock, not a route — no stage entry.
  return { group: "", label: "", href: null };
}
