"""Curated guidance, reviewed 2026-10-09. No runtime browsing or model URLs.

These are contextual practices, not a universal standard or proof of impact.
Edit card IDs only by adding a new version; generated actions keep a snapshot.
"""

from dataclasses import asdict, dataclass

from app.schemas.action_support import Lens

LIBRARY_VERSION = "act-practices-v1"

_SOURCES = {
    "rice": ("Intercom — RICE", "https://www.intercom.com/blog/rice-simple-prioritization-for-product-managers"),
    "discovery": ("Teresa Torres — Opportunity Solution Trees", "https://www.producttalk.org/opportunity-solution-trees/"),
    "sre": ("Google SRE Workbook — Canarying Releases", "https://sre.google/workbook/canarying-releases/"),
    "hax": ("Microsoft HAX — Guidelines for Human-AI Interaction", "https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/"),
    "nist_map": ("NIST — AI RMF Playbook: Map", "https://airc.nist.gov/airmf-resources/playbook/map/"),
    "nist_manage": ("NIST — AI RMF Playbook: Manage", "https://airc.nist.gov/airmf-resources/playbook/manage/"),
    "cx": ("Qualtrics — Closed-loop Follow-up", "https://www.qualtrics.com/en-au/customer-experience/closed-loop-followup/"),
    "finops": ("FinOps Foundation — Unit Economics", "https://www.finops.org/framework/capabilities/unit-economics/"),
}


@dataclass(frozen=True)
class PracticeCard:
    id: str
    lens: Lens
    principle: str
    applies_when: str
    limitations: str
    source_title: str
    url: str
    section: str
    reviewed_on: str = "2026-10-09"


def _card(card_id, lens, source, section, principle, applies_when, limitations):
    title, url = _SOURCES[source]
    return PracticeCard(card_id, lens, principle, applies_when, limitations, title, url, section)


