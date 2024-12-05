
import { ExperimentTable } from "@/components/experiments/table"
import { allExperimentsConfig } from "@/components/experiments/table-columns"
import { allExperiments } from "@/mock-data/experiments"
import { prepareExperimentTableData } from "@/utils/experiments";


export default async function ExperimentsPage() {
  const tableData = prepareExperimentTableData(allExperiments);
  return (
    <div>
      <div>
        <h1 className="text-2xl font-bold text-gray-900">All Experiments</h1>
      </div>
      <div className="container mx-auto">
        <ExperimentTable columns={allExperimentsConfig} data={tableData} />
      </div>
    </div>
  )
}