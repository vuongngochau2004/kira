/**
 * Source List Component
 * Displays the list of source documents in the left column.
 */

import { memo } from "react";
import { BookOpen } from "lucide-react";
import { SourceCard } from "./SourceCard";
import type { GroupedSource } from "../types/source-panel-types";

interface SourceListProps {
  groupedSources: GroupedSource[];
  expandedDocument: string | null;
  onDocumentExpand: (documentId: string) => void;
  onDocumentPreview: (documentId: string, filename: string) => void;
}

export const SourceList = memo<SourceListProps>(
  ({
    groupedSources,
    expandedDocument,
    onDocumentExpand,
    onDocumentPreview,
  }) => {
    if (groupedSources.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center h-48 text-center px-4">
          <BookOpen className="w-8 h-8 text-muted-foreground/40 mb-2" />
          <p className="text-xs text-muted-foreground">
            Chưa có nguồn trích xuất cho cuộc hội thoại này.
          </p>
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
