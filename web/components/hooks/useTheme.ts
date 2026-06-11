"use client";

import { useEffect, useState } from "react";

export type Theme = "dark" | "paper";

// Theme state with localStorage persistence under `sg-theme`. Default = dark
// (per designer's prototype). The page root reads this and applies
// `.theme-dark` / `.theme-paper` to drive the CSS token swap.
export function useTheme() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const stored = localStorage.getItem("sg-theme");
    if (stored === "dark" || stored === "paper") setTheme(stored);
  }, []);

  useEffect(() => {
    localStorage.setItem("sg-theme", theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === "dark" ? "paper" : "dark"));
  return { theme, toggle };
}
