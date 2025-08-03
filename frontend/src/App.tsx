import React, { useState } from 'react';
import ChatInterface from './components/Chat/ChatInterface';
import ResponsePanel from './components/Panel/ResponsePanel';
import StatusVisualization from './components/Visualization/StatusVisualization';
import './App.css';

interface StatusUpdate {
  step: string;
  status: string;
  message: string;
  progress: number;
  data?: any;
}

interface AnalysisResult {
  report: {
    ticker: string;
    company_name: string;
    timestamp: string;
    query: string;
    price_info: {
      current_price: number;
      change: number;
      change_percent: number;
    };
    analysis: string;
    fundamentals: any;
    reddit_sentiment: any;
    news: any[];
  };
}

const App: React.FC = () => {
  const [statusUpdates, setStatusUpdates] = useState<StatusUpdate[]>([]);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);

  const handleNewQuery = (query: string) => {
    setStatusUpdates([]);
    setAnalysisResult(null);
    setIsAnalyzing(true);
    setAnalysisComplete(false);
    
    // Start streaming analysis
    startStreamingAnalysis(query);
  };

  const startStreamingAnalysis = async (query: string) => {
    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('Failed to get response reader');
      }

      let currentEvent = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            
            try {
              if (dataStr.trim() === '') continue; // Skip empty data lines
              
              const data = JSON.parse(dataStr);
              
              if (currentEvent === 'status_update') {
                // This is a status update
                if (data.step && data.status) {
                  setStatusUpdates(prev => [...prev, data]);
                  
                  // Check if this status update contains the final report
                  if (data.step === 'report_generation' && data.status === 'completed' && data.data?.report) {
                    setAnalysisResult({ report: data.data.report });
                  }
                }
              } else if (currentEvent === 'analysis_start') {
                console.log('Analysis started:', data);
              } else if (currentEvent === 'analysis_complete') {
                // Analysis completed
                console.log('Analysis completed!');
                setIsAnalyzing(false);
                setAnalysisComplete(true);
              } else if (data.report) {
                // This is the final analysis result (fallback)
                setAnalysisResult(data);
                setIsAnalyzing(false);
              }
            } catch (e) {
              // If JSON parsing fails, check if it's the report data
              if (dataStr.includes('"report":')) {
                try {
                  const data = JSON.parse(dataStr);
                  setAnalysisResult(data);
                  setIsAnalyzing(false);
                } catch (parseError) {
                  console.error('Error parsing report data:', parseError);
                }
              } else {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error in streaming analysis:', error);
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="app">
      <div className="app-container">
        <div className="left-panel">
          <ChatInterface onNewQuery={handleNewQuery} isAnalyzing={isAnalyzing} analysisComplete={analysisComplete} />
          <StatusVisualization statusUpdates={statusUpdates} />
        </div>
        <div className="right-panel">
          <ResponsePanel analysisResult={analysisResult} isAnalyzing={isAnalyzing} />
        </div>
      </div>
    </div>
  );
};

export default App;