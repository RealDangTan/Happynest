import type { Metadata } from "next";
import "./landing/landing.css";
import { silkscreen } from "./landing/fonts";
import { BirdSvg, SignalField } from "./landing/motion";

export const metadata: Metadata = {
  title: "404 — Happynest",
};

export default function NotFound() {
  return (
    <div className={`${silkscreen.variable} hn`}>
      <main className="hn-vignette hn-grain relative flex min-h-screen items-center justify-center py-16">
        <SignalField />
        <div
          className="hn-enter relative mx-4 text-center"
          style={{ "--d": "0.1s" } as React.CSSProperties}
        >
          <p className="hn-eyebrow">Signal lost</p>
          <p className="hn-pixel mt-6 text-6xl tracking-widest text-[var(--hn-gold)] md:text-8xl">
            404
          </p>
          <div className="relative mt-6 inline-block" aria-hidden>
            <BirdSvg size={40} />
            <svg
              width="56"
              height="20"
              viewBox="0 0 14 5"
              shapeRendering="crispEdges"
              className="mx-auto -mt-1"
            >
              <rect x="1" y="0" width="12" height="2" fill="var(--hn-olive)" />
              <rect x="2" y="2" width="10" height="2" fill="var(--hn-olive)" opacity="0.7" />
              <rect x="3" y="4" width="8" height="1" fill="var(--hn-olive)" opacity="0.4" />
            </svg>
          </div>
          <h1 className="hn-display mt-6 text-2xl font-semibold md:text-3xl">
            This branch has no nest yet.
          </h1>
          <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-[var(--hn-stone)]">
            The page you&apos;re after drifted out of the canopy. The signal dots are
            already searching for it.
          </p>
          <a href="/" className="hn-btn mt-8 inline-flex">
            Back to the nest
          </a>
        </div>
      </main>
    </div>
  );
}
