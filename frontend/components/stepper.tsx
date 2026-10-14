/** Linear step indicator (vd: File — Preview — Mapping — Result).
 * Dùng chung cho mọi wizard; bước trước `current` hiển thị như đã xong. */
export function Stepper({
  steps,
  current,
  label = "Steps",
}: {
  steps: readonly string[];
  current: string;
  label?: string;
}) {
  const index = steps.indexOf(current);
  return (
    <ol className="flex items-center gap-2 text-sm" aria-label={label}>
      {steps.map((step, i) => (
        <li key={step} className="flex items-center gap-2">
          <span
            className={
              i === index
                ? "font-semibold text-foreground"
                : i < index
                  ? "text-lichen"
                  : "text-muted-foreground"
            }
            aria-current={i === index ? "step" : undefined}
          >
            {step}
          </span>
          {i < steps.length - 1 ? (
            <span className="text-muted-foreground">—</span>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
