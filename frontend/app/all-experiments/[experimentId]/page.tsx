import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ChevronLeft } from 'lucide-react'
import { allExperiments } from "@/mock-data/experiments";
import { ExperimentTable } from "@/components/experiments/table";
import { experimentDetailsConfig } from "@/components/experiments/table-columns";
import { prepareExperimentDetailsData } from "@/utils/experiments";

export default function ExperimentDetails(props: any) {

  const experimentId = props.params.experimentId;

  const experimentData = allExperiments.find((el) => el.experiment_id === experimentId) || null
  const tableData = prepareExperimentDetailsData(experimentData)

  return (
    <div>
      <div className="flex justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Details for #{experimentId}</h1>
        <div>
          <Button variant="ghost">
            <ChevronLeft />
            <Link href="/all-experiments">Go back</Link>
          </Button>
        </div>
      </div>
      <div className="container mx-auto">
        <ExperimentTable filterColumnKey="runId" columns={experimentDetailsConfig} data={tableData} />
      </div>
    </div>
  )
}