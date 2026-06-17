'use client'

import { useState } from "react"
import { CollapsibleSidebar } from "@/components/sidebar/CollapsibleSidebar"
import { MobileNav } from "@/components/mobile/MobileNav"
import { SourcePanel } from "@/components/sources/SourcePanel"
import { PanelResizer } from "@/components/sources/components/PanelResizer"
import { useSourcesStore } from "@/lib/stores/sources-store"
import { PanelRightClose, PanelRightOpen } from "lucide-react"

const DEFAULT_SOURCE_PANEL_WIDTH = 420
const MIN_SOURCE_PANEL_WIDTH = 340
const MAX_SOURCE_PANEL_WIDTH = 760

export default function ConversationLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { isOpen: sourcePanelOpen, toggleOpen } = useSourcesStore()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [sourcePanelWidth, setSourcePanelWidth] = useState(DEFAULT_SOURCE_PANEL_WIDTH)
  const [isResizingSourcePanel, setIsResizingSourcePanel] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Collapsible Sidebar - hidden on mobile initially */}
      <CollapsibleSidebar />

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 w-[280px] bg-background border-r z-50 md:hidden flex flex-col">
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="font-semibold">Menu</h2>
              <button onClick={() => setMobileMenuOpen(false)}>✕</button>
            </div>
          </div>
        </>
      )}

      {/* Main content */}
      <main className="flex-1 overflow-hidden min-w-0 min-h-0 flex flex-col">
        <div className="flex-1 overflow-hidden min-h-0 pb-16 md:pb-0">
          {children}
        </div>
        {/* Mobile Navigation */}
        <MobileNav onMenuClick={() => setMobileMenuOpen(true)} />
      </main>

      {/* Source Panel - Desktop only */}
      <div
        className="hidden lg:block shrink-0 relative h-full"
        style={{
          width: sourcePanelOpen ? sourcePanelWidth : 0,
          transition: isResizingSourcePanel ? "none" : "width 300ms ease-in-out",
        }}
      >
        <button
          type="button"
          onClick={toggleOpen}
          aria-label={sourcePanelOpen ? "Đóng panel nguồn" : "Mở panel nguồn"}
          aria-expanded={sourcePanelOpen}
          title={sourcePanelOpen ? "Đóng panel nguồn" : "Mở panel nguồn"}
          className="absolute -left-10 top-3 z-30 flex h-8 w-8 items-center justify-center rounded-lg border bg-background text-muted-foreground shadow-sm transition-colors hover:bg-muted hover:text-foreground"
        >
          {sourcePanelOpen ? (
            <PanelRightClose className="h-4 w-4" />
          ) : (
            <PanelRightOpen className="h-4 w-4" />
          )}
        </button>

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
        <SourcePanel
          isOpen={sourcePanelOpen}
          onToggle={toggleOpen}
        />
      </div>
    </div>
  )
}
