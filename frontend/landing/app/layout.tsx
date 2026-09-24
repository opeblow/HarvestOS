import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "HarvestOS — Farmer support, connected.",
  description:
    "Connect farmer conversations to crop guidance, local agricultural supply, and partner operations in one continuous journey.",
  applicationName: "HarvestOS",
  icons: { icon: "/icon.svg", shortcut: "/icon.svg" },
  openGraph: {
    title: "HarvestOS — Farmer support, connected.",
    description: "A connected commerce platform for the people behind every harvest.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
