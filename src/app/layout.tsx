import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RepoSage - AI Repository Analyst",
  description: "Understand unfamiliar open-source repositories using local open-weight AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-slate-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
