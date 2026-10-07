"use client";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

/**
 * The Chat segmented tab opens an inline chat panel over the workspace —
 * no route change. The panel stays mounted so a running investigation
 * keeps its thread while the user works elsewhere.
 */
type ChatContextValue = {
  chatOpen: boolean;
  /** Run opened from history (null = fresh chat). */
  activeRunId: string | null;
  /** Bumped on every openChat so the panel can reset its thread. */
  openSeq: number;
  openChat: (runId?: string | null) => void;
  closeChat: () => void;
};

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [chatOpen, setChatOpen] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [openSeq, setOpenSeq] = useState(0);

  const openChat = useCallback((runId: string | null = null) => {
    setActiveRunId(runId);
    setOpenSeq((n) => n + 1);
    setChatOpen(true);
  }, []);

  const closeChat = useCallback(() => setChatOpen(false), []);

  const value = useMemo(
    () => ({ chatOpen, activeRunId, openSeq, openChat, closeChat }),
    [chatOpen, activeRunId, openSeq, openChat, closeChat],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used inside ChatProvider");
  return ctx;
}
