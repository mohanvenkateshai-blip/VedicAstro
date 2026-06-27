"use client";

import { useTransition } from "react";
import { Trash2 } from "lucide-react";
import { deleteChart } from "@/lib/actions";

export function DeleteChartButton({ id }: { id: string }) {
  const [pending, startTransition] = useTransition();

  return (
    <button
      type="button"
      disabled={pending}
      aria-label="Delete saved chart"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!window.confirm("Delete this saved chart?")) return;
        startTransition(async () => {
          await deleteChart(id);
        });
      }}
      className="shrink-0 rounded-lg p-2 text-text-muted hover:text-danger hover:bg-danger/10 transition-colors disabled:opacity-50"
    >
      <Trash2 size={15} />
    </button>
  );
}
