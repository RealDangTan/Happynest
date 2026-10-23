import { useSyncExternalStore } from "react";

/**
 * Lớp i18n của app — không thư viện ngoài: một store nhỏ dùng
 * `useSyncExternalStore` để mọi consumer (profile popover, /settings, màn auth,
 * panel điều hướng…) cùng nghe một nguồn; đổi ngôn ngữ ở đâu cũng re-render
 * ngay ở chỗ kia, cả trong cùng một session.
 *
 * Nguồn sự thật hiển thị: `vi` — `en` được khai báo `Dictionary` nên thiếu/khá
 * key nào là gãy ngay lúc build. Không dùng LLM/dịch máy runtime cho chữ UI
 * (quyết định đã ghi trong docs/decisions.md — nhãn song ngữ đặt tại nguồn).
 */

export type AppLang = "vi" | "en";

const LANG_STORAGE_KEY = "happynest.lang";

const vi = {
  nav: {
    groups: { listen: "LẮNG NGHE", understand: "HIỂU", act: "HÀNH ĐỘNG" },
    items: {
      importer: "Nhập dữ liệu",
      taxonomy: "Taxonomy",
      vault: "Kho phản hồi",
      dataGraph: "Đồ thị dữ liệu",
      reports: "Báo cáo",
      matrix: "Ma trận ưu tiên",
      stakeholders: "Các bên liên quan",
    },
    utility: {
      settings: {
        label: "Cài đặt",
        description: "Giao diện và ngôn ngữ ứng dụng",
      },
      profile: {
        label: "Hồ sơ",
        description: "Tài khoản và phiên đăng nhập",
      },
      workspace: {
        label: "Cài đặt workspace",
        description: "Đổi tên product, chuyển hoặc xoá workspace",
      },
      help: {
        label: "Trợ giúp",
        description: "Hướng dẫn ba chặng và câu hỏi thường gặp",
      },
      contact: {
        label: "Liên hệ",
        description: "Gửi phản hồi cho nhóm phát triển",
      },
    },
  },
  panel: {
    home: "Trang chủ",
    chat: "Chat",
    collapse: "Thu gọn panel",
    expand: "Mở rộng panel",
    sections: "Mục điều hướng",
    helpContact: "Trợ giúp & liên hệ",
  },
  navbar: {
    search: "Tìm kiếm…",
    searchAria: "Tìm kiếm (Ctrl K)",
    openNavigation: "Mở điều hướng",
    chooseProduct: "Chọn một product",
    createProduct: "Tạo product",
    renameProduct: "Đổi tên product",
    deleteProduct: "Xoá product…",
    createTitle: "Tạo product",
    createDescription: "Product mới bắt đầu trống — Importer là màn đầu tiên.",
    nameLabel: "Tên",
    namePlaceholder: "Demo AI",
    descriptionLabel: "Mô tả",
    descriptionPlaceholder: "Product này làm gì (không bắt buộc)",
    cancel: "Huỷ",
    renameTitle: "Đổi tên product",
    renameDescription: "Tên mới áp dụng cho toàn bộ workspace này.",
    productNameLabel: "Tên product",
    saveChanges: "Lưu thay đổi",
    deleteTitle: (name: string) => `Xoá “${name}”?`,
    deleteDescription:
      "Toàn bộ feedback, import, insight và schema của product này sẽ bị xoá vĩnh viễn khỏi database (không thể hoàn tác). Gõ đúng tên product để xác nhận.",
    deleteConfirmLabel: (name: string) => `Gõ “${name}” để xác nhận`,
    deletePermanently: "Xoá vĩnh viễn",
    toastUpdated: "Đã cập nhật product.",
    toastRenameFailed: "Không đổi được tên product.",
    toastDeleted: (total: number) =>
      `Đã xoá product và ${total} bản ghi liên quan khỏi database.`,
    toastDeleteFailed: "Không xoá được product.",
    toastCreateFailed: "Không tạo được product.",
  },
  palette: {
    placeholder: "Tìm phản hồi, báo cáo, màn hình…",
    empty: (query: string) => `Không có gì khớp “${query}”.`,
    groupActions: "Hành động",
    groupScreens: "Màn hình",
    groupApp: "Ứng dụng",
    groupReports: "Báo cáo",
    groupFeedback: "Phản hồi",
    importCsv: "Nhập file CSV",
    startInvestigation: "Bắt đầu một cuộc điều tra",
  },
  charts: {
    severityDistribution: "Phân bố mức độ",
    sentimentDistribution: "Phân bố cảm xúc",
  },
  profile: {
    workspace: "Workspace",
    workspaceSettings: "Cài đặt workspace",
    profile: "Hồ sơ",
    settings: "Cài đặt",
    language: "Ngôn ngữ",
    theme: "Chủ đề",
    signOut: "Đăng xuất",
    light: "Sáng",
    dark: "Tối",
  },
  settings: {
    title: "Cài đặt",
    description:
      "Tuỳ chỉnh ứng dụng theo tài khoản — lưu trên trình duyệt này, áp dụng cho mọi workspace.",
    appearanceTitle: "Giao diện",
    appearanceDescription: "Chủ đề màu áp dụng ngay lập tức.",
    theme: "Chủ đề",
    light: "Sáng",
    dark: "Tối",
    language: "Ngôn ngữ",
    privacyTitle: "Dữ liệu & riêng tư",
    privacyDescription:
      "Ranh giới PII là bất biến của pipeline — không có công tắc để tắt.",
    privacyBodyBefore:
      "Mọi feedback đi qua bộ PII sanitizer (email, số điện thoại, CCCD… thay bằng placeholder ",
    privacyBodyAfter:
      ") trước khi vào prompt, log hay trace của agent. Nội dung thô chỉ nằm trong database, không bao giờ rời ranh giới sanitize.",
  },
  auth: {
    signIn: "Đăng nhập",
    signUp: "Đăng ký",
    loginTitle: "Đăng nhập để tiếp tục",
    registerTitle: "Tạo tài khoản mới",
    google: "Đăng nhập với Google",
    comingSoon: "Sắp có",
    orEmail: "hoặc dùng email",
    email: "Email",
    password: "Mật khẩu",
    confirmPassword: "Xác nhận mật khẩu",
    passwordHint: "Tối thiểu 8 ký tự.",
    noAccount: "Chưa có tài khoản?",
    haveAccount: "Đã có tài khoản?",
    invalidDetails: "Thông tin chưa hợp lệ",
    passwordTooShort: "Mật khẩu cần ít nhất 8 ký tự.",
    passwordMismatch: "Mật khẩu xác nhận chưa khớp.",
  },
  help: {
    title: "Trợ giúp",
    description:
      "Happynest chạy theo ba chặng cố định — nắm ba chặng là nắm toàn bộ app.",
    stageDescriptions: {
      listen:
        "Thu nhận phản hồi thô và chuẩn hoá thành dữ liệu sạch: import CSV, kho feedback và bộ taxonomy.",
      understand:
        "Agent phân cụm, phát hiện vấn đề và đề xuất insight kèm bằng chứng — mọi insight chờ bạn duyệt.",
      act: "Ưu tiên hoá thành ma trận và gói thành bản tin hành động cho từng phòng ban.",
    },
    faqTitle: "Câu hỏi thường gặp",
    faqDescription: "Bốn điều người mới hay hỏi nhất về dữ liệu và tài khoản.",
    faqs: [
      {
        q: "Nội dung thô của feedback có bị gửi đi đâu không?",
        a: "Không. Mọi feedback đi qua bộ PII sanitizer trước khi vào pipeline: email, số điện thoại, CCCD… được thay bằng placeholder <TYPE>. Nội dung đã sanitize mới là thứ agent thấy trong prompt, log và trace; nội dung thô chỉ nằm trong database.",
      },
      {
        q: "Vì sao chạy analysis xong mà report chưa có insight?",
        a: "Mọi insight đều chờ human review (HITL). Insight ở trạng thái pending phải được bạn duyệt mới tính vào report — nhất là các ca severity critical, có vấn đề an toàn, dính PII hoặc độ tin cậy dưới 0.60.",
      },
      {
        q: "Tài khoản mới có dùng được workspace hiện có không?",
        a: "Không. Mỗi account có workspace riêng: tài khoản mới bắt đầu với workspace trống và không bao giờ thấy dữ liệu của account khác. Các thao tác xoá vẫn cần xác nhận.",
      },
      {
        q: "Dữ liệu của tôi lưu ở đâu?",
        a: "Trong PostgreSQL (Supabase) kèm vector embedding 1536 chiều cho tìm kiếm ngữ nghĩa. Xoá một workspace là xoá cascade toàn bộ feedback, import, insight và taxonomy của nó trong một transaction.",
      },
    ],
    shortcutsTitle: "Phím tắt",
    shortcutSearch: "Tìm kiếm toàn cục",
    shortcutClose: "Đóng dialog / palette",
    stillWondering: "Vẫn còn thắc mắc?",
    stillWonderingDescription:
      "Gửi thẳng cho nhóm phát triển — câu hỏi của bạn giúp app tốt lên.",
    openContactForm: "Mở form liên hệ",
  },
  table: {
    searchPlaceholder: "Tìm trong bảng…",
    columns: "Cột hiển thị",
    columnsLabel: "Chọn cột hiển thị",
    resetColumns: "Mặc định",
    filter: "Bộ lọc",
    filterOptions: (name: string) => `Lọc theo ${name}`,
    resetFilters: "Xoá bộ lọc",
    filtersActive: (count: number) => `${count} bộ lọc đang bật`,
    noResults: "Không có dòng nào khớp",
    noResultsHint: "Thử bỏ bớt từ khoá hoặc bộ lọc.",
    clearAll: "Xoá tất cả",
    searchNoResults: "Không tìm thấy.",
    rowsPerPage: "Số dòng/trang",
    pageOf: (page: number, total: number) => `Trang ${page} / ${total}`,
    rangeOf: (from: number, to: number, total: number) =>
      `${from}–${to} trên ${total}`,
    goToFirstPage: "Trang đầu",
    goToPreviousPage: "Trang trước",
    goToNextPage: "Trang sau",
    goToLastPage: "Trang cuối",
    selectAll: "Chọn tất cả dòng trong trang",
    selectRow: "Chọn dòng",
    sortBy: (name: string) => `Sắp xếp theo ${name}`,
    sortAsc: "Tăng dần",
    sortDesc: "Giảm dần",
    sortClear: "Bỏ sắp xếp",
  },
};

