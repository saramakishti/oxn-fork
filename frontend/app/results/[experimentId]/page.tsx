import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ChevronLeft } from 'lucide-react'
import { allResults } from "@/mock-data/results";
import { ExperimentsTable } from "@/components/dynamic-table/table";
import { resultDetailsConfig } from "@/components/dynamic-table/table-columns";
import { prepareResultDetailsData } from "@/utils/results";

export default function ExperimentResultDetails(props: any) {

  const experimentId = props.params.experimentId;

  const experimentData = allResults.find((el) => el.experiment_id === experimentId) || null
  const tableData = prepareResultDetailsData(experimentData)

  return (
    <div>
      <div className="flex justify-between">
        <h1 className="text-2xl font-bold">Details for #{experimentId}</h1>
        <div>
          <Button variant="ghost">
            <ChevronLeft />
            <Link href="/results">Go back</Link>
          </Button>
        </div>
      </div>
      <div className="container mx-auto">
        <ExperimentsTable filterColumnKey="runId" columns={resultDetailsConfig} data={tableData} />
      </div>
    </div>
  )
}