PRACTICES = (
    _card("rice-reach", "product", "rice", "Reach",
          "Ước lượng số người hoặc sự kiện chịu ảnh hưởng trong một khoảng thời gian xác định.",
          "So sánh phạm vi ảnh hưởng của các đề xuất.", "Số feedback không tự đại diện cho tổng số người dùng bị ảnh hưởng."),
    _card("rice-confidence", "product", "rice", "Confidence",
          "Mức chắc chắn của ước lượng phải phản ánh dữ liệu và nghiên cứu đang có.",
          "Impact hoặc effort còn dựa vào giả định.", "Confidence tự khai báo chưa phải xác suất đã được hiệu chuẩn."),
    _card("rice-effort", "product", "rice", "Effort; How to use RICE scores effectively",
          "Tính công sức của các nhóm tham gia và cân nhắc phụ thuộc khi xếp ưu tiên.",
          "Một action cần phối hợp nhiều nhóm.", "RICE là cách ưu tiên tham khảo; công thức của Happynest là weighted scoring riêng."),
    _card("discovery-outcome", "discovery", "discovery", "What is an opportunity solution tree?",
          "Nối mục tiêu với nhu cầu khách hàng rồi mới xem xét giải pháp.",
          "Đề xuất đang nhảy từ feedback sang tính năng.", "Một phát biểu đơn lẻ chưa xác nhận nhu cầu phổ biến."),
    _card("discovery-alternatives", "discovery", "discovery", "Why should you consider multiple solutions for the same target opportunity?",
          "Cân nhắc các giải pháp khác nhau cho cùng một cơ hội cải thiện.",
          "Có nhiều cách xử lý một vấn đề.", "Các lựa chọn cần khác nhau về cơ chế hoặc đánh đổi, không chỉ cách diễn đạt."),
    _card("discovery-assumptions", "discovery", "discovery", "How do you decide which solutions to pursue?",
          "Kiểm chứng giả định rủi ro của giải pháp bằng thử nghiệm trước khi đầu tư lớn.",
          "Nguyên nhân hoặc hiệu quả giải pháp chưa được xác nhận.", "Thiết kế phép thử và tiêu chí thành công theo dữ liệu thực tế."),
    _card("sre-reliability", "engineering", "sre", "Balancing Release Velocity and Reliability",
          "Cân bằng tốc độ thay đổi với mục tiêu độ tin cậy mà người dùng cần.",
          "Đề xuất ảnh hưởng tính ổn định của dịch vụ.", "Cần mục tiêu dịch vụ và số đo thực tế; không giả định độ tin cậy tuyệt đối."),
    _card("sre-canary", "engineering", "sre", "What Is Canarying?; Requirements of a Canary Process",
          "Triển khai thay đổi có giới hạn và đánh giá trước khi mở rộng.",
          "Có thể thử thay đổi trên một phần traffic hoặc người dùng.", "Nhóm nhỏ có thể chưa phát hiện lỗi hiếm hoặc khác biệt giữa các phân khúc."),
    _card("sre-rollback", "engineering", "sre", "A Roll Forward Deployment Versus a Simple Canary Deployment",
          "Xác định tín hiệu đánh giá và cách dừng hoặc rollback khi thay đổi gây tác hại.",
          "Action thay đổi hành vi production.", "Chỉ đề xuất rollback khi hệ thống có khả năng thực hiện và đo được tác động."),
    _card("hax-capabilities", "ux", "hax", "G1 — Make clear what the system can do; G2 — Make clear how well the system can do what it can do",
          "Giúp người dùng hiểu khả năng và giới hạn chất lượng của AI.",
          "Kỳ vọng của người dùng lệch với khả năng hệ thống.", "Nêu giới hạn cần đi cùng cải thiện trải nghiệm phù hợp."),
    _card("hax-correction", "ux", "hax", "G9 — Support efficient correction",
          "Tạo cách hiệu quả để người dùng sửa kết quả hoặc hành vi AI không đúng.",
          "Người dùng gặp lỗi AI và khó sửa.", "Cơ chế sửa lỗi không tự cải thiện độ chính xác của model."),
    _card("hax-explanation", "ux", "hax", "G10 — Scope services when in doubt; G11 — Make clear why the system did what it did",
          "Giải thích hành vi AI và thu hẹp hỗ trợ khi hệ thống thiếu chắc chắn.",
          "Người dùng khó hiểu kết quả hoặc cần quyết định trong bất định.", "Giải thích phải dựa trên thông tin hệ thống thực sự có."),
    _card("nist-context", "risk", "nist_map", "MAP 1.1 — Context, users and impacts",
          "Xem xét bối cảnh sử dụng, bên bị ảnh hưởng và tác động bất lợi của AI.",
          "Feedback gợi nguy cơ gây hại hoặc ảnh hưởng nhóm dễ tổn thương.", "AI RMF là hướng dẫn tự nguyện, không phải kết luận tuân thủ pháp luật."),
    _card("nist-manage", "risk", "nist_manage", "MANAGE 1; MANAGE 4 — Risk treatment and monitoring",
          "Chọn cách xử lý rủi ro, trách nhiệm và theo dõi hiệu lực biện pháp.",
          "Một rủi ro đã được nhận diện cần quyết định xử lý.", "Cần người có trách nhiệm xác nhận mức rủi ro và biện pháp theo bối cảnh."),
    _card("cx-followup", "customer_success", "cx", "Closed-loop feedback and follow-up",
          "Theo dõi phản hồi tới bước hỗ trợ giải quyết vấn đề của khách hàng.",
          "Có vấn đề cần đội hỗ trợ tiếp tục xử lý.", "ACT chỉ đề xuất; liên hệ khách hàng phải theo quyền và quy trình của tổ chức."),
    _card("cx-systemic", "customer_success", "cx", "Action planning tools",
          "Phối hợp các nhóm để giải quyết vấn đề trải nghiệm có tính hệ thống.",
          "Nhiều phản hồi cùng chỉ tới vấn đề lặp lại.", "Theo dõi từng ca chưa chứng minh nguyên nhân hệ thống đã được giải quyết."),
    _card("finops-unit-value", "finance", "finops", "Definition — resource efficiency and business unit metrics",
          "Liên hệ chi phí công nghệ với kết quả hữu ích, như chi phí mỗi ca giải quyết thành công.",
          "Action có đánh đổi giữa chi phí và giá trị.", "Thiếu dữ liệu chi phí hoặc kết quả thì chỉ đề xuất cách đo, không bịa ROI."),
    _card("finops-trends", "finance", "finops", "Validate Impact of Unit Metrics",
          "Theo dõi chỉ số chi phí và giá trị theo thời gian trong phạm vi nhất quán.",
          "Cần kiểm tra thay đổi có cải thiện hiệu quả kinh tế hay không.", "So sánh cần cùng phạm vi và cách tính; chi phí tăng có thể đi cùng giá trị tăng."),
)

PRACTICES_BY_ID = {card.id: card for card in PRACTICES}


def catalog_for_prompt() -> list[dict[str, str]]:
    """Provide principles and applicability; public URLs are hydrated server-side."""
    return [
        {"card_id": card.id, "lens": card.lens, "principle": card.principle,
         "applies_when": card.applies_when, "limitations": card.limitations,
         "source_title": card.source_title, "section": card.section}
        for card in PRACTICES
    ]


def reference_metadata(card_id: str) -> dict[str, str]:
    card = asdict(PRACTICES_BY_ID[card_id])
    card["card_id"] = card.pop("id")
    return card
