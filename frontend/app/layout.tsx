import type { Metadata } from "next";
import { ThemeProvider } from "@/context/theme-provider";
import "@/styles/globals.css"
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import Layout from "@/components/layout";

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
            <ToastContainer position="top-right" autoClose={3000} />
          </Layout>
        </ThemeProvider>
      </body>
    </html>
  );
}
