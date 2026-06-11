"use client";

import { useEffect, useState } from "react";

interface TickerOpts {
  step?: number;
  every?: number;
  spread?: number;
}

// Slowly-incrementing counter for "live" KPI numbers in the hero + dashboard
// mockups. Pure cosmetic — adds gentle entropy so the numbers feel alive.
export function useTicker(start: number, { step = 1, every = 2400, spread = 2 }: TickerOpts = {}) {
  const [n, setN] = useState(start);
  useEffect(() => {
    const id = setInterval(() => {
      setN((v) => v + step * (1 + Math.floor(Math.random() * spread)));
    }, every);
    return () => clearInterval(id);
  }, [step, every, spread]);
  return n;
}
