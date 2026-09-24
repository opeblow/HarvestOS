import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Partner operations | HarvestOS",
  description: "Secure operations console for HarvestOS partner networks.",
  icons: { icon: "/icon.svg", shortcut: "/icon.svg" },
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-paper text-ink antialiased">{children}</body>
    </html>
  );
}
