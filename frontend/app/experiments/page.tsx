import ExperimentsView from "@/components/experiments";

export default function ExperimentsPage() {
  return (
    <div>
      <div>
        <h1 className="text-xl font-bold">All Experiment Configurations</h1>
      </div>
      <div className="container mx-auto">
        <ExperimentsView />
      </div>
    </div>
  )
}