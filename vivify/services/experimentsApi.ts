/**
 * Experiments API Service
 */

import { apiClient } from './api';

export interface Experiment {
  id: string;
  name: string;
  experiment_type: string;
  description?: string;
  created_at?: string;
}

export interface ExperimentRunRequest {
  experiment_type: string;
  config?: Record<string, any>;
}

export interface ExperimentRunResponse {
  run_id: string;
  experiment_type: string;
  status: string;
  results?: any;
}

export interface ExperimentRun {
  id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
}

export const experimentsApi = {
  /**
   * List all experiments
   */
  async listExperiments(): Promise<{ experiments: Experiment[] }> {
    return apiClient.get<{ experiments: Experiment[] }>('/api/experiments/list');
  },

  /**
   * Run an experiment
   */
  async runExperiment(
    request: ExperimentRunRequest
  ): Promise<ExperimentRunResponse> {
    return apiClient.post<ExperimentRunResponse>('/api/experiments/run', request);
  },

  /**
   * Get experiment results
   */
  async getResults(runId: string): Promise<any> {
    return apiClient.get(`/api/experiments/results/${runId}`);
  },

  /**
   * Get runs for an experiment
   */
  async getRuns(experimentId: string): Promise<{ runs: ExperimentRun[] }> {
    return apiClient.get<{ runs: ExperimentRun[] }>(`/api/experiments/runs/${experimentId}`);
  },
};

