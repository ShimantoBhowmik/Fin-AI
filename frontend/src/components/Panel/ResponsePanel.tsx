import React, { useEffect, useRef } from 'react';

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

interface ResponsePanelProps {
    analysisResult: AnalysisResult | null;
    isAnalyzing: boolean;
}

// TradingView Chart Component
const TradingViewChart: React.FC<{ ticker: string }> = ({ ticker }) => {
    const chartRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!chartRef.current) return;

        // Clear previous chart
        chartRef.current.innerHTML = '';

        // Create TradingView widget
        const script = document.createElement('script');
        script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
        script.type = 'text/javascript';
        script.async = true;
        script.innerHTML = JSON.stringify({
            autosize: true,
            symbol: `NASDAQ:${ticker}`,
            interval: "D",
            timezone: "Etc/UTC",
            theme: "dark",
            style: "1",
            locale: "en",
            enable_publishing: false,
            withdateranges: true,
            range: "6M",
            hide_side_toolbar: false,
            allow_symbol_change: false,
            save_image: false,
            calendar: false,
            hide_volume: false,
            support_host: "https://www.tradingview.com"
        });

        chartRef.current.appendChild(script);

        return () => {
            if (chartRef.current) {
                chartRef.current.innerHTML = '';
            }
        };
    }, [ticker]);

    return (
        <div className="tradingview-widget-container" style={{ height: '400px', width: '100%' }}>
            <div 
                ref={chartRef}
                className="tradingview-widget" 
                style={{ height: 'calc(100% - 32px)', width: '100%' }}
            />
        </div>
    );
};

