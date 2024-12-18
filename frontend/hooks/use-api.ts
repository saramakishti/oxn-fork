import { useState } from "react";
import axios, { AxiosRequestConfig } from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_BACKEND_API_URL, // Base URL from env
  headers: { "Content-Type": "application/json" },
});

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const get = async <T = any>(url: string, config?: AxiosRequestConfig) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<T>(url, config);
      return response.data;
    } catch (err: any) {
      setError(err.message || "An error occurred during GET request");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const post = async <T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post<T>(url, data, config);
      return response.data;
    } catch (err: any) {
      setError(err.message || "An error occurred during POST request");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { get, post, loading, error };
}
