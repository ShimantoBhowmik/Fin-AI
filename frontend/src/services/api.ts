import axios, { AxiosError } from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Backend API URL

export const fetchMessages = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/messages`);
        return response.data;
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        throw new Error('Error fetching messages: ' + errorMessage);
    }
};

export const sendMessage = async (message: string) => {
    try {
        const response = await axios.post(`${API_BASE_URL}/analyze`, { query: message });
        return response.data;
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        throw new Error('Error sending message: ' + errorMessage);
    }
};

export const fetchStatusUpdates = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/status`);
        return response.data;
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        throw new Error('Error fetching status updates: ' + errorMessage);
    }
};