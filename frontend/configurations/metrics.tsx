import { Network, AlertTriangle, Percent, Timer } from "lucide-react";

export const cardConfiguration = [
  {
    title: "Total Experiment Runs",
    description: "The total number of experiments handled.",
    icon: <Network size={20} />,
  },
  {
    title: "Total Failures",
    description: "The total number of failed experiments encountered.",
    icon: <AlertTriangle size={20} />,
  },
  {
    title: "Failure Rate",
    description: "The percentage of overall failed experiments.",
    icon: <Percent size={20} />,
  },
  {
    title: "Average Response Time",
    description: "The average time taken to process an experiment.",
    icon: <Timer size={20} />,
  },
];