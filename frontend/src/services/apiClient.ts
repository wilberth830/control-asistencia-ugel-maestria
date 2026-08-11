/** TEC-D04 — Axios base toward /api/v1 */
import axios from "axios";

export const SESSION_EXPIRED_EVENT = "chiquistrukis:session-expired";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token") ?? sessionStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const isLoginRequest =
        error.config?.method?.toLowerCase() === "post" &&
        error.config.url === "/api/v1/auth/sessions";
      const hasActiveToken = Boolean(
        localStorage.getItem("token") ?? sessionStorage.getItem("token"),
      );

      if (hasActiveToken && !isLoginRequest) {
        window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
      }
    }
    return Promise.reject(error);
  },
);

export default apiClient;
