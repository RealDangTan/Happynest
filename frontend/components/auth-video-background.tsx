"use client";
import { useEffect, useRef } from "react";

export function AuthVideoBackground() {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (video) video.playbackRate = 0.65;
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <video
        ref={videoRef}
        className="h-full w-full object-cover motion-reduce:hidden"
        src="/assets/background-hero.webm"
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
      />
      <div className="absolute inset-0 bg-black/30 motion-reduce:hidden" />
    </div>
  );
}
