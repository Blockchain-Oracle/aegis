"use client";

import { useEffect } from "react";

// Reveal-on-scroll. Adds `.in` to any `.rv` element once it intersects the
// viewport. The `.reveal-on` class on <html> gates the initial hidden state
// so non-JS users still see content.
export function useReveal() {
  useEffect(() => {
    document.documentElement.classList.add("reveal-on");
    const els = document.querySelectorAll(".rv");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}
