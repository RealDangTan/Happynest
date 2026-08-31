export type MarketingSection = {
  id: string;
  eyebrow: string;
  title: string;
  body: string;
  bullets?: readonly string[];
  link?: { label: string; href: string };
};

export type MarketingPage = {
  href: string;
  navLabel: string;
  eyebrow: string;
  title: string;
  description: string;
  sections: readonly MarketingSection[];
};

export const MARKETING_NAV = [
  { label: "Product", href: "/product" },
  { label: "Docs", href: "/docs" },
  { label: "Company", href: "/company" },
  { label: "Field notes", href: "/blog" },
] as const;

export const MARKETING_PAGES: readonly MarketingPage[] = [
  {
    href: "/product",
    navLabel: "Product",
    eyebrow: "The operating loop",
    title: "Turn scattered feedback into decisions people can defend.",
    description:
      "Happynest is a Voice-of-Customer operating system for AI product teams. It preserves the path from raw signal to reviewed action across one visible LISTEN → UNDERSTAND → ACT loop.",
    sections: [
      {
        id: "listen",
        eyebrow: "LISTEN",
        title: "Bring uneven source data into one evidence model.",
        body:
          "Import CSV exports from support, surveys, app reviews, email, and in-product channels. Happynest profiles each source, proposes a reusable schema mapping, and pauses at Gate 1 until a person approves how those columns should be understood.",
        bullets: [
          "Versioned source schemas instead of one-off column guesses",
          "Vietnamese–English feedback preserved as first-class input",
          "PII sanitized before content crosses the model boundary",
        ],
      },
      {
        id: "understand",
        eyebrow: "UNDERSTAND",
        title: "Build findings from traceable evidence, not fluent guesses.",
        body:
          "Classification, semantic themes, trend checks, and deterministic analytics produce an evidence packet. The agent plans which tools to use, evaluates whether the evidence is sufficient, and labels unsupported ideas as hypotheses rather than findings.",
        bullets: [
          "Taxonomy-aware classification with emerging-theme governance",
          "Every synthesized claim carries its supporting evidence IDs",
          "Gate 2 supports approve, edit, reject, or investigate more",
        ],
      },
      {
        id: "act",
        eyebrow: "ACT",
        title: "Route reviewed insight into accountable work.",
        body:
          "Approved insights become action drafts with a business function, priority, owner-facing rationale, and impact window. Human edits remain explicit, so the system can compare its proposal with the final decision without rewriting history.",
        bullets: [
          "Deterministic priority matrix keeps scoring inspectable",
          "Gate 3 records overrides while preserving the original proposal",
          "Impact checks close the loop with before-and-after evidence",
        ],
      },
      {
        id: "control",
        eyebrow: "Control plane",
        title: "Three gates, one audit trail, no invisible handoff.",
        body:
          "Decision logs connect source mapping, insight review, and action approval. That continuity is the product: a calm record of what the system suggested, what a person changed, and what happened next.",
        link: { label: "Read the workflow guide", href: "/docs#workflow" },
      },
    ],
  },
  {
    href: "/company",
    navLabel: "Company",
    eyebrow: "Why the nest exists",
    title: "AI feedback deserves more than another dashboard.",
    description:
      "Happynest began as an undergraduate thesis about aggregating, classifying, and detecting problems in feedback about AI products. The project asks a practical question: can automation increase clarity without removing human judgment?",
    sections: [
      {
        id: "origin",
        eyebrow: "Origin",
        title: "Built from the realities of mixed-language product feedback.",
        body:
          "Vietnamese teams rarely receive tidy, single-language datasets. A support ticket may switch languages mid-sentence, carry screenshots, or hide the real issue beneath frustration. Happynest treats that mess as the starting condition, not an edge case.",
      },
      {
        id: "evidence-before-elegance",
        eyebrow: "Principle 01",
        title: "Evidence before elegance.",
        body:
          "A polished paragraph is not automatically an insight. The system is designed to preserve evidence IDs, distinguish findings from hypotheses, and ask for more investigation when the available signals do not justify a confident conclusion.",
      },
      {
        id: "human-review",
        eyebrow: "Principle 02",
        title: "Human review is a product surface, not a disclaimer.",
        body:
          "Review appears at the decisions that change meaning: source mapping, synthesized insight, and proposed action. Approvals, edits, rejections, and overrides become durable product data instead of disappearing inside chat history.",
      },
      {
        id: "constraints",
        eyebrow: "Constraint-led",
        title: "Designed to run within a student project’s real limits.",
        body:
          "The architecture targets an 8 GB development machine and an inexpensive VPS, using managed PostgreSQL and explicit budget caps. Those constraints encourage smaller models, deterministic analytics, and fewer wasteful agent loops.",
      },
    ],
  },
  {
    href: "/blog",
    navLabel: "Field notes",
    eyebrow: "From the build log",
    title: "Notes on evidence, language, and human control.",
    description:
      "A working notebook from the Happynest thesis: architecture decisions, evaluation questions, and practical lessons from building a bilingual Voice-of-Customer agent under tight compute and budget constraints.",
    sections: [
      {
        id: "fluent-summary",
        eyebrow: "Field note · 01",
        title: "Why a fluent summary can still be a weak insight.",
        body:
          "LLMs make synthesis feel finished before the evidence is ready. This note explains the finding-versus-hypothesis split, evidence whitelisting, and why the evaluator can send an investigation back to planning instead of rewarding confident prose.",
        link: { label: "See the evidence model", href: "/product#understand" },
      },
      {
        id: "code-switching",
        eyebrow: "Field note · 02",
        title: "Code-switching is not dirty data.",
        body:
          "Vietnamese–English feedback often carries the exact vocabulary a product team uses internally. Normalizing it away can erase intent. The pipeline keeps multilingual text, sanitizes PII, and classifies against a governed taxonomy without forcing translation first.",
        link: { label: "Read the input guide", href: "/docs#import" },
      },
      {
        id: "review-records",
        eyebrow: "Field note · 03",
        title: "What a useful human-in-the-loop gate records.",
        body:
          "A binary approve button is not enough. Useful review data includes the proposed value, the final human value, the reason for change, the time spent, and the evidence available at that moment. Those records make agreement and latency measurable.",
        link: { label: "Explore the review loop", href: "/qna#review" },
      },
      {
        id: "small-machine",
        eyebrow: "Field note · 04",
        title: "Small-machine architecture is a design discipline.",
        body:
          "A limited machine pushes work toward bounded context, reusable embeddings, deterministic SQL analytics, and visible model-call budgets. The result is easier to explain in a thesis and often easier to operate in production-shaped environments.",
      },
    ],
  },
  {
    href: "/docs",
    navLabel: "Docs",
    eyebrow: "Working guide",
    title: "From first import to reviewed action.",
    description:
      "A concise guide to the Happynest workflow. The current build is a thesis prototype, so these docs focus on the concrete path through products, imports, analysis, evidence review, and action approval.",
    sections: [
      {
        id: "product",
        eyebrow: "01 · Product",
        title: "Start with the product whose feedback you want to understand.",
        body:
          "Products are the top-level context. Source schemas, taxonomies, imports, insights, and actions stay attached to a product so an analyst can reason about one vocabulary and customer surface at a time.",
        bullets: [
          "Choose or create a product context",
          "Confirm the taxonomy matches that product’s language",
          "Keep separate products separate instead of mixing feedback pools",
        ],
      },
      {
        id: "import",
        eyebrow: "02 · Import",
        title: "Upload a CSV and approve the proposed mapping.",
        body:
          "Happynest profiles the file and proposes how source columns map to feedback text, timestamps, identity fields, and metadata. Inspect coverage and examples before approving Gate 1; the mapping becomes a reusable schema version.",
        bullets: [
          "Never upload secrets or credentials as feedback content",
          "Review timestamp and text-column coverage first",
          "Reject or edit mappings that would merge unrelated fields",
        ],
      },
      {
        id: "workflow",
        eyebrow: "03 · Workflow",
        title: "Run UNDERSTAND and inspect the evidence packet.",
        body:
          "The agent selects bounded analytics tools, collects evidence, evaluates coverage, and synthesizes a finding or hypothesis. At Gate 2, approve, edit, reject, or request more investigation; edits are sanitized again before storage.",
        bullets: [
          "Open cited feedback before accepting a broad claim",
          "Use investigate more when coverage is narrow or contradictory",
          "Keep edit reasons specific enough to improve later evaluation",
        ],
      },
      {
        id: "action",
        eyebrow: "04 · Action",
        title: "Approve ownership and priority, then measure what changed.",
        body:
          "ACT proposes a business function, action text, and priority from a deterministic matrix. Gate 3 preserves both the proposal and any human override. Impact checks later compare the affected context before and after the decision window.",
        link: { label: "Open the product", href: "/login" },
      },
    ],
  },
  {
    href: "/qna",
    navLabel: "Q&A",
    eyebrow: "Questions, answered plainly",
    title: "What Happynest does—and where people stay in control.",
    description:
      "Answers for product managers, operations teams, and thesis reviewers evaluating what the system automates, how evidence is handled, and which claims still require careful human judgment.",
    sections: [
      {
        id: "scope",
        eyebrow: "Scope",
        title: "Is Happynest a customer-support chatbot?",
        body:
          "No. It does not answer customers or send messages on a team’s behalf. Happynest analyzes feedback that a team has already collected, then helps people review evidence, decide what it means, and turn approved insight into internal action.",
      },
      {
        id: "language",
        eyebrow: "Language",
        title: "Can it work with Vietnamese and English in the same dataset?",
        body:
          "Yes—that is a core design assumption. The sanitizer and classification workflow account for Vietnamese, English, and code-switched phrases. Quality still depends on source coverage and taxonomy fit, so bilingual support does not remove the need for review.",
      },
      {
        id: "review",
        eyebrow: "Review",
        title: "Where does a human make decisions?",
        body:
          "Gate 1 approves source mapping, Gate 2 approves or revises an evidence-backed insight, and Gate 3 approves or overrides the proposed action. Each gate records the system proposal and the human outcome for later evaluation.",
      },
      {
        id: "privacy",
        eyebrow: "Privacy",
        title: "Does raw feedback go directly to the language model?",
        body:
          "The intended boundary is no: raw content is sanitized for emails, URLs, IP addresses, Vietnamese phone numbers, citizen identifiers, and recognized names before model calls, logs, or traces. No automated detector is perfect, so operators must still minimize sensitive source data.",
      },
      {
        id: "readiness",
        eyebrow: "Readiness",
        title: "Is this a production service?",
        body:
          "It is an undergraduate thesis prototype with production-shaped architecture, not a commercial service commitment. The repository includes real authentication, managed PostgreSQL, audit logs, and tests, while deployment hardening and formal legal review remain separate work.",
      },
    ],
  },
  {
    href: "/legal",
    navLabel: "Legal",
    eyebrow: "Prototype terms",
    title: "Clear boundaries for a research-stage system.",
    description:
      "Happynest is an undergraduate thesis prototype. This page explains the project’s current data-handling intent and acceptable-use boundaries; it is not a substitute for organization-specific legal, privacy, or security review.",
    sections: [
      {
        id: "privacy",
        eyebrow: "Privacy",
        title: "Submit only feedback you are authorized to process.",
        body:
          "Operators are responsible for obtaining the permissions required for imported feedback. Avoid uploading credentials, health data, financial data, or other unnecessary sensitive information. The sanitizer reduces exposure risk but cannot guarantee detection of every identifier.",
      },
      {
        id: "data-path",
        eyebrow: "Data path",
        title: "Sanitized content crosses the model boundary.",
        body:
          "The application is designed so raw feedback stays outside prompts, traces, durable model-call logs, test fixtures, and documentation. Sanitized placeholders may be sent to the configured language-model and embedding providers according to the operator’s environment settings.",
      },
      {
        id: "acceptable-use",
        eyebrow: "Acceptable use",
        title: "Keep high-impact decisions with accountable people.",
        body:
          "Do not use prototype output as the sole basis for employment, credit, healthcare, legal, safety, or other high-impact decisions. Findings can be incomplete or wrong; reviewers should inspect evidence and document meaningful corrections.",
      },
      {
        id: "no-warranty",
        eyebrow: "No warranty",
        title: "Research software is provided without service guarantees.",
        body:
          "Availability, retention, model behavior, and external provider access may change during development. Before real organizational use, complete a security review, define retention and deletion procedures, confirm processor agreements, and replace development credentials.",
        link: { label: "Review common questions", href: "/qna" },
      },
    ],
  },
] as const;

export function getMarketingPage(href: string): MarketingPage {
  const page = MARKETING_PAGES.find((entry) => entry.href === href);
  if (!page) throw new Error(`Unknown marketing page: ${href}`);
  return page;
}
