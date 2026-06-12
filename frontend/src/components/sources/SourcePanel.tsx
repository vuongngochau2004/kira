/**
 * Source Panel Component
 * Displays a NotebookLM-style source list.
 */

"use client";

import { useMemo, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";

import { useSourcePanelState } from "./hooks/use-source-panel-state";
import { SourceList } from "./components/SourceList";

import type { GroupedSource } from "./types/source-panel-types";

export function SourcePanel({ isOpen }: SourcePanelProps) {
  const { state, store, expandDocument, copyToClipboard } =
    useSourcePanelState();

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

  useEffect(() => {
    if (groupedSources.length === 0) return;
    if (state.expandedDocument) return;

    const firstGroup = groupedSources[0];
    expandDocument(firstGroup.document_id || firstGroup.title);
  }, [groupedSources, state.expandedDocument, expandDocument]);

  const handleDocumentExpand = useCallback(
    (documentKey: string) => {
      const wasExpanded = state.expandedDocument === documentKey;
      const nextDocument = wasExpanded ? null : documentKey;
      expandDocument(nextDocument);
    },
    [state.expandedDocument, expandDocument],
  );

  const isExpanded = isOpen !== undefined ? isOpen : store.isOpen;

  return (
    <aside
      className={cn(
        "relative flex bg-background border-l transition-all duration-300 ease-in-out shrink-0 h-full overflow-hidden",
        isExpanded ? "w-85 max-w-[95vw]" : "w-0",
      )}
    >
      {isExpanded && (
        <SourceList
          groupedSources={groupedSources}
          expandedDocument={state.expandedDocument}
          copiedId={state.clipboard.id}
          onDocumentExpand={handleDocumentExpand}
          onCopy={copyToClipboard}
        />
      )}
    </aside>
  );
}

export interface SourcePanelProps {
  isOpen?: boolean;
  onToggle?: () => void;
}
