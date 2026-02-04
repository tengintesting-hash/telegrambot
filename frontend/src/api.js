const API_BASE = import.meta.env.VITE_API_BASE || "/api";

const getInitData = () => {
  if (window.Telegram?.WebApp?.initData) {
    return window.Telegram.WebApp.initData;
  }
  return "";
};

const apiRequest = async (path, options = {}) => {
  const initData = getInitData();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    "X-Telegram-Init-Data": initData,
  };
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Request failed");
  }
  return response.json();
};

export const authTelegram = (initData) =>
  apiRequest("/auth/telegram", {
    method: "POST",
    body: JSON.stringify({ initData }),
  });

export const fetchMe = () => apiRequest("/me");

export const fetchTasks = () => apiRequest("/tasks");

export const completeTask = (id) =>
  apiRequest(`/tasks/${id}/complete`, { method: "POST" });

export const fetchReferrals = () => apiRequest("/referrals");

export const fetchUsers = () => apiRequest("/admin/users");

export const setBanUser = (id, is_banned) =>
  apiRequest(`/admin/user/${id}/ban`, {
    method: "POST",
    body: JSON.stringify({ is_banned }),
  });
