"use client";

import { useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { clsx } from "clsx";

interface OverlayProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  /** "bottom" = compact partial-height slide-up sheet. "center" = centered modal. */
  slideFrom?: "bottom" | "center";
  ariaLabel: string;
}

export function Overlay({ open, onClose, children, slideFrom = "center", ariaLabel }: OverlayProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
          <motion.div
            className="absolute inset-0 bg-black/50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={ariaLabel}
            className={clsx(
              "relative z-10 w-full bg-card border border-hairline shadow-xl",
              slideFrom === "bottom"
                ? "max-w-lg rounded-t-2xl sm:rounded-2xl max-h-[70vh] overflow-y-auto"
                : "max-w-md rounded-2xl m-4 max-h-[85vh] overflow-y-auto",
            )}
            initial={
              slideFrom === "bottom" ? { y: "100%", opacity: 1 } : { opacity: 0, scale: 0.96 }
            }
            animate={slideFrom === "bottom" ? { y: 0, opacity: 1 } : { opacity: 1, scale: 1 }}
            exit={
              slideFrom === "bottom" ? { y: "100%", opacity: 1 } : { opacity: 0, scale: 0.96 }
            }
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
          >
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
