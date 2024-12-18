export interface Experiment {
  experiment_id: string;
  date: string;
  runs: any;
  // runs: { [key: string]: Run }
}

export interface Run {
  id: string;
  date: string;
  interactions: { [key: string]: Interaction };
  loadgen: Loadgen;
}

export interface Interaction {
  treatment_name: string;
  treatment_type: string;
  treatment_start: string;
  treatment_end: string;
  response_name: string;
  response_start: string;
  response_end: string;
  response_type: string;
  store_key: string;
}

export interface Loadgen {
  loadgen_start_time: string;
  loadgen_end_time: string;
  loadgen_total_requests: number;
  loadgen_total_failures: number;
}