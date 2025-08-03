import { useState, useEffect } from 'react';
import axios, { AxiosError } from 'axios';

interface UseApiReturn {
    data: any;
    loading: boolean;
    error: AxiosError | null;
    fetchData: (endpoint: string) => Promise<void>;
    updateData: (endpoint: string, payload: any) => Promise<void>;
}

const useApi = (baseURL: string): UseApiReturn => {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<AxiosError | null>(null);

    const fetchData = async (endpoint: string): Promise<void> => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get(`${baseURL}${endpoint}`);
            setData(response.data);
        } catch (err) {
            setError(err as AxiosError);
        } finally {
            setLoading(false);
        }
    };

    const updateData = async (endpoint: string, payload: any): Promise<void> => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.put(`${baseURL}${endpoint}`, payload);
            setData(response.data);
        } catch (err) {
            setError(err as AxiosError);
        } finally {
            setLoading(false);
        }
    };

    return { data, loading, error, fetchData, updateData };
};

export default useApi;