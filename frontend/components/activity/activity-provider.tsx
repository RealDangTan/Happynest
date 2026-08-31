"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useImports } from "@/hooks/use-imports";
import { useRuns } from "@/hooks/use-analysis";
import type { ActivitySummary, ImportRecord, RunProgress } from "@/lib/types";
import { deriveActivitySummary, withActivityParam } from "@/lib/activity";
import { ActivitySheet } from "./activity-sheet";

type ActivityContextValue = ActivitySummary & {
  imports: ImportRecord[];
  runs: RunProgress[];
  activityParam: string | null;
  openQueue: () => void;
  openImport: (id: string) => void;
  openRun: (id: string) => void;
  closeActivity: () => void;
};

const ActivityContext = createContext<ActivityContextValue | null>(null);

export function ActivityProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const importsQuery = useImports();
  const runsQuery = useRuns();
  const activityParam = searchParams.get("activity");
  const imports = importsQuery.data?.items ?? [];
  const runs = runsQuery.data?.items ?? [];
  const [seenFailures, setSeenFailures] = useState("");
  const [completedUntil, setCompletedUntil] = useState(0);
  const previousRunning = useRef(0);
  const summary = deriveActivitySummary({
    imports,
    runs,
    seenFailures,
    completedRecently: Date.now() < completedUntil,
  });

  useEffect(() => {
    if (activityParam && summary.failedSignature) setSeenFailures(summary.failedSignature);
  }, [activityParam, summary.failedSignature]);

  useEffect(() => {
    if (previousRunning.current > summary.runningCount) setCompletedUntil(Date.now() + 8000);
    previousRunning.current = summary.runningCount;
  }, [summary.runningCount]);

  const setActivity = useCallback((value: string | null) => {
    const query = withActivityParam(searchParams.toString(), value);
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }, [pathname, router, searchParams]);

  const value = useMemo<ActivityContextValue>(() => {
    return {
      state: summary.state,
      attentionCount: summary.attentionCount,
      runningCount: summary.runningCount,
      primaryActivity: summary.primaryActivity,
      imports,
      runs,
      activityParam,
      openQueue: () => setActivity("queue"),
      openImport: (id) => setActivity(`import:${id}`),
      openRun: (id) => setActivity(`run:${id}`),
      closeActivity: () => setActivity(null),
    };
  }, [activityParam, imports, runs, setActivity, summary.attentionCount, summary.primaryActivity, summary.runningCount, summary.state]);

  return (
    <ActivityContext.Provider value={value}>
      {children}
      <ActivitySheet />
    </ActivityContext.Provider>
  );
}

export function useActivity() {
  const value = useContext(ActivityContext);
  if (!value) throw new Error("useActivity must be used inside ActivityProvider");
  return value;
}
