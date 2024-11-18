import type { Metadata } from "next";
import { ThemeProvider } from "@/context/theme-provider";
import "@/styles/globals.css"
import Layout from "@/components/layout";
import { useState } from "react";

export const metadata: Metadata = {
  title: "OXN++ Dashboard",
  description: "A user-friendly interface for configuring, monitoring, and analyzing observability experiments in cloud-native applications.",
  keywords: ["OXN", "Observability", "Microservices", "Dashboard", "Cloud-Native", "Fault Injection", "Performance Monitoring"],
  authors: [],
  applicationName: "OXN++",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head />
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <Layout>
            {children}
          </Layout>
        </ThemeProvider>
      </body>
    </html>
  );
}