const ResponsePanel: React.FC<ResponsePanelProps> = ({ analysisResult, isAnalyzing }) => {
    const downloadPDF = () => {
        if (!analysisResult?.report.analysis) return;
        
        // Create a blob with the markdown content
        const blob = new Blob([analysisResult.report.analysis], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        
        // Create a download link
        const a = document.createElement('a');
        a.href = url;
        a.download = `${analysisResult.report.ticker}_analysis_${new Date().toISOString().slice(0, 10)}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    // Function to parse and render markdown-like content
    const renderMarkdown = (text: string) => {
        return text
            .replace(/<think>[\s\S]*?<\/think>/g, '') // Remove <think> tags and content
            .replace(/```markdown\s*```/g, '') // Remove empty markdown code blocks
            .replace(/```\s*```/g, '') // Remove empty code blocks
            .replace(/```markdown\s*\n\s*```/g, '') // Remove empty markdown code blocks with newlines
            .replace(/```\s*\n\s*```/g, '') // Remove empty code blocks with newlines
            .split('\n')
            .filter(line => {
                // Filter out lines that are just markdown code block markers
                const trimmed = line.trim();
                return !(trimmed === '```' || trimmed === '```markdown' || trimmed === '```md');
            })
            .map((line, index) => {
                // Headers
                if (line.startsWith('# ')) {
                    return <h1 key={index} className="md-h1">{line.substring(2)}</h1>;
                }
                if (line.startsWith('## ')) {
                    return <h2 key={index} className="md-h2">{line.substring(3)}</h2>;
                }
                if (line.startsWith('### ')) {
                    return <h3 key={index} className="md-h3">{line.substring(4)}</h3>;
                }
                
                // Bold text
                line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                
                // Bullet points
                if (line.startsWith('* ') || line.startsWith('- ')) {
                    return <li key={index} className="md-li" dangerouslySetInnerHTML={{ __html: line.substring(2) }} />;
                }
                
                // Table rows
                if (line.includes('|') && line.trim() !== '') {
                    const cells = line.split('|').map(cell => cell.trim()).filter(cell => cell !== '');
                    if (cells.length > 1) {
                        return (
                            <tr key={index} className="md-tr">
                                {cells.map((cell, cellIndex) => (
                                    <td key={cellIndex} className="md-td" dangerouslySetInnerHTML={{ __html: cell }} />
                                ))}
                            </tr>
                        );
                    }
                }
                
                // Empty lines
                if (line.trim() === '') {
                    return <br key={index} />;
                }
                
                // Regular paragraphs
                return <p key={index} className="md-p" dangerouslySetInnerHTML={{ __html: line }} />;
            })
            .filter(element => element !== null);
    };

    return (
        <div className="response-panel">
            <div className="response-header">
                <h2>Analysis Report</h2>
                {analysisResult && (
                    <button onClick={downloadPDF} className="download-btn">
                        Download Report
                    </button>
                )}
            </div>
            
            <div className="response-content">
                {isAnalyzing && (
                    <div className="analyzing-indicator">
                        <div className="beautiful-spinner">
                            <div className="spinner-ring"></div>
                            <div className="spinner-ring"></div>
                            <div className="spinner-ring"></div>
                        </div>
                        <p className="analyzing-text">Analyzing stock data...</p>
                        <p className="analyzing-subtext">Gathering fundamentals, news, and sentiment</p>
                    </div>
                )}
                
                {analysisResult && (
                    <div className="analysis-result">
                        <div className="stock-header">
                            <h3>{analysisResult.report.ticker} - {analysisResult.report.company_name}</h3>
                            <div className="price-info">
                                <span className="price">${analysisResult.report.price_info.current_price.toFixed(2)}</span>
                                <span className={`change ${analysisResult.report.price_info.change >= 0 ? 'positive' : 'negative'}`}>
                                    {analysisResult.report.price_info.change >= 0 ? '+' : ''}
                                    {analysisResult.report.price_info.change.toFixed(2)} ({analysisResult.report.price_info.change_percent}%)
                                </span>
                            </div>
                            <div className="timestamp">
                                Generated: {new Date(analysisResult.report.timestamp).toLocaleString()}
                            </div>
                        </div>
                        
                        {/* Stock Chart Section */}
                        <div className="chart-section">
                            <h4 className="section-title">Chart</h4>
                            <div className="chart-container">
                                <TradingViewChart ticker={analysisResult.report.ticker} />
                            </div>
                        </div>
                        
                        <div className="analysis-content">
                            {/* Analysis Report Section */}
                            <div className="report-section">
                                <h4 className="section-title">Analysis Report</h4>
                                <div className="markdown-content">
                                    {renderMarkdown(analysisResult.report.analysis)}
                                </div>
                            </div>

                            {/* Price Information Section */}
                            <div className="report-section">
                                <h4 className="section-title">Price Information</h4>
                                <div className="price-details">
                                    <div className="price-item">
                                        <span className="label">Current Price:</span>
                                        <span className="value">${analysisResult.report.price_info.current_price.toFixed(2)}</span>
                                    </div>
                                    <div className="price-item">
                                        <span className="label">Change:</span>
                                        <span className={`value ${analysisResult.report.price_info.change >= 0 ? 'positive' : 'negative'}`}>
                                            {analysisResult.report.price_info.change >= 0 ? '+' : ''}${analysisResult.report.price_info.change.toFixed(2)}
                                        </span>
                                    </div>
                                    <div className="price-item">
                                        <span className="label">Change Percent:</span>
                                        <span className={`value ${analysisResult.report.price_info.change_percent >= 0 ? 'positive' : 'negative'}`}>
                                            {analysisResult.report.price_info.change_percent}%
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Reddit Sentiment Section */}
                            {analysisResult.report.reddit_sentiment && (
                                <div className="report-section">
                                    <h4 className="section-title">Reddit Sentiment</h4>
                                    <div className="sentiment-details">
                                        <div className="sentiment-item">
                                            <span className="label">Overall Sentiment:</span>
                                            <span className={`sentiment-badge ${analysisResult.report.reddit_sentiment.sentiment}`}>
                                                {analysisResult.report.reddit_sentiment.sentiment.toUpperCase()}
                                            </span>
                                        </div>
                                        <div className="sentiment-item">
                                            <span className="label">Confidence Score:</span>
                                            <span className="confidence-score">
                                                {(analysisResult.report.reddit_sentiment.confidence * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        {analysisResult.report.reddit_sentiment.summary && (
                                            <div className="sentiment-summary">
                                                <span className="label">Summary:</span>
                                                <p className="summary-text">{analysisResult.report.reddit_sentiment.summary}</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Latest News Section */}
                            {analysisResult.report.news && analysisResult.report.news.length > 0 && (
                                <div className="report-section">
                                    <h4 className="section-title">Latest News</h4>
                                    <div className="news-list">
                                        {analysisResult.report.news.map((article, index) => (
                                            <div key={index} className="news-item">
                                                <div className="news-header">
                                                    <h5 className="news-title">{article.title}</h5>
                                                    <div className="news-meta">
                                                        <span className="news-source">{article.source}</span>
                                                        <span className="news-date">{article.date}</span>
                                                    </div>
                                                </div>
                                                {article.url && (
                                                    <a href={article.url} target="_blank" rel="noopener noreferrer" className="news-link">
                                                        Read more →
                                                    </a>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Fundamentals Section */}
                            {analysisResult.report.fundamentals && Object.keys(analysisResult.report.fundamentals).some(key => analysisResult.report.fundamentals[key] !== null) && (
                                <div className="report-section">
                                    <h4 className="section-title">Fundamentals</h4>
                                    <div className="fundamentals-grid">
                                        {Object.entries(analysisResult.report.fundamentals).map(([key, value], index) => {
                                            if (value !== null && value !== undefined) {
                                                return (
                                                    <div key={index} className="fundamental-item">
                                                        <span className="label">{key.replace(/_/g, ' ').toUpperCase()}:</span>
                                                        <span className="value">{value}</span>
                                                    </div>
                                                );
                                            }
                                            return null;
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
                
                {!isAnalyzing && !analysisResult && (
                    <div className="empty-state">
                        <p>Start a conversation to see analysis results here.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ResponsePanel;