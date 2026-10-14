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
      { href: "/taxonomy", label: "Taxonomy", icon: ListTree },
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

/** Màn ngoại lai ngoài six-screen journey — vào từ profile menu, panel footer
 * và command palette; không có stage entry nên breadcrumb không hiển thị. */
export const UTILITY_SCREENS: {
  href: string;
  label: string;
  description: string;
  icon: LucideIcon;
}[] = [
  {
    href: "/settings",
    label: "Settings",
    description: "Giao diện và ngôn ngữ ứng dụng",
    icon: Settings,
  },
  {
    href: "/profile",
    label: "Profile",
    description: "Tài khoản và phiên đăng nhập",
    icon: UserRound,
  },
  {
    href: "/settings/workspace",
    label: "Workspace settings",
    description: "Đổi tên product, chuyển hoặc xoá workspace",
    icon: SlidersHorizontal,
  },
  {
    href: "/help",
    label: "Help",
    description: "Hướng dẫn ba chặng và câu hỏi thường gặp",
    icon: LifeBuoy,
  },
  {
    href: "/contact",
    label: "Contact",
    description: "Gửi phản hồi cho nhóm phát triển",
    icon: Mail,
  },
];
