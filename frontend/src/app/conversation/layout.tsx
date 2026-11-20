'use client'

import { useEffect, useState } from "react"
import { CollapsibleSidebar } from "@/components/layout/CollapsibleSidebar"
import { MobileNav } from "@/components/layout/MobileNav"
import { SourcePanel } from "@/features/chat/sources/SourcePanel"
import { PanelResizer } from "@/features/chat/sources/PanelResizer"
import { useSourcesStore } from "@/features/chat/stores/sources-store"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"

const DEFAULT_SOURCE_PANEL_WIDTH = 420
const MIN_SOURCE_PANEL_WIDTH = 340
const MAX_SOURCE_PANEL_WIDTH = 760

export default function ConversationLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const sourcePanelOpen = useSourcesStore((state) => state.isOpen)
  const [sourcePanelWidth, setSourcePanelWidth] = useState(DEFAULT_SOURCE_PANEL_WIDTH)
  const [isResizingSourcePanel, setIsResizingSourcePanel] = useState(false)
  const [isDesktop, setIsDesktop] = useState(false)
  const setSourcesOpen = useSourcesStore((state) => state.setIsOpen)

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)")
    const update = () => setIsDesktop(media.matches)
    update()
    media.addEventListener("change", update)
    return () => media.removeEventListener("change", update)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Collapsible Sidebar - hidden on mobile initially */}
      <CollapsibleSidebar />

      {/* Main content */}
      <main className="flex-1 overflow-hidden min-w-0 min-h-0 flex flex-col">
        <div className="flex-1 overflow-hidden min-h-0 pb-16 md:pb-0">
          {children}
        </div>
        {/* Mobile Navigation */}
        <MobileNav />
      </main>

      {isDesktop ? <div
        className="shrink-0 relative h-full"
        style={{ width: sourcePanelOpen ? sourcePanelWidth : 0, transition: isResizingSourcePanel ? "none" : "width 300ms ease-in-out" }}
      >
        {sourcePanelOpen && (
          <PanelResizer
            direction="horizontal"
            resizeFrom="start"
            size={sourcePanelWidth}
            minSize={MIN_SOURCE_PANEL_WIDTH}
            maxSize={MAX_SOURCE_PANEL_WIDTH}
            onResize={setSourcePanelWidth}
            onResizeStart={() => setIsResizingSourcePanel(true)}
            onResizeEnd={() => setIsResizingSourcePanel(false)}
            className="-left-1"
          />
        )}
        <SourcePanel isOpen={sourcePanelOpen} />
      </div> : (
        <Dialog open={sourcePanelOpen} onOpenChange={setSourcesOpen}>
          <DialogContent
            className="right-0 left-auto top-0 h-dvh w-[min(420px,100vw)] max-w-none translate-x-0 translate-y-0 rounded-none p-0"
            showCloseButton={false}
            onCloseAutoFocus={(event) => {
              event.preventDefault()
              document.getElementById("conversation-sources-trigger")?.focus()
            }}
          >
            <DialogTitle className="sr-only">Nguồn trích dẫn</DialogTitle>
            <SourcePanel isOpen />
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
