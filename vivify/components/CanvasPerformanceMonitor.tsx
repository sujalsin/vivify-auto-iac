import React, { useState, useEffect, useRef } from 'react';

interface PerformanceMetrics {
  fps: number;
  latency: number;
  droppedEvents: number;
  totalEvents: number;
}

const CanvasPerformanceMonitor: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    fps: 0,
    latency: 0,
    droppedEvents: 0,
    totalEvents: 0,
  });
  const frameCountRef = useRef(0);
  const lastTimeRef = useRef(performance.now());
  const eventCountRef = useRef(0);
  const droppedCountRef = useRef(0);

  useEffect(() => {
    const calculateFPS = () => {
      const now = performance.now();
      const delta = now - lastTimeRef.current;
      frameCountRef.current++;

      if (delta >= 1000) {
        const fps = (frameCountRef.current * 1000) / delta;
        setMetrics((prev) => ({
          ...prev,
          fps: Math.round(fps),
        }));
        frameCountRef.current = 0;
        lastTimeRef.current = now;
      }

      requestAnimationFrame(calculateFPS);
    };

    const animationId = requestAnimationFrame(calculateFPS);
    return () => cancelAnimationFrame(animationId);
  }, []);

  const recordEvent = (latency: number, dropped: boolean = false) => {
    eventCountRef.current++;
    if (dropped) {
      droppedCountRef.current++;
    }

    setMetrics((prev) => ({
      ...prev,
      latency,
      totalEvents: eventCountRef.current,
      droppedEvents: droppedCountRef.current,
    }));
  };

  const droppedEventsPercent =
    metrics.totalEvents > 0
      ? ((metrics.droppedEvents / metrics.totalEvents) * 100).toFixed(2)
      : '0.00';

  return (
    <div
      style={{
        position: 'fixed',
        top: '10px',
        right: '10px',
        background: 'rgba(0, 0, 0, 0.8)',
        color: 'white',
        padding: '1rem',
        borderRadius: '8px',
        fontFamily: 'monospace',
        fontSize: '12px',
        zIndex: 1000,
        minWidth: '200px',
      }}
    >
      <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '14px' }}>Performance Monitor</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
        <div>
          <strong>FPS:</strong> {metrics.fps}
        </div>
        <div>
          <strong>Latency:</strong> {metrics.latency.toFixed(2)}ms
        </div>
        <div>
          <strong>Events:</strong> {metrics.totalEvents}
        </div>
        <div>
          <strong>Dropped:</strong> {metrics.droppedEvents} ({droppedEventsPercent}%)
        </div>
      </div>
    </div>
  );
};

export default CanvasPerformanceMonitor;

