import { ExperimentDetailsType, ExperimentType } from "@/types";
import { Experiment, Run, Interaction, Loadgen } from '../types/experiment';


export function prepareResultsTableData(data: Experiment[]): ExperimentType[] {
  return data.map((experiment) => {
    const runs = Object.values(experiment.runs);
    const treatmentNamesSet = new Set<string>();
    const treatmentTypesSet = new Set<string>();

    runs.forEach((run: Run) => {
      const interactions = Object.values(run.interactions);
      interactions.forEach((interaction: Interaction) => {
        treatmentNamesSet.add(interaction.treatment_name);
        treatmentTypesSet.add(interaction.treatment_type);
      });
    });

    return {
      experimentId: experiment.experiment_id,
      experimentDate: experiment.date,
      numberOfRuns: runs.length,
      treatmentNames: Array.from(treatmentNamesSet),
      treatmentTypes: Array.from(treatmentTypesSet),
    };
  });
}


export function prepareResultDetailsData(data: Experiment | null): ExperimentDetailsType[] {
  const rows: ExperimentDetailsType[] = [];

  if (data) {
    const experimentId = data.experiment_id;
    const experimentDate = data.date;
    const runs = data.runs;

    for (const [_, runValue] of Object.entries(runs)) {
      const run = runValue as Run;
      const runId = run.id;
      const runDate = run.date;
      const loadgen = run.loadgen;
      const interactions = run.interactions;

      for (const [interactionKey, interactionValue] of Object.entries(interactions)) {
        const interaction = interactionValue as Interaction;
        const row: ExperimentDetailsType = {
          experimentId,
          experimentDate,
          runId,
          runDate,
          loadgenStartTime: loadgen.loadgen_start_time,
          loadgenEndTime: loadgen.loadgen_end_time,
          loadgenTotalRequests: loadgen.loadgen_total_requests,
          loadgenTotalFailures: loadgen.loadgen_total_failures,
          interactionId: interactionKey,
          treatmentName: interaction.treatment_name,
          treatmentType: interaction.treatment_type,
          treatmentStart: interaction.treatment_start,
          treatmentEnd: interaction.treatment_end,
          responseName: interaction.response_name,
          responseStart: interaction.response_start,
          responseEnd: interaction.response_end,
          responseType: interaction.response_type,
          storeKey: interaction.store_key,
        };
        rows.push(row);
      }
    }
  }

  return rows;
}
