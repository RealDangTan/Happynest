import type { Dictionary } from "@/lib/i18n";
import {
  FileText,
  Inbox,
  LayoutGrid,
  LifeBuoy,
  ListTree,
  Mail,
  Settings,
  SlidersHorizontal,
  Upload,
  UserRound,
  Users,
  Waypoints,
  type LucideIcon,
} from "lucide-react";

/** The six-screen journey, grouped by stage — single source for panel, breadcrumb
 * and command palette (FE-13). Chữ hiển thị sống trong lib/i18n.ts; module này
 * chỉ giữ key, href và icon để label đổi theo ngôn ngữ ở mọi nơi tiêu dùng. */
export type NavGroupKey = keyof Dictionary["nav"]["groups"];
export type NavItemKey = keyof Dictionary["nav"]["items"];
export type UtilityKey = keyof Dictionary["nav"]["utility"];

export const STAGES: {
  group: NavGroupKey;
  items: { href: string; key: NavItemKey; icon: LucideIcon }[];
}[] = [
  {
    group: "listen",
    items: [
      { href: "/importer", key: "importer", icon: Upload },
      { href: "/taxonomy", key: "taxonomy", icon: ListTree },
      { href: "/vault", key: "vault", icon: Inbox },
    ],
  },
  {
    group: "understand",
    items: [
      { href: "/data-graph", key: "dataGraph", icon: Waypoints },
      { href: "/reports", key: "reports", icon: FileText },
    ],
  },
  {
    group: "act",
    items: [
      { href: "/matrix", key: "matrix", icon: LayoutGrid },
      { href: "/stakeholders", key: "stakeholders", icon: Users },
    ],
  },
];

export function findStage(
  pathname: string,
):
  | { group: NavGroupKey; key: NavItemKey; href: string }
  | { group: null; key: null; href: null } {
  for (const stage of STAGES) {
    for (const item of stage.items) {
      if (item.href === pathname) {
        return { group: stage.group, key: item.key, href: item.href };
      }
    }
  }
  // Chat is a panel tab in the dock, not a route — no stage entry.
  return { group: null, key: null, href: null };
}

/** Màn ngoại lai ngoài six-screen journey — vào từ profile menu, panel footer
 * và command palette; không có stage entry nên breadcrumb không hiển thị. */
export const UTILITY_SCREENS: {
  href: string;
  key: UtilityKey;
  icon: LucideIcon;
}[] = [
  { href: "/settings", key: "settings", icon: Settings },
  { href: "/profile", key: "profile", icon: UserRound },
  { href: "/settings/workspace", key: "workspace", icon: SlidersHorizontal },
  { href: "/help", key: "help", icon: LifeBuoy },
  { href: "/contact", key: "contact", icon: Mail },
];
