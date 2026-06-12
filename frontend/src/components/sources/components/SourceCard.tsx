/**
 * Source Card Component
 * Compact source item used in the left NotebookLM-style source list.
 */

import React, { memo } from "react";
import { FileText, Globe } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SourceCardProps } from "../types/source-panel-types";

const FILE_ICONS = {
  pdf: FileText,
  docx: FileText,
  web: Globe,
} as const;

export const SourceCard = memo<SourceCardProps>((props) => {
  const { group, index, isSelected, onExpand } = props;

  const Icon = (FILE_ICONS as any)[group.type] || FileText;
  const groupKey = group.document_id || group.title;

  return (
    <div
      id={`source-card-${groupKey}`}
      role="button"
      tabIndex={0}
      onClick={() => onExpand(groupKey)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onExpand(groupKey);
        }
      }}
      className={cn(
        "group w-full rounded-xl border bg-card p-3.5 transition-all duration-200 cursor-pointer",
        "hover:border-primary/30 hover:bg-muted/30",
        isSelected
          ? "border-primary/35 bg-primary/5 shadow-sm ring-1 ring-primary/15"
          : "border-border/60",
      )}
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 mt-0.5 w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center ring-1 ring-primary/10">
          <span className="text-xs font-semibold text-primary">
            {index + 1}
          </span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 min-w-0">
            <Icon className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            <h3 className="min-w-0 flex-1 text-sm font-medium truncate text-foreground leading-5">
              {group.title}
            </h3>
          </div>

          <div className="mt-2 flex items-center gap-1.5">
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
              {group.chunks.length} trích dẫn
            </span>
          </div>
        </div>
      </div>
    </div>
  );
});

SourceCard.displayName = "SourceCard";

export default SourceCard;