// Không `as const` — giá trị tự widening thành `string` (function giữ nguyên
// chữ ký) để `en` chỉ cần đúng CẤU TRÚC, không cần đúng literal VI.
export type Dictionary = typeof vi;

const en: Dictionary = {
  nav: {
    groups: { listen: "LISTEN", understand: "UNDERSTAND", act: "ACT" },
    items: {
      importer: "Importer",
      taxonomy: "Taxonomy",
      vault: "Feedback Vault",
      dataGraph: "Data Graph",
      reports: "Reports",
      matrix: "Priority Matrix",
      stakeholders: "Stakeholders",
    },
    utility: {
      settings: {
        label: "Settings",
        description: "Appearance and app language",
      },
      profile: {
        label: "Profile",
        description: "Account and sessions",
      },
      workspace: {
        label: "Workspace settings",
        description: "Rename the product, switch or delete a workspace",
      },
      help: {
        label: "Help",
        description: "Guided journey and frequently asked questions",
      },
      contact: {
        label: "Contact",
        description: "Send feedback to the team",
      },
    },
  },
  panel: {
    home: "Home",
    chat: "Chat",
    collapse: "Collapse panel",
    expand: "Expand panel",
    sections: "Panel sections",
    helpContact: "Help & contact",
  },
  navbar: {
    search: "Search…",
    searchAria: "Search (Ctrl K)",
    openNavigation: "Open navigation",
    chooseProduct: "Choose a product",
    createProduct: "Create product",
    renameProduct: "Rename product",
    deleteProduct: "Delete product…",
    createTitle: "Create product",
    createDescription:
      "A new product starts empty — the Importer is the first screen.",
    nameLabel: "Name",
    namePlaceholder: "Demo AI",
    descriptionLabel: "Description",
    descriptionPlaceholder: "What this product does (optional)",
    cancel: "Cancel",
    renameTitle: "Rename product",
    renameDescription: "The new name applies across this entire workspace.",
    productNameLabel: "Product name",
    saveChanges: "Save changes",
    deleteTitle: (name) => `Delete “${name}”?`,
    deleteDescription:
      "Every feedback, import, insight and schema of this product will be permanently deleted from the database (cannot be undone). Type the product name exactly to confirm.",
    deleteConfirmLabel: (name) => `Type “${name}” to confirm`,
    deletePermanently: "Delete permanently",
    toastUpdated: "Product updated.",
    toastRenameFailed: "Could not rename the product.",
    toastDeleted: (total) =>
      `Product deleted, ${total} linked records removed from the database.`,
    toastDeleteFailed: "Could not delete the product.",
    toastCreateFailed: "Could not create the product.",
  },
  palette: {
    placeholder: "Search feedback, reports, screens…",
    empty: (query) => `Nothing matches “${query}”.`,
    groupActions: "Actions",
    groupScreens: "Screens",
    groupApp: "App",
    groupReports: "Reports",
    groupFeedback: "Feedback",
    importCsv: "Import a CSV file",
    startInvestigation: "Start an investigation",
  },
  charts: {
    severityDistribution: "Severity distribution",
    sentimentDistribution: "Sentiment distribution",
  },
  profile: {
    workspace: "Workspace",
    workspaceSettings: "Workspace settings",
    profile: "Profile",
    settings: "Settings",
    language: "Language",
    theme: "Theme",
    signOut: "Sign out",
    light: "Light",
    dark: "Dark",
  },
  settings: {
    title: "Settings",
    description:
      "Personalize the app for your account — saved in this browser, applied across every workspace.",
    appearanceTitle: "Appearance",
    appearanceDescription: "Color theme applied instantly.",
    theme: "Theme",
    light: "Light",
    dark: "Dark",
    language: "Language",
    privacyTitle: "Data & privacy",
    privacyDescription:
      "The PII boundary is a pipeline invariant — there is no switch to turn it off.",
    privacyBodyBefore:
      "Every piece of feedback passes through the PII sanitizer (email, phone numbers, national IDs… replaced with the ",
    privacyBodyAfter:
      " placeholder) before entering prompts, logs or agent traces. Raw content stays in the database and never crosses the sanitize boundary.",
  },
  auth: {
    signIn: "Sign in",
    signUp: "Create account",
    loginTitle: "Sign in to continue",
    registerTitle: "Create a new account",
    google: "Sign in with Google",
    comingSoon: "Coming soon",
    orEmail: "or continue with email",
    email: "Email",
    password: "Password",
    confirmPassword: "Confirm password",
    passwordHint: "At least 8 characters.",
    noAccount: "No account yet?",
    haveAccount: "Already have an account?",
    invalidDetails: "Invalid details",
    passwordTooShort: "Password needs at least 8 characters.",
    passwordMismatch: "Passwords don't match.",
  },
  help: {
    title: "Help",
    description:
      "Happynest runs on three fixed stages — know the stages and you know the whole app.",
    stageDescriptions: {
      listen:
        "Collect raw feedback and normalize it into clean data: CSV import, the feedback vault and the taxonomy.",
      understand:
        "The agent clusters, detects problems and proposes evidence-backed insights — every insight waits for your approval.",
      act: "Prioritize into a matrix and package into an action digest per department.",
    },
    faqTitle: "Frequently asked questions",
    faqDescription: "The four things newcomers ask most about data and accounts.",
    faqs: [
      {
        q: "Does the raw feedback content get sent anywhere?",
        a: "No. Every piece of feedback passes through the PII sanitizer before entering the pipeline: emails, phone numbers, national IDs… are replaced with <TYPE> placeholders. Sanitized content is what the agent sees in prompts, logs and traces; raw content stays in the database.",
      },
      {
        q: "Why does a finished analysis run have no insights in the report yet?",
        a: "Every insight waits for human review (HITL). Pending insights only count toward the report once you approve them — especially critical-severity cases, safety issues, PII hits, or confidence below 0.60.",
      },
      {
        q: "Can a new account use an existing workspace?",
        a: "No. Each account has its own workspace: a new account starts empty and never sees another account's data. Destructive actions still require confirmation.",
      },
      {
        q: "Where is my data stored?",
        a: "In PostgreSQL (Supabase) with 1536-dimension vector embeddings for semantic search. Deleting a workspace cascades all of its feedback, imports, insights and taxonomy in a single transaction.",
      },
    ],
    shortcutsTitle: "Keyboard shortcuts",
    shortcutSearch: "Global search",
    shortcutClose: "Close dialog / palette",
    stillWondering: "Still wondering?",
    stillWonderingDescription:
      "Send it straight to the team — your questions make the app better.",
    openContactForm: "Open the contact form",
  },
  table: {
    searchPlaceholder: "Search table…",
    columns: "Columns",
    columnsLabel: "Toggle visible columns",
    resetColumns: "Reset",
    filter: "Filter",
    filterOptions: (name: string) => `Filter by ${name}`,
    resetFilters: "Reset filters",
    filtersActive: (count: number) => `${count} filters active`,
    noResults: "No matching rows",
    noResultsHint: "Try loosening the search or filters.",
    clearAll: "Clear all",
    searchNoResults: "No results found.",
    rowsPerPage: "Rows per page",
    pageOf: (page: number, total: number) => `Page ${page} of ${total}`,
    rangeOf: (from: number, to: number, total: number) =>
      `${from}–${to} of ${total}`,
    goToFirstPage: "First page",
    goToPreviousPage: "Previous page",
    goToNextPage: "Next page",
    goToLastPage: "Last page",
    selectAll: "Select all rows on this page",
    selectRow: "Select row",
    sortBy: (name: string) => `Sort by ${name}`,
    sortAsc: "Ascending",
    sortDesc: "Descending",
    sortClear: "Clear sort",
  },
};

const DICTIONARIES: Record<AppLang, Dictionary> = { vi, en };

// ---- Store ------------------------------------------------------------------

let currentLang: AppLang =
  typeof window === "undefined" || localStorage.getItem(LANG_STORAGE_KEY) !== "en"
    ? "vi"
    : "en";

const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): AppLang {
  return currentLang;
}

// SSR + lần render hydrate luôn là "vi"; sau hydrate React đối chiếu
// getSnapshot (đã đọc localStorage) và render lại nếu khác — không mismatch.
function getServerSnapshot(): AppLang {
  return "vi";
}

export function setAppLang(next: AppLang) {
  if (next === currentLang) return;
  currentLang = next;
  try {
    localStorage.setItem(LANG_STORAGE_KEY, next);
  } catch {
    // private mode / storage đầy — preference chỉ sống trong session này.
  }
  document.documentElement.lang = next;
  for (const listener of listeners) listener();
}

export function useAppLang(): AppLang {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/** Toàn bộ bộ chữ của ngôn ngữ hiện tại — `t.nav.items.importer`, v.v. */
export function useT(): Dictionary {
  return DICTIONARIES[useAppLang()];
}
