import React, { useEffect, useRef } from 'react';

interface StatusUpdate {
  step: string;
  status: string;
  message: string;
  progress: number;
  data?: any;
}

interface StatusVisualizationProps {
  statusUpdates: StatusUpdate[];
}

const StatusVisualization: React.FC<StatusVisualizationProps> = ({ statusUpdates }) => {
    const statusListRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new status updates are added
    useEffect(() => {
        if (statusListRef.current) {
            statusListRef.current.scrollTop = statusListRef.current.scrollHeight;
        }
    }, [statusUpdates]);

    return (
        <div className="status-visualization">
            <h3>Analysis Progress</h3>
            <div className="status-list" ref={statusListRef}>
                {statusUpdates.map((update, index) => (
                    <div key={index} className={`status-item ${update.status}`}>
                        <div className="status-step">{update.step.replace(/_/g, ' ').toUpperCase()}</div>
                        <div className="status-message">{update.message}</div>
                        <div className="status-progress">
                            <div className="progress-bar">
                                <div 
                                    className="progress-fill" 
                                    style={{ width: `${update.progress * 100}%` }}
                                ></div>
                            </div>
                            <span className="progress-text">{Math.round(update.progress * 100)}%</span>
                        </div>
                        {update.data && (
                            <div className="status-data">
                                {JSON.stringify(update.data, null, 2)}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default StatusVisualization;