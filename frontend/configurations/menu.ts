import { MenuId } from "@/types"
import {
  FileChartLine,
  Gauge,
  MonitorCog,
  // Settings,
  // FileText,
  // Activity,
  // Search,
} from "lucide-react"

export const items = [
  {
    id: MenuId.DASHBOARD,
    title: "Dashboard",
    url: "/",
    icon: Gauge,
  },
  {
    id: MenuId.EXPERIMENTS,
    title: "Experiments",
    url: "/experiments",
    icon: MonitorCog,
  },
  {
    id: MenuId.RESULTS,
    title: "Results",
    url: "/results",
    icon: FileChartLine,
  },
  // {
  //   id: MenuId.REALTIME,
  //   title: 'Real-time monitoring',
  //   url: '/real-time',
  //   icon: Activity,
  // },
  // {
  //   id: MenuId.SEARCH,
  //   title: "Search",
  //   url: "/search",
  //   icon: Search,
  // },
  // {
  //   id: MenuId.SETTINGS,
  //   title: "Settings",
  //   url: "/settings",
  //   icon: Settings,
  // }
]