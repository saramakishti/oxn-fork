
import { ExperimentResultsTable } from "@/components/experiments/table"
import { allResultsConfig } from "@/components/experiments/table-columns"
import { allResults } from "@/mock-data/results"
import { prepareResultsTableData } from "@/utils/results";


export default async function ResultsPage() {
  const tableData = prepareResultsTableData(allResults);
  return (
    <div>
      <div>
        <h1 className="text-2xl font-bold text-gray-900">All Experiment Results</h1>
      </div>
      <div className="container mx-auto">
        <ExperimentResultsTable columns={allResultsConfig} data={tableData} />
      </div>
    </div>
  )
}