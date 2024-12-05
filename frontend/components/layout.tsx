import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "./app-sidebar"
import { ThemeToggle } from "./dark-mode-toggle"
export default function Layout({ children }: { children: React.ReactNode }) {

  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="w-full p-2">
        <div className="flex items-center justify-between w-full">
          <SidebarTrigger />
          <ThemeToggle />
        </div>
        <div className="p-2 mt-2">
          {children}
        </div>
      </main>
    </SidebarProvider>
  )
}
