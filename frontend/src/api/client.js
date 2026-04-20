const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api";

function getMessageFromResponse(data, fallback) {
  if (!data) {
    return fallback;
  }
  if (typeof data === "string") {
    return data;
  }
  if (data.detail) {
    return data.detail;
  }
  const firstKey = Object.keys(data)[0];
  if (!firstKey) {
    return fallback;
  }
  const firstValue = data[firstKey];
  if (Array.isArray(firstValue)) {
    return `${firstKey}: ${firstValue.join(", ")}`;
  }
  return `${firstKey}: ${String(firstValue)}`;
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(getMessageFromResponse(data, "Request failed"));
  }

  return data;
}

export { API_BASE_URL };
