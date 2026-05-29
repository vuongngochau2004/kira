import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { Providers } from "./providers"
import { ThemeScript } from "@/components/ThemeScript"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "K.I.R.A — Knowledge & Intelligent Robotic Assistant",
  description: "AI Research Assistant with RAG and Knowledge Graph",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body className={inter.className} suppressHydrationWarning>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
