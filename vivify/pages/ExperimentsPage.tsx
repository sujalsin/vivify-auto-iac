import React, { useState, useEffect } from 'react';
import { experimentsApi, Experiment, ExperimentRunResponse } from '../services/experimentsApi';

const ExperimentsPage: React.FC = () => {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<string>('');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<ExperimentRunResponse | null>(null);
  const [config, setConfig] = useState<any>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchExperiments();
  }, []);

  const fetchExperiments = async () => {
    try {
      const data = await experimentsApi.listExperiments();
      setExperiments(data.experiments || []);
    } catch (error) {
      console.error('Failed to fetch experiments:', error);
      setError('Failed to load experiments. Make sure the backend is running.');
    }
  };

  const runExperiment = async () => {
    if (!selectedExperiment) return;

    setRunning(true);
    setResults(null);
    setError(null);

    try {
      const data = await experimentsApi.runExperiment({
        experiment_type: selectedExperiment,
        config: config,
      });
      setResults(data);
      
      // If run_id is available, fetch detailed results
      if (data.run_id) {
        setTimeout(async () => {
          try {
            const detailedResults = await experimentsApi.getResults(data.run_id);
            setResults(prev => prev ? { ...prev, results: detailedResults } : null);
          } catch (err) {
            console.error('Failed to fetch detailed results:', err);
          }
        }, 1000);
      }
    } catch (error: any) {
      console.error('Failed to run experiment:', error);
      setError(error.message || 'Failed to run experiment');
      setResults({
        run_id: '',
        experiment_type: selectedExperiment,
        status: 'failed',
        results: { error: error.message || String(error) },
      });
    } finally {
      setRunning(false);
    }
  };

  const getExperimentConfig = (type: string) => {
    const configs: Record<string, any> = {
      e1: { num_tasks: 100, max_parallel: 10 },
      e2: { max_iterations: 5 },
      e3: { num_stacks: 10 },
      e4: { num_sessions: 100, canvas_sizes: [100, 500] },
    };
    return configs[type] || {};
  };

  const handleExperimentChange = (type: string) => {
    setSelectedExperiment(type);
    setConfig(getExperimentConfig(type));
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto', color: '#333' }}>
      <h1>Experiments Dashboard</h1>
      
      {error && (
        <div style={{ 
          background: '#fee', 
          color: '#c33', 
          padding: '1rem', 
          borderRadius: '4px', 
          marginBottom: '1rem' 
        }}>
          {error}
        </div>
      )}

      <div style={{ marginBottom: '2rem' }}>
        <h2>Available Experiments</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
          <div
            onClick={() => handleExperimentChange('e1')}
            style={{
              padding: '1rem',
              border: selectedExperiment === 'e1' ? '2px solid #4285f4' : '1px solid #ccc',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            <h3>E1: Parallelism</h3>
            <p>Measure throughput and speedup</p>
          </div>
          <div
            onClick={() => handleExperimentChange('e2')}
            style={{
              padding: '1rem',
              border: selectedExperiment === 'e2' ? '2px solid #4285f4' : '1px solid #ccc',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            <h3>E2: Deployability</h3>
            <p>Measure passItr@n</p>
          </div>
          <div
            onClick={() => handleExperimentChange('e3')}
            style={{
              padding: '1rem',
              border: selectedExperiment === 'e3' ? '2px solid #4285f4' : '1px solid #ccc',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            <h3>E3: Concurrency</h3>
            <p>Measure convergence and rollback</p>
          </div>
          <div
            onClick={() => handleExperimentChange('e4')}
            style={{
              padding: '1rem',
              border: selectedExperiment === 'e4' ? '2px solid #4285f4' : '1px solid #ccc',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            <h3>E4: Canvas Performance</h3>
            <p>Measure WebSocket latency and FPS</p>
          </div>
        </div>
      </div>

      {selectedExperiment && (
        <div style={{ marginBottom: '2rem' }}>
          <h2>Configuration</h2>
          <div style={{ marginBottom: '1rem' }}>
            <pre style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '4px' }}>
              {JSON.stringify(config, null, 2)}
            </pre>
          </div>
          <button
            onClick={runExperiment}
            disabled={running}
            style={{
              padding: '0.75rem 1.5rem',
              background: running ? '#ccc' : '#4285f4',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: running ? 'not-allowed' : 'pointer',
            }}
          >
            {running ? 'Running...' : 'Run Experiment'}
          </button>
        </div>
      )}

      {results && (
        <div>
          <h2>Results</h2>
          <div style={{ 
            background: results.status === 'completed' ? '#e8f5e9' : results.status === 'failed' ? '#ffebee' : '#fff3e0',
            padding: '1rem', 
            borderRadius: '4px',
            border: `2px solid ${results.status === 'completed' ? '#4caf50' : results.status === 'failed' ? '#f44336' : '#ff9800'}`
          }}>
            <p><strong>Status:</strong> <span style={{ 
              color: results.status === 'completed' ? '#2e7d32' : results.status === 'failed' ? '#c62828' : '#e65100',
              fontWeight: 'bold'
            }}>{results.status.toUpperCase()}</span></p>
            <p><strong>Run ID:</strong> <code>{results.run_id}</code></p>
            {results.status === 'running' && (
              <p style={{ color: '#e65100' }}>⏳ Experiment is running... Results will appear when complete.</p>
            )}
            {results.results && (
              <div style={{ marginTop: '1rem' }}>
                <h3>Results Data:</h3>
                <pre style={{ 
                  background: 'white', 
                  padding: '1rem', 
                  borderRadius: '4px', 
                  overflow: 'auto',
                  maxHeight: '400px',
                  fontSize: '12px'
                }}>
                  {JSON.stringify(results.results, null, 2)}
                </pre>
              </div>
            )}
            {results.run_id && results.status === 'running' && (
              <button
                onClick={async () => {
                  try {
                    const detailedResults = await experimentsApi.getResults(results.run_id);
                    setResults(prev => prev ? { ...prev, results: detailedResults, status: detailedResults.status || prev.status } : null);
                  } catch (err) {
                    console.error('Failed to fetch results:', err);
                  }
                }}
                style={{
                  marginTop: '1rem',
                  padding: '0.5rem 1rem',
                  background: '#4285f4',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Refresh Results
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExperimentsPage;

