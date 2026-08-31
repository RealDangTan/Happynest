import type { Metadata } from "next";
import "./landing.css";
import { lora, silkscreen } from "./fonts";
import {
  BirdSvg,
  ConfidenceRing,
  CountUp,
  HeroVideo,
  LandingNav,
  PublicFooter,
  Reveal,
  SignalField,
} from "./motion";

export const metadata: Metadata = {
  title: "Happynest — Where feedback finds a home",
  description:
    "Happynest aggregates user feedback about AI products, classifies and clusters it into evidence-backed insights, and puts a human in the loop before anything becomes action.",
};

function SteppedConnector({ delay }: { delay: string }) {
  return (
    <svg
      className="hn-connector hidden lg:block"
      width="56"
      height="24"
      viewBox="0 0 56 24"
      fill="none"
      aria-hidden
    >
      <path
        className="hn-drawline"
        style={{ "--len": 90, "--dd": delay } as React.CSSProperties}
        d="M0 20 H18 V4 H38 V12 H56"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="4 4"
      />
    </svg>
  );
}

const PIPE_STEPS = [
  { label: "Signal", desc: "Raw feedback flows in from every channel." },
  { label: "Insight", desc: "Clusters and trends surface on their own." },
  { label: "Evidence", desc: "Every claim links back to its signals." },
  { label: "Human review", desc: "Nothing ships without a person's OK." },
  { label: "Action", desc: "Approved insights become work." },
];

function Pipeline() {
  return (
    <section id="how-it-works" className="bg-[var(--hn-charcoal)] py-24">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal>
          <p className="hn-eyebrow">The loop</p>
          <h2 className="hn-display mt-3 text-3xl font-semibold md:text-4xl">
            From noise to action, one loop.
          </h2>
        </Reveal>

        <Reveal className="mt-12">
          <ol className="flex flex-col items-stretch gap-6 lg:flex-row lg:items-start lg:gap-0">
            {PIPE_STEPS.map((step, i) => (
              <li key={step.label} className="contents">
                {i > 0 && (
                  <div className="hidden justify-center pt-10 lg:flex">
                    <SteppedConnector delay={`${0.2 + i * 0.2}s`} />
                  </div>
                )}
                <div className="hn-card hn-pipe flex-1 p-5">
                  <div className="flex h-12 items-center">
                    {i === 0 && (
                      <div className="hn-cluster" aria-hidden>
                        <i style={{ "--x": "2px", "--y": "30px" } as React.CSSProperties} />
                        <i style={{ "--x": "40px", "--y": "6px" } as React.CSSProperties} />
                        <i style={{ "--x": "36px", "--y": "38px" } as React.CSSProperties} />
                        <i style={{ "--x": "6px", "--y": "8px" } as React.CSSProperties} />
                        <i style={{ "--x": "24px", "--y": "20px" } as React.CSSProperties} />
                      </div>
                    )}
                    {i === 1 && <ConfidenceRing value={87} size={48} />}
                    {i === 2 && (
                      <div className="hn-evidence" aria-hidden>
                        <i />
                      </div>
                    )}
                    {i === 3 && (
                      <div className="flex flex-col gap-1.5" aria-hidden>
                        <span className="hn-check">
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                            <path d="M2 6 L5 9 L10 3" strokeWidth="2" />
                          </svg>
                        </span>
                        <span className="hn-check">
                          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                            <path d="M2 6 L5 9 L10 3" strokeWidth="2" />
                          </svg>
                        </span>
                      </div>
                    )}
                    {i === 4 && (
                      <span className="hn-stamp hn-pixel">APPROVED</span>
                    )}
                  </div>
                  <p className="hn-pixel mt-4 text-[11px] uppercase tracking-widest text-[var(--hn-soft)]">
                    {step.label}
                  </p>
                  <p className="mt-1 text-sm text-[var(--hn-stone)]">{step.desc}</p>
                </div>
              </li>
            ))}
          </ol>
        </Reveal>
      </div>
    </section>
  );
}

const MARQUEE_ROW_1 = [
  { text: "đăng nhập lỗi hoài 😤", tag: "Bug" },
  { text: "Loving the new dashboard ✨", tag: "Praise" },
  { text: "cho xin bản export CSV đi", tag: "Request" },
  { text: "app nặng quá, máy nóng", tag: "Bug" },
  { text: "onboarding was smooth", tag: "Praise" },
  { text: "muốn tích hợp Slack", tag: "Request" },
  { text: "response time is night and day", tag: "Praise" },
  { text: "biểu đồ bị sai số liệu tuần trước", tag: "Bug" },
];

