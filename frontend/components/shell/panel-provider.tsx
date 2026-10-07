"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

const STORAGE_KEY = "happynest.panel.collapsed";

type PanelContextValue = {
  collapsed: boolean;
  toggle: () => void;
  setCollapsed: (v: boolean) => void;
  mobileOpen: boolean;
  setMobileOpen: (v: boolean) => void;
};

const PanelContext = createContext<PanelContextValue | null>(null);

export function PanelProvider({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsedState] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time localStorage read after hydration
    setCollapsedState(localStorage.getItem(STORAGE_KEY) === "1");
  }, []);

  const setCollapsed = useCallback((v: boolean) => {
    setCollapsedState(v);
    localStorage.setItem(STORAGE_KEY, v ? "1" : "0");
  }, []);

  const toggle = useCallback(() => setCollapsed(!collapsed), [collapsed, setCollapsed]);

  return (
    <PanelContext.Provider
      value={{ collapsed, toggle, setCollapsed, mobileOpen, setMobileOpen }}
    >
      {children}
    </PanelContext.Provider>
  );
}

export function usePanel(): PanelContextValue {
  const ctx = useContext(PanelContext);
  if (!ctx) throw new Error("usePanel must be used inside PanelProvider");
  return ctx;
}
