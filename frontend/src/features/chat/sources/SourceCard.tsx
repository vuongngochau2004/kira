/**
 * Source Card Component
 * Compact source item used in the left NotebookLM-style source list.
 */

import React, { memo, useEffect, useRef } from "react";
import { ChevronDown, Eye, Quote } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SourceCardProps, SourceChunk } from "@/features/chat/sources/types";
import { LegalCitationMeta } from "@/features/legal/components/LegalCitationMeta";
import { SourceSummary } from "@/features/chat/sources/SourceSummary";

export const SourceCard = memo<SourceCardProps>((props) => {
  const { group, isSelected, activeSourceId, onExpand, onPreview } = props;
  const [expandedCitations, setExpandedCitations] = React.useState<Set<string>>(new Set());
  const activeCitationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isSelected && activeSourceId) {
      activeCitationRef.current?.scrollIntoView?.({ block: "nearest" });
    }
  }, [activeSourceId, isSelected]);

  const groupKey = group.document_id || group.title;
  const readableChunks = group.chunks.filter((chunk) => chunk.snippet?.trim());

  const toggleCitation = (citationKey: string) => {
    setExpandedCitations((current) => {
      const next = new Set(current);
      if (next.has(citationKey)) {
        next.delete(citationKey);
      } else {
        next.add(citationKey);
      }
      return next;
    });
  };

  return (
    <div
      id={`source-card-${groupKey}`}
      className={cn(
        "group w-full min-w-0 max-w-full overflow-hidden rounded-xl border bg-card p-3.5 transition-all duration-200",
        "hover:border-primary/30 hover:bg-muted/30",
        isSelected
          ? "border-primary/35 bg-primary/5 shadow-sm ring-1 ring-primary/15"
          : "border-border/60",
      )}
    >
      <div className="flex min-w-0 items-start">
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex min-w-0 items-start gap-2">
            <SourceSummary
              title={group.title}
              type={group.type}
              referenceCount={group.chunks.length}
              expanded={isSelected}
              onExpand={() => onExpand(groupKey)}
            />
            {group.document_id && (
              <button
                type="button"
                onClick={() => onPreview(group.document_id!, group.title)}
                className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-primary focus-visible:outline-2 focus-visible:outline-primary"
                aria-label={`Xem tài liệu gốc ${group.title}`}
                title="Xem tài liệu gốc"
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {isSelected && (
            <div className="space-y-2.5">
              {readableChunks.length > 0 ? (
                readableChunks.map((chunk, chunkIndex) => {
                  const citationKey = chunk.id || `${groupKey}-${chunkIndex}`;
                  const isCitationExpanded = expandedCitations.has(citationKey);
                  const isActive = citationKey === activeSourceId;

                  return (
                    <div
                      key={citationKey}
                      ref={isActive ? activeCitationRef : undefined}
                      className={cn("group/citation rounded-lg border p-3 transition-colors hover:border-primary/30 hover:bg-muted/30", isActive ? "border-primary bg-primary/10" : "border-border/60 bg-muted/20")}
                    >
                      <div className="flex items-center gap-2">
                        <button type="button" onClick={() => toggleCitation(citationKey)} aria-expanded={isCitationExpanded || isActive} aria-label={`${isCitationExpanded || isActive ? "Đóng" : "Mở"} trích dẫn ${chunkIndex + 1}${chunk.page !== undefined ? `, trang ${chunk.page}` : ""}`} className="flex min-w-0 flex-1 items-center gap-1.5 text-left text-[10px] font-medium uppercase tracking-wide text-muted-foreground focus-visible:outline-2 focus-visible:outline-primary">
                          <Quote className="w-3 h-3 shrink-0" />
                          <span className="truncate">
                            Trích dẫn {chunkIndex + 1}
                          </span>
                          {chunk.page !== undefined && <span>· Trang {chunk.page}</span>}
                          <ChevronDown className={cn("ml-auto w-3.5 h-3.5 shrink-0 transition-transform", (isCitationExpanded || isActive) && "rotate-180 text-primary")} aria-hidden="true" />
                        </button>
                        {chunk.legal && <LegalCitationMeta legal={chunk.legal} />}
                      </div>

                      {(isCitationExpanded || isActive) && (
                        <CitationExcerpt citation={chunk} />
                      )}
                    </div>
                  );
                })
              ) : (
                <p className="text-xs leading-5 text-muted-foreground">
                  Không có đoạn trích dẫn hiển thị cho tài liệu này.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

SourceCard.displayName = "SourceCard";

interface CitationExcerptProps {
  citation: SourceChunk;
}

function CitationExcerpt({ citation }: CitationExcerptProps) {
  return (
    <div className="mt-2 space-y-2">
      <div className="border-b pb-1 text-[11px] font-medium text-muted-foreground">
        <span>Đoạn trích</span>
      </div>

      <blockquote className="max-h-80 overflow-y-auto rounded-lg border border-border border-l-4 border-l-primary bg-background p-3 pr-2 text-[13px] leading-6 text-foreground whitespace-pre-line break-words custom-scrollbar">
        {citation.snippet.trim()}
      </blockquote>
    </div>
  );
}

export default SourceCard;
