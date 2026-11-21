/**
 * Source List Component
 * Displays the list of source documents in the left column.
 */

import { memo } from "react";
import { BookOpen, X } from "lucide-react";
import { SourceCard } from "@/features/chat/sources/SourceCard";
import type { GroupedSource } from "@/features/chat/sources/types";

interface SourceListProps {
  groupedSources: GroupedSource[];
  expandedDocument: string | null;
  activeSourceId: string | null;
  onDocumentExpand: (documentId: string) => void;
  onDocumentPreview: (documentId: string, filename: string) => void;
  onClose: () => void;
}

export const SourceList = memo<SourceListProps>(
  ({
    groupedSources,
    expandedDocument,
    activeSourceId,
    onDocumentExpand,
    onDocumentPreview,
    onClose,
  }) => {
    if (groupedSources.length === 0) {
      return (
        <div className="flex h-full min-h-0 w-full flex-col">
          <div className="flex h-14 shrink-0 items-center justify-between border-b px-4">
            <h2 className="text-sm font-semibold">Nguồn</h2>
            <button type="button" onClick={onClose} aria-label="Đóng nguồn" className="rounded-md p-1.5 text-muted-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-primary">
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
          <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
            <BookOpen className="w-8 h-8 text-muted-foreground/40 mb-2" />
            <p className="max-w-xs text-sm leading-6 text-muted-foreground">Chưa có nguồn trích xuất cho cuộc hội thoại này.</p>
          </div>
        </div>
      );
    }

    return (
      <div className="flex flex-col h-full w-full min-w-0 overflow-hidden">
        <div className="h-14 border-b flex items-center justify-between px-4 shrink-0 bg-background/95 backdrop-blur min-w-0">
          <div className="flex items-center gap-2 min-w-0">
            <BookOpen className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold">Nguồn</h2>
            <span className="text-xs text-muted-foreground">
              ({groupedSources.length})
            </span>
          </div>
          <button type="button" onClick={onClose} aria-label="Đóng nguồn" className="rounded-md p-1.5 text-muted-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-primary">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0">
          <div className="w-full min-w-0 p-4 space-y-3">
            {groupedSources.map((group, index) => {
              const groupKey = group.document_id || group.title;
              const isExpanded = expandedDocument === groupKey;

              return (
                <SourceCard
                  key={groupKey}
                  group={group}
                  index={index}
                  isSelected={isExpanded}
                  activeSourceId={activeSourceId}
                  onExpand={onDocumentExpand}
                  onPreview={onDocumentPreview}
                />
              );
            })}
          </div>
        </div>
      </div>
    );
  },
);

SourceList.displayName = "SourceList";
