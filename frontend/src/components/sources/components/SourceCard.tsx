/**
 * Source Card Component
 * Compact source item used in the left NotebookLM-style source list.
 */

import React, { memo } from "react";
import { ChevronDown, Eye, FileText, Globe, Quote } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SourceCardProps } from "../types/source-panel-types";

const FILE_ICONS = {
  pdf: FileText,
  docx: FileText,
  web: Globe,
} as const;

export const SourceCard = memo<SourceCardProps>((props) => {
  const { group, isSelected, onExpand, onPreview } = props;
  const [expandedCitations, setExpandedCitations] = React.useState<Set<string>>(new Set());

  const Icon = (FILE_ICONS as any)[group.type] || FileText;
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
        "group w-full min-w-0 max-w-full cursor-pointer overflow-hidden rounded-xl border bg-card p-3.5 transition-all duration-200",
        "hover:border-primary/30 hover:bg-muted/30",
        isSelected
          ? "border-primary/35 bg-primary/5 shadow-sm ring-1 ring-primary/15"
          : "border-border/60",
      )}
    >
      <div className="flex min-w-0 items-start">
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex items-start gap-2 min-w-0">
            <Icon className="mt-0.5 w-3.5 h-3.5 text-muted-foreground shrink-0" />
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-semibold text-foreground leading-5 break-words">
                {group.title}
              </h3>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                  {group.chunks.length} trích dẫn
                </span>
                {group.maxScore > 0 && (
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                    {(group.maxScore * 100).toFixed(0)}% liên quan
                  </span>
                )}
              </div>
            </div>

            {group.document_id && (
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onPreview(group.document_id!, group.title);
                }}
                className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
                aria-label="Xem tài liệu gốc"
                title="Xem tài liệu gốc"
              >
                <Eye className="w-3.5 h-3.5" />
              </button>
            )}
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onExpand(groupKey);
              }}
              className="shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
              aria-expanded={isSelected}
              aria-label={isSelected ? "Đóng trích dẫn" : "Mở trích dẫn"}
              title={isSelected ? "Đóng trích dẫn" : "Mở trích dẫn"}
            >
              <ChevronDown
                className={cn(
                  "w-4 h-4 transition-transform duration-200",
                  isSelected && "rotate-180 text-primary",
                )}
                aria-hidden="true"
              />
            </button>
          </div>

          {isSelected && (
            <div className="space-y-2.5">
              {readableChunks.length > 0 ? (
                readableChunks.map((chunk, chunkIndex) => {
                  const citationKey = chunk.id || `${groupKey}-${chunkIndex}`;
                  const isCitationExpanded = expandedCitations.has(citationKey);

                  return (
                    <div
                      key={citationKey}
                      role="button"
                      tabIndex={0}
                      aria-expanded={isCitationExpanded}
                      aria-label={isCitationExpanded ? "Đóng nội dung trích dẫn" : "Mở nội dung trích dẫn"}
                      title={isCitationExpanded ? "Đóng nội dung trích dẫn" : "Mở nội dung trích dẫn"}
                      onClick={(event) => {
                        event.stopPropagation();
                        toggleCitation(citationKey);
                      }}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          event.stopPropagation();
                          toggleCitation(citationKey);
                        }
                      }}
                      className="group/citation cursor-pointer rounded-lg border border-border/60 bg-muted/20 p-3 transition-colors hover:border-primary/30 hover:bg-muted/30"
                    >
                      <div className="flex items-center gap-2">
                        <div className="flex min-w-0 flex-1 items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                          <Quote className="w-3 h-3 shrink-0" />
                          <span className="truncate">
                            Trích dẫn {chunkIndex + 1}
                            {chunk.page ? ` · Trang ${chunk.page}` : ""}
                          </span>
                        </div>

                        <span
                          className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors group-hover/citation:text-primary"
                          aria-hidden="true"
                        >
                          <ChevronDown
                            className={cn(
                              "w-3.5 h-3.5 transition-transform duration-200",
                              isCitationExpanded && "rotate-180 text-primary",
                            )}
                            aria-hidden="true"
                          />
                        </span>
                      </div>

                      {isCitationExpanded && (
                        <p className="mt-2 max-h-72 overflow-y-auto pr-2 text-[13px] leading-6 text-foreground/90 whitespace-pre-line break-words text-justify custom-scrollbar">
                          {chunk.snippet.trim()}
                        </p>
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

export default SourceCard;
