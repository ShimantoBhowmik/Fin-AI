export interface Message {
    id: string;
    content: string;
    sender: 'user' | 'bot';
    timestamp: Date;
}

export interface Response {
    id: string;
    content: string;
    timestamp: Date;
}

export interface StatusUpdate {
    status: string;
    timestamp: Date;
}