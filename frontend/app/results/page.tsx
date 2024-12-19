
import { ExperimentsTable } from "@/components/dynamic-table/table"
import { allResultsConfig } from "@/components/dynamic-table/table-columns"
import { allResults } from "@/mock-data/results"
import { prepareResultsTableData } from "@/utils/results";


export default async function ResultsPage() {
  const tableData = prepareResultsTableData(allResults);
  return (
    <div>
      <div>
        <h1 className="text-xl font-bold">All Experiment Results</h1>
      </div>
      <div className="container mx-auto">
        <ExperimentsTable columns={allResultsConfig} data={tableData} />
      </div>
    </div>
  )
}