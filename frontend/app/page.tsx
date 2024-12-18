import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Telescope } from "lucide-react";
import StartExperimentDialog from "@/components/dashboard/start-experiment";
import ComingSoon from "@/components/coming-soon";

export default function Home() {
  return (
    <div>
      <div className="flex justify-between">
        <StartExperimentDialog />
        <Button variant="outline">
          <Telescope />
          <Link href='/results'>
            Explore past results</Link>
        </Button>
      </div>
      <div className="my-4">
        <ComingSoon showBackButton={false} />
      </div>
    </div>
  );
}
