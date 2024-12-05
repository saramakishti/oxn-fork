import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Telescope } from "lucide-react";
import StartExperimentDialog from "@/components/dashboard/start-experiment";
import Metrics from "@/components/dashboard/metrics";

export default function Home() {
  return (
    <div>
      <div className="flex justify-between">
        <StartExperimentDialog />
        <Button variant="outline">
          <Telescope />
          <Link href='/all-experiments'>
            Explore past experiments</Link>
        </Button>
      </div>
      <div className="my-4">
        <Metrics />
        Chart coming soon...
      </div>
    </div>
  );
}
