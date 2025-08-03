import React from 'react';
import { Message } from '../../types';

interface MessageListProps {
    messages: Message[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
    return (
        <div className="message-list">
            {messages.map((message) => (
                <div key={message.id} className={`message ${message.sender}`}>
                    <div className="message-avatar">
                        {message.sender === 'user' ? 'U' : 'B'}
                    </div>
                    <div className="message-content">
                        {message.content}
                    </div>
                </div>
            ))}
            {messages.length === 0 && (
                <div className="empty-chat">
                    <p>Hi, I am Finance Bro, your personal finance assistant! How can I help you today?</p>
                </div>
            )}
        </div>
    );
};

export default MessageList;