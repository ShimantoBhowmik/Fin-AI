import React, { useState } from 'react';

interface MessageInputProps {
    onSendMessage: (message: string) => void;
    disabled?: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({ onSendMessage, disabled = false }) => {
    const [message, setMessage] = useState('');

    const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        console.log('Input change:', event.target.value);
        setMessage(event.target.value);
    };

    const handleSend = () => {
        console.log('Send clicked, message:', message);
        if (message.trim() && !disabled) {
            onSendMessage(message);
            setMessage('');
        }
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter' && !disabled) {
            handleSend();
        }
    };

    return (
        <div className="message-input">
            <input
                type="text"
                value={message}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                onFocus={() => console.log('Input focused')}
                onClick={() => console.log('Input clicked')}
                placeholder={disabled ? "Analysis in progress..." : "Type your message..."}
                disabled={disabled}
                className={disabled ? "disabled" : ""}
                style={{ zIndex: 1000, position: 'relative' }}
            />
            <button onClick={handleSend} disabled={disabled}>
                {disabled ? "Analyzing..." : "Send"}
            </button>
        </div>
    );
};

export default MessageInput;