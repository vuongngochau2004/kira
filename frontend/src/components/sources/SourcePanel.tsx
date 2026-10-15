/**
 * Source Panel Component
 * Displays a NotebookLM-style source list.
 */

"use client";

import { useMemo, useCallback, useState } from "react";
import { cn } from "@/lib/utils";

import { useSourcePanelState } from "./hooks/use-source-panel-state";
import { SourceList } from "./components/SourceList";
import { DocumentPreviewDialog } from "@/components/document-preview-dialog";

import type { GroupedSource } from "./types/source-panel-types";

export function SourcePanel({ isOpen }: SourcePanelProps) {
  const { state, store, expandDocument } = useSourcePanelState();
  const [previewDocument, setPreviewDocument] = useState<{
    id: string;
    filename: string;
  } | null>(null);

  const groupedSources = useMemo(() => {
    const groups: Record<string, GroupedSource> = {};

    store.sources.forEach((source) => {
      const key = source.document_id || source.title;

      if (!groups[key]) {
        groups[key] = {
          document_id: source.document_id || null,
          title: source.title,
          type: source.type,
          maxScore: source.score,
          chunks: [],
        };
      }

      groups[key].chunks.push({
        id: source.id,
        snippet: source.snippet,
        page: source.page,
        score: source.score,
      });

      if (source.score > groups[key].maxScore) {
        groups[key].maxScore = source.score;
      }
    });

    return Object.values(groups);
  }, [store.sources]);

  const handleDocumentExpand = useCallback(
    (documentKey: string) => {
      const wasExpanded = state.expandedDocument === documentKey;
      const nextDocument = wasExpanded ? null : documentKey;
      if (wasExpanded) {
        store.setActiveSourceId(null);
      }
      expandDocument(nextDocument);
    },
    [state.expandedDocument, store, expandDocument],
  );

  const isExpanded = isOpen !== undefined ? isOpen : store.isOpen;

  return (
    <aside
      className={cn(
        "relative flex min-w-0 bg-background border-l transition-all duration-300 ease-in-out shrink-0 h-full overflow-hidden",
        isExpanded ? "w-full" : "w-0",
      )}
    >
      {isExpanded && (
        <SourceList
          groupedSources={groupedSources}
          expandedDocument={state.expandedDocument}
          onDocumentExpand={handleDocumentExpand}
          onDocumentPreview={(documentId, filename) => {
            setPreviewDocument({ id: documentId, filename });
          }}
        />
      )}
      <DocumentPreviewDialog
        documentId={previewDocument?.id ?? null}
        filename={previewDocument?.filename ?? ""}
        isOpen={previewDocument !== null}
        onClose={() => setPreviewDocument(null)}
      />
    </aside>
  );
}

export interface SourcePanelProps {
  isOpen?: boolean;
  onToggle?: () => void;
}
