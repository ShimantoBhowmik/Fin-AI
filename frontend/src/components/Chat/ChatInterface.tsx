import React, { useState } from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { Message } from '../../types';

interface ChatInterfaceProps {
  onNewQuery: (query: string) => void;
  isAnalyzing: boolean;
  analysisComplete?: boolean;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onNewQuery, isAnalyzing, analysisComplete }) => {
    const [messages, setMessages] = useState<Message[]>([]);

    // Add completion message when analysis is done
    React.useEffect(() => {
        if (analysisComplete && !isAnalyzing) {
            const completionMessage: Message = {
                id: `completion-${Date.now()}`,
                content: '✅ Analysis complete! Check the report on the right panel.',
                sender: 'bot',
                timestamp: new Date()
            };
            
            setMessages((prevMessages) => {
                // Check if completion message already exists
                const hasCompletionMessage = prevMessages.some(msg => 
                    msg.content.includes('Analysis complete!') && msg.sender === 'bot'
                );
                
                if (!hasCompletionMessage) {
                    return [...prevMessages, completionMessage];
                }
                return prevMessages;
            });
        }
    }, [analysisComplete, isAnalyzing]);

    const handleSendMessage = async (content: string) => {
        const newMessage: Message = { 
            id: Date.now().toString(),
            content, 
            sender: 'user',
            timestamp: new Date()
        };
        
        setMessages((prevMessages) => [...prevMessages, newMessage]);
        
        // Notify parent component about new query
        onNewQuery(content);
        
        // Add a bot message indicating analysis has started
        const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: 'Starting analysis...',
            sender: 'bot',
            timestamp: new Date()
        };
        setMessages((prevMessages) => [...prevMessages, botMessage]);
    };

    return (
        <div className="chat-interface">
            <div className="chat-header">
                <h2>Finance Bro Final Boss</h2>
            </div>
            <MessageList messages={messages} />
            <MessageInput onSendMessage={handleSendMessage} disabled={isAnalyzing} />
        </div>
    );
};

export default ChatInterface;