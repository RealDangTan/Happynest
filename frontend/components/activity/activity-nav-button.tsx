"use client";

import { Activity, CheckCircle2, CircleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useActivity } from "./activity-provider";

export function ActivityNavButton() {
  const activity = useActivity();
  const label = `${activity.attentionCount} task(s) need review, ${activity.runningCount} running`;

  return (
    <Button
      variant="outline"
      size="sm"
      className="ml-auto rounded-full border-border/80 bg-card shadow-sm"
      aria-label={label}
      onClick={activity.openQueue}
    >
      {activity.state === "running" ? <Spinner data-icon="inline-start" /> : null}
      {activity.state === "failed" ? (
        <CircleAlert className="text-destructive" data-icon="inline-start" />
      ) : null}
      {activity.state === "completed" ? (
        <CheckCircle2 className="text-emerald-600" data-icon="inline-start" />
      ) : null}
      {["idle", "needs_attention"].includes(activity.state) ? (
        <Activity data-icon="inline-start" />
      ) : null}
      <span className="hidden sm:inline">Current tasks</span>
      {activity.state === "running" && activity.runningCount > 0 ? (
        <Badge variant="secondary">{activity.runningCount}</Badge>
      ) : activity.attentionCount > 0 ? (
        <Badge variant={activity.state === "failed" ? "destructive" : "default"}>
          {activity.attentionCount}
        </Badge>
      ) : null}
    </Button>
  );
}