const MARQUEE_ROW_2 = [
  { text: "please add dark mode", tag: "Request" },
  { text: "cảm ơn team hỗ trợ nhanh", tag: "Praise" },
  { text: "crashed when uploading 10k rows", tag: "Bug" },
  { text: "the summaries are scarily accurate", tag: "Praise" },
  { text: "tính năng gán tag tự động hay đó", tag: "Praise" },
  { text: "logo bị vỡ trên màn hình nhỏ", tag: "Bug" },
  { text: "integracja with Notion?", tag: "Request" },
  { text: "email thông báo trễ 2 tiếng", tag: "Bug" },
];

function ChipRow({ items, reverse }: { items: typeof MARQUEE_ROW_1; reverse?: boolean }) {
  const doubled = [...items, ...items];
  return (
    <div className={`hn-marquee-row ${reverse ? "hn-marquee-rev" : ""}`}>
      <div className="hn-marquee py-2">
        {doubled.map((chip, i) => (
          <span
            key={i}
            className="hn-chip"
            style={{ "--d": `${(i % items.length) * 0.9}s` } as React.CSSProperties}
          >
            {chip.text}
            <span className="hn-chip-tag">{chip.tag}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function Marquee() {
  return (
    <section id="signals" className="py-24">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal>
          <p className="hn-eyebrow">Live classify</p>
          <h2 className="hn-display mt-3 text-3xl font-semibold md:text-4xl">
            What Happynest hears.
          </h2>
          <p className="mt-3 max-w-xl text-[var(--hn-stone)]">
            Vietnamese, English, or both in one sentence — every piece of feedback
            lands, gets read, and finds its category. PII never leaves the nest.
          </p>
        </Reveal>
      </div>
      <Reveal className="mt-10 flex flex-col gap-2">
        <ChipRow items={MARQUEE_ROW_1} />
        <ChipRow items={MARQUEE_ROW_2} reverse />
      </Reveal>
    </section>
  );
}

function NestIllustration() {
  return (
    <svg width="56" height="48" viewBox="0 0 14 12" shapeRendering="crispEdges" aria-hidden>
      <g className="hn-feat-group">
        <rect x="5" y="1" width="4" height="3" fill="var(--hn-ivory)" />
        <rect x="6" y="2" width="1" height="1" className="hn-eye" fill="var(--hn-deep)" />
        <rect x="9" y="2" width="1" height="1" fill="var(--hn-gold)" />
        <rect x="3" y="4" width="8" height="3" fill="var(--hn-ivory)" />
        <rect x="2" y="7" width="10" height="2" fill="var(--hn-olive)" />
        <rect x="3" y="9" width="8" height="2" fill="var(--hn-olive)" opacity="0.7" />
        <rect x="4" y="11" width="6" height="1" fill="var(--hn-olive)" opacity="0.4" />
      </g>
    </svg>
  );
}

function LanternIllustration() {
  return (
    <svg width="56" height="48" viewBox="0 0 14 12" shapeRendering="crispEdges" aria-hidden>
      <circle className="hn-glow" cx="7" cy="7" r="5" fill="var(--hn-gold)" opacity="0.5" />
      <rect x="5" y="1" width="4" height="1" fill="var(--hn-stone)" />
      <rect x="4" y="2" width="6" height="1" fill="var(--hn-olive)" />
      <rect x="5" y="3" width="4" height="6" fill="var(--hn-gold)" />
      <rect x="6" y="5" width="2" height="2" fill="var(--hn-ivory)" />
      <rect x="4" y="9" width="6" height="1" fill="var(--hn-olive)" />
    </svg>
  );
}

function ClipboardIllustration() {
  return (
    <svg width="56" height="48" viewBox="0 0 14 12" shapeRendering="crispEdges" aria-hidden>
      <rect x="3" y="1" width="8" height="10" fill="none" stroke="var(--hn-olive)" strokeWidth="1" />
      <rect x="5" y="0" width="4" height="2" fill="var(--hn-stone)" />
      <rect x="5" y="4" width="4" height="1" fill="var(--hn-stone)" opacity="0.6" />
      <rect x="5" y="6" width="3" height="1" fill="var(--hn-stone)" opacity="0.6" />
      <path
        className="hn-clipcheck"
        d="M5 9 L7 11 L11 6"
        stroke="var(--hn-gold)"
        strokeWidth="1.5"
        fill="none"
      />
    </svg>
  );
}

const FEATURES = [
  {
    title: "Warm intelligence",
    desc: "Clustering and trend detection that read the room, not just the count. Code-switching Vietnamese–English included.",
    art: <NestIllustration />,
  },
  {
    title: "Calm clarity",
    desc: "Evidence-backed summaries. Every insight links back to the exact signals that earned it — no black boxes.",
    art: <LanternIllustration />,
  },
  {
    title: "Human control",
    desc: "Nothing ships without review. A human signs off in the loop, and corrections make the model smarter.",
    art: <ClipboardIllustration />,
  },
];

function Features() {
  return (
    <section id="why" className="bg-[var(--hn-charcoal)] py-24">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal>
          <p className="hn-eyebrow">Why Happynest</p>
          <h2 className="hn-display mt-3 text-3xl font-semibold md:text-4xl">
            Warm intelligence. Calm clarity. Human control.
          </h2>
        </Reveal>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={i * 100}>
              <div className="hn-card hn-feat h-full p-6">
                <div className="flex h-14 items-end">{f.art}</div>
                <h3 className="hn-display mt-5 text-xl font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--hn-stone)]">
                  {f.desc}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const SOURCES = [
  ["App reviews", "rating + release"],
  ["Support", "ticket + queue"],
  ["Surveys", "score + response"],
  ["Email", "thread + timestamp"],
  ["In-product", "event + context"],
  ["CSV exports", "your schema"],
] as const;

function Sources() {
  return (
    <section id="sources" className="py-24 md:py-32">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
        <Reveal>
          <p className="hn-eyebrow">Source intelligence</p>
          <h2 className="hn-display mt-4 text-3xl font-semibold md:text-4xl">
            Every channel speaks a different dialect.
          </h2>
          <p className="mt-5 max-w-xl leading-relaxed text-[var(--hn-stone)]">
            Happynest profiles each import, proposes a reusable source schema, and
            shows its coverage before anything enters analysis. You approve the map;
            the system remembers the structure.
          </p>
          <a href="/docs#import" className="hn-link mt-7 inline-flex text-sm">
            Read the import guide →
          </a>
        </Reveal>
        <Reveal delay={120}>
          <div className="hn-source-grid">
            {SOURCES.map(([name, meta], index) => (
              <article key={name} className="hn-source-cell">
                <span className="hn-pixel text-[10px] text-[var(--hn-gold)]">
                  {(index + 1).toString().padStart(2, "0")}
                </span>
                <h3 className="hn-display mt-4 text-xl font-semibold">{name}</h3>
                <p className="mt-2 text-sm text-[var(--hn-stone)]">{meta}</p>
              </article>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function EvidenceAnatomy() {
  return (
    <section id="evidence" className="bg-[var(--hn-charcoal)] py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal>
          <p className="hn-eyebrow">Inside one insight</p>
          <h2 className="hn-display mt-4 max-w-3xl text-3xl font-semibold md:text-4xl">
            A claim is only as useful as the trail behind it.
          </h2>
        </Reveal>
        <div className="mt-12 grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <Reveal>
            <article className="hn-insight-card">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <span className="hn-pixel text-[10px] text-[var(--hn-soft)]">
                  FINDING · REVIEW READY
                </span>
                <ConfidenceRing value={87} size={52} />
              </div>
              <h3 className="hn-display mt-8 text-2xl font-semibold md:text-3xl">
                Upload failures concentrate on older Android devices after the latest release.
              </h3>
              <p className="mt-5 leading-relaxed text-[var(--hn-stone)]">
                The statement stays paired with scope, time window, confidence, and
                evidence IDs. If support is weak or contradictory, it remains a
                hypothesis instead of being polished into certainty.
              </p>
              <div className="hn-evidence-meta mt-8">
                <span>WINDOW · 14 DAYS</span>
                <span>SIGNALS · 38</span>
                <span>SOURCES · 3</span>
              </div>
            </article>
          </Reveal>
          <Reveal delay={120}>
            <ol className="hn-trace-list">
              {[
                ["01", "App review", "Crash after selecting a large file", "Android 11"],
                ["02", "Support", "Upload reaches 82%, then returns to start", "Ticket queue"],
                ["03", "In-product", "Repeated upload_error after release 2.4", "Event context"],
              ].map(([id, source, quote, meta]) => (
                <li key={id} className="hn-trace-item">
                  <span className="hn-pixel text-[10px] text-[var(--hn-gold)]">{id}</span>
                  <div>
                    <p className="text-sm text-[var(--hn-ivory)]">{quote}</p>
                    <p className="mt-2 text-xs text-[var(--hn-stone)]">
                      {source} · {meta}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

const GATES = [
  {
    gate: "GATE 1",
    title: "Approve meaning",
    body: "Confirm how an imported source maps its text, time, identity, and metadata before analysis begins.",
  },
  {
    gate: "GATE 2",
    title: "Approve insight",
    body: "Inspect cited evidence, edit the synthesis, reject it, or send the agent back to investigate more.",
  },
  {
    gate: "GATE 3",
    title: "Approve action",
    body: "Keep or override the proposed owner and priority while preserving the system’s original recommendation.",
  },
] as const;

function HumanGates() {
  return (
    <section id="human-gates" className="py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal className="grid gap-6 lg:grid-cols-2 lg:items-end">
          <div>
            <p className="hn-eyebrow">Human by design</p>
            <h2 className="hn-display mt-4 text-3xl font-semibold md:text-4xl">
              Automation moves the work. People move the meaning.
            </h2>
          </div>
          <p className="max-w-xl leading-relaxed text-[var(--hn-stone)] lg:justify-self-end">
            Each gate records what the system proposed, what a reviewer decided,
            and why. Corrections become evaluation evidence rather than disappearing
            inside a chat transcript.
          </p>
        </Reveal>
        <div className="mt-12 grid gap-px bg-[var(--hn-olive)] lg:grid-cols-3">
          {GATES.map((gate, index) => (
            <Reveal key={gate.gate} delay={index * 90}>
              <article className="hn-gate h-full">
                <span className="hn-pixel text-[10px] text-[var(--hn-gold)]">{gate.gate}</span>
                <h3 className="hn-display mt-6 text-2xl font-semibold">{gate.title}</h3>
                <p className="mt-4 text-sm leading-relaxed text-[var(--hn-stone)]">
                  {gate.body}
                </p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Teams() {
  return (
    <section id="teams" className="bg-[var(--hn-charcoal)] py-24 md:py-32">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal>
          <p className="hn-eyebrow">One signal, several decisions</p>
          <h2 className="hn-display mt-4 text-3xl font-semibold md:text-4xl">
            Clarity travels farther than a report.
          </h2>
        </Reveal>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {[
            ["Product", "See recurring friction with scope, severity, and customer language attached."],
            ["Operations", "Review source quality, route accountable action, and keep decision latency visible."],
            ["AI quality", "Track safety signals, model-behavior complaints, and taxonomy drift over time."],
          ].map(([role, outcome], index) => (
            <Reveal key={role} delay={index * 90}>
              <article className="hn-role-card h-full">
                <span className="hn-pixel text-[10px] text-[var(--hn-soft)]">FOR {role.toUpperCase()}</span>
                <h3 className="hn-display mt-8 text-2xl font-semibold">{role}</h3>
                <p className="mt-4 leading-relaxed text-[var(--hn-stone)]">{outcome}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Questions() {
  const questions = [
    ["Does raw feedback go to the model?", "The intended boundary sanitizes PII before prompts, traces, or durable model-call logs."],
    ["What happens when evidence is weak?", "The system can label a synthesis as a hypothesis or loop back to investigate more."],
    ["Can it read Vietnamese and English together?", "Yes. Mixed-language and code-switched feedback are core design assumptions."],
    ["Is this a production service?", "It is a production-shaped undergraduate thesis prototype, not a commercial service guarantee."],
  ] as const;

  return (
    <section id="questions" className="py-24 md:py-32">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 lg:grid-cols-[0.7fr_1.3fr]">
        <Reveal>
          <p className="hn-eyebrow">Questions worth asking</p>
          <h2 className="hn-display mt-4 text-3xl font-semibold md:text-4xl">
            Trust starts with clear limits.
          </h2>
          <a href="/qna" className="hn-link mt-7 inline-flex text-sm">
            Read all questions →
          </a>
        </Reveal>
        <Reveal delay={100}>
          <div className="hn-question-list">
            {questions.map(([question, answer]) => (
              <details key={question} className="hn-question">
                <summary className="hn-display text-xl font-semibold">{question}</summary>
                <p className="mt-4 max-w-2xl leading-relaxed text-[var(--hn-stone)]">{answer}</p>
              </details>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}

const STATS = [
  { to: 3, suffix: "", label: "human decision gates" },
  { to: 9, suffix: "", label: "bounded analytics tools" },
  { to: 1, suffix: "", label: "linked decision trail" },
];

function Proof() {
  return (
    <section id="proof" className="py-24">
      <div className="hn-divider mx-auto max-w-6xl" />
      <div className="mx-auto mt-16 grid max-w-6xl gap-10 px-4 md:grid-cols-2 md:items-center">
        <Reveal className="grid grid-cols-3 gap-6">
          {STATS.map((s) => (
            <div key={s.label}>
              <p className="hn-display text-3xl font-semibold text-[var(--hn-gold)] md:text-4xl">
                <CountUp to={s.to} suffix={s.suffix} />
              </p>
              <p className="mt-2 text-xs leading-relaxed text-[var(--hn-stone)]">
                {s.label}
              </p>
            </div>
          ))}
        </Reveal>
        <Reveal delay={150}>
          <figure className="hn-frame p-6">
            <span className="hn-tick hn-tick-tl" />
            <span className="hn-tick hn-tick-br" />
            <blockquote className="hn-display text-lg leading-relaxed">
              “The thesis is not that an agent should decide faster. It is that a
              team should see the evidence, intervention, and outcome in one place.”
            </blockquote>
            <figcaption className="mt-4 text-sm text-[var(--hn-stone)]">
              Happynest design principle · research prototype
            </figcaption>
          </figure>
        </Reveal>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="hn-vignette hn-grain bg-[var(--hn-charcoal)] py-28">
      <div className="relative mx-auto max-w-3xl px-4 text-center">
        <Reveal>
          <p className="hn-eyebrow">Open the nest</p>
          <h2 className="hn-display mt-4 text-4xl font-semibold md:text-5xl">
            Ready to give feedback a home?
          </h2>
          <p className="mt-4 text-[var(--hn-stone)]">
            Aggregate, classify, cluster — and keep the last word for humans.
          </p>
          <div className="mt-8">
            <span className="hn-fly">
              <BirdSvg size={28} />
            </span>
          </div>
          <a href="/login" className="hn-btn mt-6 inline-flex">
            Open the nest
          </a>
        </Reveal>
      </div>
    </section>
  );
}

export default function LandingPage() {
  return (
    <div className={`${silkscreen.variable} ${lora.variable} hn`}>
      <LandingNav />
      <main>
        <section className="hn-hero hn-vignette relative">
          <HeroVideo src="/assets/landing-hero.webm" />
          <div className="hn-hero-shade" aria-hidden />
          <SignalField />
          <div className="hn-hero-content relative mx-auto flex max-w-6xl items-end px-4">
            <div className="max-w-2xl pb-24 pt-28 md:pb-32">
              <p className="hn-eyebrow hn-enter" style={{ "--d": "0s" } as React.CSSProperties}>
                Feedback finds a home
              </p>
              <h1
                className="hn-hero-title hn-display hn-enter mt-5 font-semibold leading-tight"
                style={{ "--d": "0.12s" } as React.CSSProperties}
              >
                Where feedback finds a home, insights find clarity.
              </h1>
              <p
                className="hn-enter mt-6 max-w-lg leading-relaxed text-[var(--hn-stone)]"
                style={{ "--d": "0.24s" } as React.CSSProperties}
              >
                Happynest gathers what users say about your AI product, separates
                signal from noise, and carries traceable insight through three human
                decision gates.
              </p>
              <div
                className="hn-enter mt-8 flex flex-wrap gap-4"
                style={{ "--d": "0.36s" } as React.CSSProperties}
              >
                <a href="/login" className="hn-btn">
                  Start listening
                </a>
                <a href="#how-it-works" className="hn-btn-ghost">
                  See how it works ↓
                </a>
              </div>
              <p
                className="hn-enter hn-pixel mt-8 text-[10px] tracking-widest text-[var(--hn-stone)]"
                style={{ "--d": "0.48s" } as React.CSSProperties}
              >
                PII SANITIZED · EVIDENCE LINKED · HUMAN APPROVED
              </p>
            </div>
          </div>
        </section>

        <Pipeline />
        <Sources />
        <Marquee />
        <EvidenceAnatomy />
        <Features />
        <HumanGates />
        <Teams />
        <Proof />
        <Questions />
        <FinalCta />
      </main>
      <PublicFooter />
    </div>
  );
}
