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
      taxonomy: "Chủ đề",
      vault: "Kho phản hồi",
      dataGraph: "Khám phá",
      reports: "Báo cáo",
      matrix: "Ma trận ưu tiên",
      stakeholders: "Phòng ban",
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
    utilities: "Tiện ích",
    whatsNew: "Có gì mới",
  },
  importer: {
    title: "Nhập dữ liệu",
    description:
      "Một file CSV có cột nội dung phản hồi là đủ. AI đoán ý nghĩa từng cột, bạn xác nhận trước khi lưu.",
    back: "Quay lại",
    steps: ["Chọn file", "Xem trước", "Xác nhận cột", "Kết quả"],
    stepsLabel: "Các bước nhập",
    productLine: (name: string) => `Sản phẩm: ${name}`,
    howTitle: "Quy trình nhập",
    how: [
      "Tải lên CSV có cột chứa nội dung phản hồi.",
      "Kiểm tra dữ liệu mẫu đã ẩn thông tin cá nhân.",
      "Yêu cầu AI gợi ý ý nghĩa các cột rồi duyệt trước khi nhập.",
      "Mở Kho phản hồi để xem dữ liệu và bắt đầu phân loại.",
    ],
    queueTitle: "Đang chờ bạn",
    queueDescription: "File đang chờ xác nhận cột hoặc gặp lỗi.",
    continue: "Tiếp tục",
    historyTitle: "Đã nhập",
    colFile: "File",
    colRows: "Dòng",
    colStatus: "Trạng thái",
    open: "Xem",
    status: {
      profile_ready: "Chờ xác nhận cột",
      mapping_generating: "AI đang đọc cột",
      mapping_review: "Chờ xác nhận cột",
      importing: "Đang nhập",
      imported: "Đã nhập",
      failed: "Lỗi",
      cancelled: "Đã huỷ",
    } as Record<string, string>,
    file: {
      title: "Tải phản hồi lên",
      description: "Xem trước chỉ dùng dữ liệu đã ẩn thông tin cá nhân — chưa gọi AI.",
      drop: "Kéo thả file CSV vào đây",
      choose: "Chọn file",
      uploading: (name: string) => `Đang tải “${name}” lên…`,
      needProduct: "Hãy chọn sản phẩm trước (menu sản phẩm ở thanh trên cùng).",
      cancel: "Huỷ",
      uploaded: "Đã có bản xem trước — chưa dùng AI.",
      uploadFailed: "Không tải được file.",
    },
    preview: {
      proposing: "AI đang đọc ý nghĩa các cột",
      proposingBody:
        "Chỉ hồ sơ cột và giá trị mẫu đã ẩn thông tin cá nhân được gửi đi. Bạn có thể rời màn này.",
      lastFailed: "Lần thử trước bị lỗi",
      loadFailed: "Không tải được bản xem trước",
      loadFailedHint: "bản xem trước vẫn được giữ trên máy chủ.",
      retry: "Thử lại",
      rowsCols: (rows: number, cols: number) => `${rows} dòng · ${cols} cột`,
      noAi: "Chưa dùng AI · mẫu đã ẩn thông tin cá nhân",
      colColumn: "Cột",
      colType: "Kiểu",
      colSample: "Giá trị mẫu",
      hint: "Nhìn qua cấu trúc file rồi để AI đoán ý nghĩa từng cột.",
      backToFile: "Chọn file khác",
      suggest: "Để AI đọc cột",
      confirmTitle: "Gửi cho AI đọc cột?",
      confirmBody:
        "Một lần gọi AI. Chỉ hồ sơ cột và giá trị mẫu đã ẩn thông tin cá nhân được gửi — không gửi file gốc. Bạn xác nhận kết quả ở bước sau.",
      confirmBack: "Quay lại",
      confirmGo: "Gửi cho AI",
      startFailed: "Không bắt đầu được.",
    },
    mapping: {
      colCsv: "Cột trong CSV",
      colSuggest: "AI đề xuất",
      colExplain: "Giải thích",
      colAction: "Quyết định",
      approve: "Đồng ý",
      change: "Đổi…",
      ignore: "Bỏ qua",
      ambiguous: "Chưa rõ",
      newField: "trường mới",
      sourceMeta: "Thông tin nguồn",
      core: {
        feedback_text: "Nội dung phản hồi",
        occurred_at: "Ngày phản hồi",
        source: "Thông tin nguồn",
        source_record_id: "Mã bản ghi nguồn",
      } as Record<string, string>,
      targetPlaceholder: "Tên trường — vd: occurred_at",
      willCreate: (key: string) => `Sẽ tạo trường mới “${key}”.`,
      decisionFor: (column: string) => `Quyết định cho ${column}`,
      gateTitle: "Xác nhận ý nghĩa các cột",
      gateBody: "Giữ nguyên đề xuất của AI nếu thấy đúng.",
      changed: (n: number) => ` Bạn đã đổi ${n} cột.`,
      pendingChange: (n: number) => ` ${n} cột chọn “Đổi…” nhưng chưa nhập tên trường.`,
      duplicateAuto: (kept: string) =>
        `Cùng ý nghĩa với cột “${kept}” — đã tự bỏ qua để không trùng. Chọn lại nếu muốn.`,
      duplicateConflict: (other: string) =>
        `Trùng ý nghĩa với cột “${other}” — mỗi ý nghĩa chỉ nhận một cột.`,
      conflicts: (n: number) => ` ${n} cột đang trùng ý nghĩa — hãy bỏ qua bớt để nhập.`,
      backToPreview: "Quay lại xem trước",
      confirm: "Xác nhận & nhập",
      confirmTitle: "Nhập file với các cột này?",
      confirmBody:
        "Hệ thống nhập nền và chỉ lưu nội dung đã ẩn thông tin cá nhân. AI chỉ phân loại khi bạn bấm ở bước sau.",
      checkAgain: "Kiểm tra lại",
      go: "Nhập ngay",
      importFailed: "Không bắt đầu nhập được.",
    },
    result: {
      importing: "Đang nhập…",
      importingBody: "Bạn có thể rời màn này — lộ trình tự cập nhật khi xong.",
      importingStatus: "Đang ẩn thông tin cá nhân và lưu từng dòng…",
      failed: "Nhập thất bại",
      unknownError: "Lỗi không xác định",
      another: "Nhập file khác",
      cancelled: "Đã huỷ nhập",
      cancelledBody: "Chưa có gì được ghi. Bắt đầu lại khi bạn sẵn sàng.",
      inReview: "File chưa được nhập",
      inReviewBody: "Hãy xác nhận cột của file trước.",
      backToImporter: "Về màn nhập",
      done: "Đã nhập xong",
      sourceRows: "dòng trong file",
      imported: "đã nhập",
      failedRows: "lỗi",
      rowErrors: "Dòng bị lỗi",
      rowError: (row: number, reason: string) => `Dòng ${row}: ${reason}`,
      rowErrorsHint: "Sửa rồi nhập lại riêng các dòng lỗi.",
      nextTitle: "Bước tiếp: AI phân loại phản hồi",
      nextBody:
        "AI gắn chủ đề, mức độ và cảm xúc cho từng phản hồi vừa nhập. Bạn xem ước tính chi phí trước khi chạy.",
      classify: "Phân loại ngay",
    },
  },
  vault: {
    analyze: (n: number) => (n > 0 ? `Phân loại ${n} mục chờ` : "Phân loại mục chờ"),
    pendingLine: (n: number) => `${n} mục chờ phân loại trong phạm vi này · tối đa 100 mục mỗi lượt`,
    chooseImport: "Chọn một file trước.",
    receiptTitle: "Phân loại bằng AI?",
    receiptHeadline: (n: number) => `AI sẽ phân loại ${n} phản hồi`,
    inScope: "phản hồi",
    classifyCalls: "lượt phân loại",
    embedCalls: "lượt nhúng",
    maxAttempts: "lượt thử tối đa",
    inputTokens: "token đầu vào",
    remaining: "còn chờ sau lượt này",
    receiptNote:
      "Ước tính có trước khi chạy. Nếu dữ liệu đổi từ lúc xem ước tính, hệ thống từ chối để bạn xem lại.",
    receiptFile: "File",
    receiptNothingTitle: "File này không còn mục nào chạy được",
    receiptNothingBody:
      "Các phản hồi chờ phân loại của file này đang được một lượt khác xử lý, hoặc đã phân loại xong. Đợi lượt đang chạy kết thúc rồi thử lại.",
    receiptOtherFiles: (n: number) =>
      `Mỗi lượt chạy một file. Còn ${n} mục chờ ở các file khác — sau lượt này, bấm “Phân loại” lần nữa để chạy tiếp.`,
    receiptStartFailed: "Chưa bắt đầu được lượt phân loại",
    receiptRefresh: "Xem lại ước tính",
    busyLine: (n: number) =>
      `${n} mục đang được phân loại trong lượt đang chạy — chưa còn mục nào để chạy thêm.`,
    back: "Quay lại",
    start: "Bắt đầu phân loại",
    runTitle: "Phân loại bằng AI",
    runStatus: {
      running: "Đang phân loại",
      completed: "Đã xong",
      failed: "Lỗi",
      cancelled: "Đã dừng",
    } as Record<string, string>,
    runLeave: "Bạn có thể rời màn này — lộ trình tự cập nhật khi xong.",
    stop: "Dừng phân loại",
    stopping: "Đang dừng…",
    stopRequested: "Đã yêu cầu dừng — áp dụng sau mục hiện tại.",
    closeCard: "Đóng thẻ",
    toastDone: "Phân loại xong — danh sách đã cập nhật.",
    toastFailed: "Phân loại gặp lỗi — xem thẻ tiến trình.",
    nextTitle: "Bước tiếp: hỏi AI về dữ liệu này",
    nextBody: "AI tự tìm bằng chứng trong phản hồi đã phân loại và đưa kết luận để bạn duyệt.",
    nextCta: "Hỏi AI",
  },
  graph: {
    askTitle: "Hỏi AI về phản hồi",
    askBody:
      "Chọn câu gợi ý để điền vào ô soạn. Bạn có thể chỉnh lại trước khi bấm Hỏi AI để bắt đầu điều tra.",
    placeholder: "Ví dụ: Vấn đề nào đang ảnh hưởng người dùng nhiều nhất?",
    ask: "Hỏi AI",
    suggestionsLabel: "Câu hỏi gợi ý",
    suggestions: [
      "Vấn đề nào đang ảnh hưởng người dùng nhiều nhất?",
      "Lỗi nghiêm trọng nào cần xử lý ngay?",
      "Điều gì khiến người dùng không hài lòng nhất?",
      "Người dùng khen tính năng nào nhiều nhất?",
    ],
    noData: "Chưa có phản hồi nào được phân loại — hãy phân loại ở bước 2 trước.",
    goClassify: "Đi tới bước phân loại",
    started: "Đã bắt đầu điều tra. Tiến độ và phần duyệt hiện ngay bên dưới.",
    startFailed: "Không bắt đầu được cuộc điều tra.",
    exploreTitle: "Khám phá dữ liệu",
    scopeLoading: "Đang tải phạm vi dữ liệu…",
    scopeEmpty: "Chọn file ở cột bên trái rồi bấm Áp dụng để khám phá.",
    emptyNoneTitle: "Chưa có phản hồi nào được phân loại trong phạm vi này",
    emptyNoneBody: "Phân loại các mục chờ ở Kho phản hồi, rồi quay lại đây.",
    emptyNoneCta: "Mở Kho phản hồi",
    emptyUncatTitle: (n: number) => `${n} phản hồi đã phân loại nhưng chưa có chủ đề`,
    emptyUncatBody:
      "Lúc phân loại, sản phẩm chưa có bộ chủ đề (hoặc không chủ đề nào khớp) nên AI gắn nhãn UNCATEGORIZED. Tạo hoặc cập nhật bộ chủ đề, rồi mở khoá để phân loại lại.",
    emptyUncatCta: "Tạo bộ chủ đề",
    emptyUncatReclassify: "Mở khoá và phân loại lại",
    trends: {
      tab: "Xu hướng",
      title: "Lượng phản hồi theo thời gian",
      description: "Tính theo ngày phát sinh của phản hồi đã phân loại trong các lô đang chọn.",
      other: "Mức khác hoặc chưa có mức",
      severe: "Cao hoặc nghiêm trọng",
      granularity: "Gộp phản hồi theo thời gian",
      day: "Theo ngày",
      week: "Theo tuần",
      count: (n: number) => n.toLocaleString("vi-VN") + " phản hồi",
      pick: "Chọn một cột để xem số liệu và mở bảng phản hồi của ngày hoặc tuần đó.",
      partial: "Biểu đồ dựa trên tối đa 100 phản hồi đã tải từ mỗi lô.",
      viewFeedback: "Xem phản hồi",
      clear: "Bỏ lọc ngày",
      emptyTitle: "Chưa có phản hồi đã phân loại có ngày phát sinh",
      emptyDescription: "Chọn lô nhập có ngày phản hồi và áp dụng để xem diễn biến theo thời gian.",
      loadFailed: "Chưa tải được dữ liệu xu hướng.",
      retry: "Tải lại",
    },
  },
  matrixPage: {
    addManual: "Tự thêm hành động",
    noReportTitle: "Chưa có kết luận nào được duyệt",
    noReportBody: "Hành động chỉ được tạo từ kết luận đã duyệt. Hãy hỏi AI và duyệt một kết luận trước.",
    noReportCta: "Hỏi AI",
    notApprovedTitle: "Kết luận này chưa được duyệt",
    notApprovedBody: "Duyệt kết luận trước, rồi mới tạo hành động từ nó.",
    reviewIt: "Duyệt kết luận",
    noActionsTitle: "Kết luận này chưa có hành động",
    noActionsBody:
      "AI đề xuất việc cần làm cho từng nhóm phụ trách, kèm điểm tác động và công sức. Bạn quyết định từng việc.",
    generate: "Tạo gợi ý hành động bằng AI",
    generating: "Đang tạo gợi ý… (thường mất vài phút)",
    generateFailed: "Chưa tạo được gợi ý. Thử lại — kết luận đã duyệt vẫn được giữ.",
    noSuggestion: "Chưa có gợi ý phù hợp từ bằng chứng hiện tại.",
    filteredEmpty: "Không có hành động nào khớp bộ lọc.",
    decideTitle: (n: number) => `Chờ bạn quyết định (${n})`,
    decideBody: "Nhận việc nên làm, chỉnh điểm nếu cần, hoặc từ chối. Việc đã nhận sẽ được bàn giao.",
    sourceReport: "Xem kết luận gốc",
    byDepartment: "Bàn giao theo nhóm",
  },
  journey: {
    checking: "Đang kiểm tra tiến độ…",
    progressLabel: "Bước tiếp theo",
    nextLabel: "Bước tiếp theo",
    meta: {
      feedback: (n: number) => `${n} phản hồi`,
      pending: (n: number) => `${n} chờ phân loại`,
      review: (n: number) => `${n} chờ duyệt`,
      open: (n: number) => `${n} chờ quyết định`,
      accepted: (n: number) => `${n} việc đã nhận`,
    },
    next: {
      createProduct: {
        title: "Tạo sản phẩm đầu tiên",
        body: "Mỗi sản phẩm là một không gian riêng chứa phản hồi của nó.",
        cta: "Tạo sản phẩm",
      },
      finishMapping: {
        title: (file: string) => `Xác nhận cột cho “${file}”`,
        body: "AI đã đoán ý nghĩa từng cột. Kiểm tra nhanh rồi bấm nhập — chưa có gì được lưu.",
        cta: "Xác nhận cột",
      },
      importing: {
        title: (file: string) => `Đang nhập “${file}”…`,
        body: "Hệ thống đang ẩn thông tin cá nhân và lưu từng dòng. Bạn có thể rời màn này.",
        cta: "Xem tiến độ",
      },
      importFirst: {
        title: "Nhập file phản hồi đầu tiên",
        body: "Chỉ cần một file CSV có cột nội dung phản hồi. Thông tin cá nhân được ẩn trước khi lưu.",
        cta: "Chọn file CSV",
      },
      classifying: {
        title: "AI đang phân loại phản hồi",
        body: (done: number, total: number) =>
          `Đã xong ${done}/${total} mục. Bạn có thể rời màn này — lộ trình tự sang bước kế khi xong.`,
        cta: "Xem tiến độ",
      },
      buildTopics: {
        title: "Tạo bộ chủ đề cho sản phẩm",
        body: "AI đọc mẫu phản hồi và đề xuất các chủ đề (vd: đăng nhập, thanh toán). Bạn duyệt rồi áp dụng — sau đó AI phân loại theo đúng các chủ đề này.",
        cta: "Tạo bộ chủ đề",
      },
      reclassify: {
        title: (n: number) => `${n} phản hồi chưa có chủ đề`,
        body: "Bộ chủ đề đã sẵn sàng. Phân loại lại để mỗi phản hồi được gắn đúng chủ đề.",
        cta: "Phân loại lại",
      },
      classify: {
        title: (n: number) => `${n} phản hồi chưa được phân loại`,
        body: "AI gắn chủ đề, mức độ và cảm xúc cho từng phản hồi. Bạn xem ước tính chi phí trước khi chạy.",
        cta: "Phân loại ngay",
      },
      reviewFinding: {
        title: "Một kết luận đang chờ bạn duyệt",
        body: (title: string) => `“${title}” — xem bằng chứng rồi duyệt, sửa hoặc từ chối.`,
        cta: "Duyệt kết luận",
      },
      ask: {
        title: "Hỏi AI về phản hồi đã phân loại",
        body: "Chọn một câu hỏi gợi ý hoặc tự gõ. AI tự tìm bằng chứng và đưa kết luận để bạn duyệt.",
        cta: "Đặt câu hỏi",
      },
      openActions: {
        title: "Biến kết luận đã duyệt thành hành động",
        body: (title: string) => `Xem các việc cần làm cho “${title}”.`,
        cta: "Xem hành động",
      },
      generateActions: {
        title: "Biến kết luận đã duyệt thành hành động",
        body: (title: string) =>
          `AI đề xuất việc cần làm cho “${title}”, chia theo nhóm phụ trách và xếp theo ưu tiên.`,
        cta: "Tạo gợi ý hành động",
      },
      decideActions: {
        title: (n: number) => `${n} hành động chờ bạn quyết định`,
        body: "Nhận, chỉnh điểm hoặc từ chối từng gợi ý. Hành động đã nhận sẽ được bàn giao.",
        cta: "Chọn hành động",
      },
      handoff: {
        title: "Bàn giao việc cho các nhóm",
        body: (n: number) => `${n} hành động đã nhận — mỗi nhóm thấy việc của mình kèm bằng chứng gốc.`,
        cta: "Mở bàn giao",
      },
      complete: {
        title: "Vòng phản hồi đã khép kín",
        body: "Gửi bảng này cho các nhóm, hoặc nhập dữ liệu mới để bắt đầu vòng tiếp theo.",
        cta: "Nhập dữ liệu mới",
      },
    },
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
    menu: "Menu hồ sơ",
    username: "Tên hiển thị",
    usernamePlaceholder: "Nhập tên hiển thị",
    usernameSave: "Lưu tên",
    usernameSaved: "Đã lưu tên hiển thị.",
    usernameSaveFailed: "Không lưu được tên hiển thị. Hãy thử lại.",
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
    utilities: "Utilities",
    whatsNew: "What's new",
  },
  importer: {
    title: "Importer",
    description:
      "A CSV with a feedback text column is enough. AI guesses what each column means; you confirm before anything is stored.",
    back: "Back",
    steps: ["Choose file", "Preview", "Confirm columns", "Result"],
    stepsLabel: "Import steps",
    productLine: (name: string) => `Product: ${name}`,
    howTitle: "Import workflow",
    how: [
      "Upload a CSV with a feedback text column.",
      "Review the sample rows with personal data masked.",
      "Ask AI to suggest column mappings, then approve them to import.",
      "Open the Feedback Vault to review and classify the data.",
    ],
    queueTitle: "Waiting for you",
    queueDescription: "Files waiting for column confirmation or with errors.",
    continue: "Continue",
    historyTitle: "Imported",
    colFile: "File",
    colRows: "Rows",
    colStatus: "Status",
    open: "View",
    status: {
      profile_ready: "Confirm columns",
      mapping_generating: "AI reading columns",
      mapping_review: "Confirm columns",
      importing: "Importing",
      imported: "Imported",
      failed: "Failed",
      cancelled: "Cancelled",
    } as Record<string, string>,
    file: {
      title: "Upload feedback",
      description: "The preview only uses data with personal details masked — no AI yet.",
      drop: "Drop a CSV file here",
      choose: "Choose file",
      uploading: (name: string) => `Uploading “${name}”…`,
      needProduct: "Choose a product first (product menu in the top bar).",
      cancel: "Cancel",
      uploaded: "Preview ready — no AI used yet.",
      uploadFailed: "Could not upload the file.",
    },
    preview: {
      proposing: "AI is reading what the columns mean",
      proposingBody:
        "Only the column profile and masked sample values are sent. You can leave this screen.",
      lastFailed: "Last attempt failed",
      loadFailed: "Could not load the preview",
      loadFailedHint: "the preview is still on the server.",
      retry: "Retry",
      rowsCols: (rows: number, cols: number) => `${rows} rows · ${cols} columns`,
      noAi: "No AI used yet · samples masked",
      colColumn: "Column",
      colType: "Type",
      colSample: "Sample values",
      hint: "Glance at the structure, then let AI guess what each column means.",
      backToFile: "Choose another file",
      suggest: "Let AI read the columns",
      confirmTitle: "Send to AI to read the columns?",
      confirmBody:
        "One AI call. Only the column profile and masked sample values are sent — never the raw file. You confirm the result next.",
      confirmBack: "Back",
      confirmGo: "Send to AI",
      startFailed: "Could not start.",
    },
    mapping: {
      colCsv: "CSV column",
      colSuggest: "AI suggests",
      colExplain: "Why",
      colAction: "Decision",
      approve: "Accept",
      change: "Change…",
      ignore: "Ignore",
      ambiguous: "Unclear",
      newField: "new field",
      sourceMeta: "Source details",
      core: {
        feedback_text: "Feedback text",
        occurred_at: "Feedback date",
        source: "Source details",
        source_record_id: "Source record ID",
      } as Record<string, string>,
      targetPlaceholder: "Field name — e.g. occurred_at",
      willCreate: (key: string) => `Creates a new field “${key}”.`,
      decisionFor: (column: string) => `Decision for ${column}`,
      gateTitle: "Confirm what these columns mean",
      gateBody: "Keep the AI proposal if it looks right.",
      changed: (n: number) => ` You changed ${n} column(s).`,
      pendingChange: (n: number) => ` ${n} column(s) set to “Change…” without a field name.`,
      duplicateAuto: (kept: string) =>
        `Same meaning as “${kept}” — ignored automatically to avoid a clash. Change it if needed.`,
      duplicateConflict: (other: string) =>
        `Same meaning as “${other}” — each meaning takes one column.`,
      conflicts: (n: number) => ` ${n} columns share a meaning — ignore the extras to import.`,
      backToPreview: "Back to preview",
      confirm: "Confirm & import",
      confirmTitle: "Import the file with these columns?",
      confirmBody:
        "The import runs in the background and stores masked feedback only. AI classifies only when you ask in the next step.",
      checkAgain: "Check again",
      go: "Import now",
      importFailed: "Import could not start.",
    },
    result: {
      importing: "Importing…",
      importingBody: "You can leave this screen — the journey updates when it finishes.",
      importingStatus: "Masking personal data and storing rows…",
      failed: "Import failed",
      unknownError: "Unknown error",
      another: "Import another file",
      cancelled: "Import cancelled",
      cancelledBody: "Nothing was written. Start over whenever you are ready.",
      inReview: "This file is not imported yet",
      inReviewBody: "Confirm its columns first.",
      backToImporter: "Back to import",
      done: "Import completed",
      sourceRows: "rows in file",
      imported: "imported",
      failedRows: "failed",
      rowErrors: "Rows with errors",
      rowError: (row: number, reason: string) => `Row ${row}: ${reason}`,
      rowErrorsHint: "Fix and re-import only the failed rows.",
      nextTitle: "Next: AI classifies the feedback",
      nextBody:
        "AI tags each imported item with topic, severity and sentiment. You see the cost estimate before it runs.",
      classify: "Classify now",
    },
  },
  vault: {
    analyze: (n: number) => (n > 0 ? `Classify ${n} pending` : "Classify pending"),
    pendingLine: (n: number) => `${n} pending in this scope · up to 100 per run`,
    chooseImport: "Choose a file first.",
    receiptTitle: "Classify with AI?",
    receiptHeadline: (n: number) => `AI will classify ${n} feedback items`,
    inScope: "items",
    classifyCalls: "classify calls",
    embedCalls: "embed calls",
    maxAttempts: "max attempts",
    inputTokens: "input tokens",
    remaining: "still pending after this",
    receiptNote:
      "The estimate comes before anything runs. If the selection changed since, the run is rejected so you can review again.",
    receiptFile: "File",
    receiptNothingTitle: "Nothing left to run in this file",
    receiptNothingBody:
      "This file's pending feedback is being classified by another run, or is already done. Wait for the running one to finish, then try again.",
    receiptOtherFiles: (n: number) =>
      `Each run covers one file. ${n} more are pending in other files — after this run, click “Classify” again to continue.`,
    receiptStartFailed: "Could not start the classification run",
    receiptRefresh: "Refresh estimate",
    busyLine: (n: number) =>
      `${n} items are being classified by the running job — nothing more to start yet.`,
    back: "Back",
    start: "Start classifying",
    runTitle: "AI classification",
    runStatus: {
      running: "Classifying",
      completed: "Done",
      failed: "Failed",
      cancelled: "Stopped",
    } as Record<string, string>,
    runLeave: "You can leave this screen — the journey updates when it finishes.",
    stop: "Stop classifying",
    stopping: "Stopping…",
    stopRequested: "Stop requested — it applies after the current item.",
    closeCard: "Close card",
    toastDone: "Classification finished — the list is up to date.",
    toastFailed: "Classification failed — see the progress card.",
    nextTitle: "Next: ask AI about this data",
    nextBody: "AI gathers evidence from the classified feedback and drafts a finding for you to review.",
    nextCta: "Ask AI",
  },
  graph: {
    askTitle: "Ask AI about your feedback",
    askBody:
      "Choose a suggestion to fill the draft. Edit it if you like, then select Ask AI to start the investigation.",
    placeholder: "e.g. Which problem affects the most users?",
    ask: "Ask AI",
    suggestionsLabel: "Suggested questions",
    suggestions: [
      "Which problem affects the most users?",
      "Which critical bugs need fixing right now?",
      "What frustrates users the most?",
      "Which feature do users praise the most?",
    ],
    noData: "No feedback is classified yet — classify it in step 2 first.",
    goClassify: "Go to classification",
    started: "Investigation started. Progress and review appear right below.",
    startFailed: "Could not start the investigation.",
    scopeLoading: "Loading the dataset scope…",
    scopeEmpty: "Pick files in the left column, then click Apply to explore.",
    emptyNoneTitle: "No classified feedback in this scope yet",
    emptyNoneBody: "Classify the pending items in the Vault, then come back.",
    emptyNoneCta: "Open the Vault",
    emptyUncatTitle: (n: number) => `${n} items are classified but have no topic`,
    emptyUncatBody:
      "The product had no topic set when these were classified (or no topic matched), so AI tagged them UNCATEGORIZED. Create or update the topic set, then unlock to reclassify.",
    emptyUncatCta: "Create the topic set",
    emptyUncatReclassify: "Unlock and reclassify",
    exploreTitle: "Explore the data",
    trends: {
      tab: "Trends",
      title: "Feedback volume over time",
      description: "By the reported date of classified feedback in the selected imports.",
      other: "Other or unrated severity",
      severe: "High or critical severity",
      granularity: "Group feedback by time",
      day: "By day",
      week: "By week",
      count: (n: number) => n.toLocaleString("en-US") + " feedback items",
      pick: "Select a bar for counts and to open the feedback table for that day or week.",
      partial: "This chart uses up to 100 loaded feedback items from each import.",
      viewFeedback: "View feedback",
      clear: "Clear date filter",
      emptyTitle: "No dated, classified feedback",
      emptyDescription: "Select and apply an import with dated feedback to see how volume changes over time.",
      loadFailed: "Could not load trend data.",
      retry: "Reload",
    },
  },
  matrixPage: {
    addManual: "Add an action",
    noReportTitle: "No approved finding yet",
    noReportBody: "Actions come only from approved findings. Ask AI and approve a finding first.",
    noReportCta: "Ask AI",
    notApprovedTitle: "This finding is not approved yet",
    notApprovedBody: "Approve the finding first, then create actions from it.",
    reviewIt: "Review finding",
    noActionsTitle: "This finding has no actions yet",
    noActionsBody:
      "AI proposes what each owning team should do, with impact and effort scores. You decide on each one.",
    generate: "Suggest actions with AI",
    generating: "Suggesting… (usually a few minutes)",
    generateFailed: "Could not suggest actions. Try again — the approved finding is kept.",
    noSuggestion: "No suitable suggestion from the current evidence.",
    filteredEmpty: "No action matches these filters.",
    decideTitle: (n: number) => `Waiting for your decision (${n})`,
    decideBody: "Accept what is worth doing, re-score if needed, or reject. Accepted work gets handed off.",
    sourceReport: "View source finding",
    byDepartment: "Hand off by team",
  },
  journey: {
    checking: "Checking progress…",
    progressLabel: "Next step",
    nextLabel: "Next step",
    meta: {
      feedback: (n: number) => `${n} feedback`,
      pending: (n: number) => `${n} to classify`,
      review: (n: number) => `${n} to review`,
      open: (n: number) => `${n} to decide`,
      accepted: (n: number) => `${n} accepted`,
    },
    next: {
      createProduct: {
        title: "Create your first product",
        body: "Each product is its own space for its feedback.",
        cta: "Create product",
      },
      finishMapping: {
        title: (file: string) => `Confirm the columns of “${file}”`,
        body: "AI guessed what each column means. Check it, then import — nothing is stored yet.",
        cta: "Confirm columns",
      },
      importing: {
        title: (file: string) => `Importing “${file}”…`,
        body: "Personal data is being masked and rows stored. You can leave this screen.",
        cta: "View progress",
      },
      importFirst: {
        title: "Import your first feedback file",
        body: "All you need is a CSV with a feedback text column. Personal data is masked before storage.",
        cta: "Choose a CSV file",
      },
      classifying: {
        title: "AI is classifying feedback",
        body: (done: number, total: number) =>
          `${done} of ${total} done. You can leave — the journey moves on when it finishes.`,
        cta: "View progress",
      },
      buildTopics: {
        title: "Create the topic set for this product",
        body: "AI reads sample feedback and proposes topics (e.g. login, billing). You review and apply them — then AI classifies against exactly these topics.",
        cta: "Create topics",
      },
      reclassify: {
        title: (n: number) => `${n} feedback without a topic`,
        body: "The topic set is ready. Re-classify so each item gets the right topic.",
        cta: "Re-classify",
      },
      classify: {
        title: (n: number) => `${n} feedback not classified yet`,
        body: "AI tags each item with topic, severity and sentiment. You see the cost estimate before it runs.",
        cta: "Classify now",
      },
      reviewFinding: {
        title: "A finding is waiting for your review",
        body: (title: string) => `“${title}” — check the evidence, then approve, edit or reject.`,
        cta: "Review finding",
      },
      ask: {
        title: "Ask AI about your classified feedback",
        body: "Pick a suggested question or type your own. AI gathers evidence and drafts a finding for you to review.",
        cta: "Ask a question",
      },
      openActions: {
        title: "Turn the approved finding into actions",
        body: (title: string) => `See what to do about “${title}”.`,
        cta: "View actions",
      },
      generateActions: {
        title: "Turn the approved finding into actions",
        body: (title: string) =>
          `AI proposes what to do about “${title}”, split by owning team and ranked by priority.`,
        cta: "Suggest actions",
      },
      decideActions: {
        title: (n: number) => `${n} actions waiting for your decision`,
        body: "Accept, re-score or reject each suggestion. Accepted actions get handed off.",
        cta: "Choose actions",
      },
      handoff: {
        title: "Hand the work to each team",
        body: (n: number) => `${n} accepted actions — each team sees its own work with the source evidence.`,
        cta: "Open hand-off",
      },
      complete: {
        title: "The feedback loop is closed",
        body: "Share this board with the teams, or import new data to start the next loop.",
        cta: "Import new data",
      },
    },
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
    menu: "Profile menu",
    username: "Display name",
    usernamePlaceholder: "Enter a display name",
    usernameSave: "Save name",
    usernameSaved: "Display name saved.",
    usernameSaveFailed: "Couldn't save your display name. Try again.",
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
