"use client"

import React from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { documentsAPI } from "@/lib/api/simple-client"
import { Download, FileText, ExternalLink } from "lucide-react"

interface DocumentPreviewDialogProps {
  documentId: string | null
  filename: string
  isOpen: boolean
  onClose: () => void
}

export function DocumentPreviewDialog({
  documentId,
  filename,
  isOpen,
  onClose,
}: DocumentPreviewDialogProps) {
  if (!documentId || !isOpen) return null

  const downloadUrl = documentsAPI.getDownloadUrl(documentId)
  const isPdf = filename.toLowerCase().endsWith(".pdf")
  const isImage = filename.toLowerCase().endsWith(".png") ||
                  filename.toLowerCase().endsWith(".jpg") ||
                  filename.toLowerCase().endsWith(".jpeg") ||
                  filename.toLowerCase().endsWith(".gif") ||
                  filename.toLowerCase().endsWith(".webp")
  const isTxt = filename.toLowerCase().endsWith(".txt")

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className={cn(
          "bg-background border border-border shadow-2xl p-0 overflow-hidden gap-0 rounded-xl flex flex-col",
          isImage
            ? "max-w-3xl w-[90vw] max-h-[85vh]"
            : "max-w-5xl w-[95vw] h-[85vh]"
        )}
      >
        {/* Header Section */}
        <DialogHeader className="p-4 border-b border-border bg-muted/30 shrink-0 flex flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <FileText className="w-4.5 h-4.5 text-primary" />
            </div>
            <div className="min-w-0">
              <DialogTitle className="text-sm font-semibold truncate leading-tight pr-6">
                {filename}
              </DialogTitle>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2 shrink-0 pr-8">
            <Button
              variant="outline"
              size="sm"
              className="flex items-center gap-1 h-8 text-xs"
              asChild
            >
              <a href={downloadUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-3 h-3" />
                Mở tab mới
              </a>
            </Button>
            <Button
              variant="default"
              size="sm"
              className="flex items-center gap-1 h-8 text-xs bg-primary text-primary-foreground hover:bg-primary/95"
              asChild
            >
              <a href={downloadUrl} download>
                <Download className="w-3 h-3" />
                Tải về
              </a>
            </Button>
          </div>
        </DialogHeader>

        {/* Dynamic File Viewer Body */}
        <div className="flex-1 min-h-0 bg-muted/5 flex items-center justify-center overflow-hidden">
          {isPdf || isTxt ? (
            // Direct browser native viewer supporting page scrolling, zoom in/out, fit page, print, find
            <iframe
              src={downloadUrl}
              className="w-full h-full border-0 bg-background"
              title={filename}
            />
          ) : isImage ? (
            // Centered Image Lightbox
            <div className="p-6 max-w-full max-h-[70vh] flex items-center justify-center overflow-auto">
              <img
                src={downloadUrl}
                alt={filename}
                className="max-w-full max-h-[65vh] object-contain rounded-lg border border-border shadow-sm hover:scale-105 transition-transform duration-200"
              />
            </div>
          ) : (
            // Fallback warning (normally won't trigger because Word/PPT are handled with direct download)
            <div className="p-8 text-center">
              <p className="text-sm text-muted-foreground">Định dạng file không hỗ trợ xem trực tuyến.</p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

// Utility to handle conditional Tailwind classnames safely
function cn(...classes: any[]) {
  return classes.filter(Boolean).join(" ")
}
