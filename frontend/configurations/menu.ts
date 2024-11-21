import { MenuId } from "@/types"
import { FileChartLine, Search, Settings, Gauge, FileSliders, Activity } from "lucide-react"

export const items = [
  {
    id: MenuId.DASHBOARD,
    title: "Dashboard",
    url: "/",
    icon: Gauge,
  },
  {
    id: MenuId.RESULTS,
    title: "Results & reports",
    url: "/results-and-reports",
    icon: FileChartLine,
  },
  {
    id: MenuId.EXPERIMENT,
    title: "Experiment setup",
    url: "/experiment-setup",
    icon: FileSliders,
  },
  {
    id: MenuId.REALTIME,
    title: 'Real-time monitoring',
    url: '/real-time',
    icon: Activity,
  },
  {
    id: MenuId.SEARCH,
    title: "Search",
    url: "/search",
    icon: Search,
  },
  {
    id: MenuId.SETTINGS,
    title: "Settings",
    url: "/settings",
    icon: Settings,
  }
]