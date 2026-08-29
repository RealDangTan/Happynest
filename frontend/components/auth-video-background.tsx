export function AuthVideoBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <video
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
