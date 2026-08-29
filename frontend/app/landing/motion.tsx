"use client";

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";

export function Reveal({
  children,
  className = "",
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("is-in");
          io.disconnect();
        }
      },
      { threshold: 0.2 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`hn-reveal ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

export function CountUp({
  to,
  suffix = "",
  duration = 1400,
}: {
  to: number;
  suffix?: string;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [val, setVal] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVal(to);
      return;
    }
    let raf = 0;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        io.disconnect();
        const start = performance.now();
        const tick = (t: number) => {
          const p = Math.min(1, (t - start) / duration);
          const eased = 1 - Math.pow(1 - p, 3);
          setVal(Math.round(to * eased));
          if (p < 1) raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
      },
      { threshold: 0.5 }
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [to, duration]);

  return (
    <span ref={ref}>
      {val.toLocaleString("en-US")}
      {suffix}
    </span>
  );
}

export function ConfidenceRing({ value = 87, size = 56 }: { value?: number; size?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [on, setOn] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        io.disconnect();
        if (reduce) setOn(true);
        else {
          // slight delay so the ring animates after the card reveal
          setTimeout(() => setOn(true), 300);
        }
      },
      { threshold: 0.5 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const stroke = 4;
  const r = (size - stroke * 2) / 2;
  const c = 2 * Math.PI * r;

  return (
    <div ref={ref} className="hn-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--hn-olive)"
          strokeWidth={stroke}
          opacity={0.35}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--hn-gold)"
          strokeWidth={stroke}
          strokeDasharray={c}
          strokeDashoffset={on ? c * (1 - value / 100) : c}
          style={{
            transition: "stroke-dashoffset 1.2s steps(16, end)",
            transform: "rotate(-90deg)",
            transformOrigin: "center",
          }}
        />
      </svg>
      <span className="hn-ring-label">{value}%</span>
    </div>
  );
}

const SIGNAL_DOTS: Array<{ "--x": string; "--y": string; "--d": string; "--dur": string }> = [
  { "--x": "4%", "--y": "88%", "--d": "0s", "--dur": "11s" },
  { "--x": "9%", "--y": "95%", "--d": "1.2s", "--dur": "9s" },
  { "--x": "14%", "--y": "90%", "--d": "2.4s", "--dur": "12s" },
  { "--x": "21%", "--y": "97%", "--d": "0.6s", "--dur": "10s" },
  { "--x": "27%", "--y": "92%", "--d": "3.1s", "--dur": "13s" },
  { "--x": "33%", "--y": "96%", "--d": "1.8s", "--dur": "9.5s" },
  { "--x": "39%", "--y": "89%", "--d": "4.2s", "--dur": "11.5s" },
  { "--x": "46%", "--y": "94%", "--d": "0.3s", "--dur": "10.5s" },
  { "--x": "52%", "--y": "91%", "--d": "2.9s", "--dur": "12.5s" },
  { "--x": "58%", "--y": "97%", "--d": "5s", "--dur": "9s" },
  { "--x": "64%", "--y": "90%", "--d": "1.5s", "--dur": "10s" },
  { "--x": "70%", "--y": "95%", "--d": "3.7s", "--dur": "12s" },
  { "--x": "76%", "--y": "92%", "--d": "0.9s", "--dur": "11s" },
  { "--x": "82%", "--y": "96%", "--d": "2.2s", "--dur": "9.8s" },
  { "--x": "88%", "--y": "89%", "--d": "4.6s", "--dur": "12.8s" },
  { "--x": "94%", "--y": "93%", "--d": "1.1s", "--dur": "10.2s" },
];

export function SignalField() {
  return (
    <div aria-hidden className="hn-signals">
      {SIGNAL_DOTS.map((dot, i) => (
        <i key={i} style={dot as CSSProperties} />
      ))}
    </div>
  );
}

export function BirdSvg({ size = 24, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 12 12"
      shapeRendering="crispEdges"
      aria-hidden
      className={className}
    >
      {/* tail */}
      <rect x="0" y="6" width="2" height="2" fill="var(--hn-olive)" />
      {/* body */}
      <rect x="2" y="4" width="6" height="5" fill="var(--hn-ivory)" />
      {/* head */}
      <rect x="7" y="2" width="3" height="3" fill="var(--hn-ivory)" />
      {/* eye */}
      <rect x="8" y="3" width="1" height="1" fill="var(--hn-deep)" />
      {/* beak */}
      <rect x="10" y="3" width="1" height="1" fill="var(--hn-gold)" />
      {/* wing */}
      <rect x="3" y="6" width="3" height="2" fill="var(--hn-stone)" />
    </svg>
  );
}

export function LandingNav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={`hn-nav ${scrolled ? "hn-nav-scrolled" : ""}`}>
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <a href="#" className="flex items-center gap-2">
          <BirdSvg size={20} />
          <span className="hn-pixel text-sm tracking-widest text-[var(--hn-ivory)]">
            happynest
          </span>
        </a>
        <div className="hidden items-center gap-6 md:flex">
          <a href="#how-it-works" className="hn-link text-sm">
            How it works
          </a>
          <a href="#signals" className="hn-link text-sm">
            Signals
          </a>
          <a href="#why" className="hn-link text-sm">
            Why Happynest
          </a>
          <a href="#proof" className="hn-link text-sm">
            Proof
          </a>
        </div>
        <a href="#" className="hn-btn !px-4 !py-2 text-sm">
          Open the nest
        </a>
      </nav>
    </header>
  );
}
