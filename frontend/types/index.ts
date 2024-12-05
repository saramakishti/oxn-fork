export enum MenuId {
  DASHBOARD = 'dashboard',
  EXPERIMENTS = 'experiments',
  REALTIME = 'realtime',
  SEARCH = 'search',
  SETTINGS = 'settings',
}

export type ExperimentType = {
  experimentId: string;
  experimentDate: string;
  numberOfRuns: number;
  treatmentNames: string[];
  treatmentTypes: string[];
};


export type ExperimentDetailsType = {
  experimentId: string;
  experimentDate: string;
  runId: string;
  runDate: string;
  loadgenStartTime: string;
  loadgenEndTime: string;
  loadgenTotalRequests: number;
  loadgenTotalFailures: number;
  interactionId: string;
  treatmentName: string;
  treatmentType: string;
  treatmentStart: string;
  treatmentEnd: string;
  responseName: string;
  responseStart: string;
  responseEnd: string;
  responseType: string;
  storeKey: string;
};
