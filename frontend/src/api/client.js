const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api";
const API_ROOT = API_BASE_URL.replace(/\/api\/?$/, "");

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
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const baseHeaders = isFormData ? {} : { "Content-Type": "application/json" };
  const mergedHeaders = {
    ...baseHeaders,
    ...(options.headers || {}),
  };
  const fetchOptions = {
    ...options,
    headers: mergedHeaders,
  };

  const response = await fetch(`${API_BASE_URL}${path}`, fetchOptions);

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      data = text;
    }
  }

  if (!response.ok) {
    throw new Error(getMessageFromResponse(data, "Request failed"));
  }

  return data;
}

export function toAbsoluteMediaUrl(maybeRelativeUrl) {
  if (!maybeRelativeUrl) {
    return null;
  }
  if (maybeRelativeUrl.startsWith("http://") || maybeRelativeUrl.startsWith("https://")) {
    return maybeRelativeUrl;
  }
  if (maybeRelativeUrl.startsWith("/")) {
    return `${API_ROOT}${maybeRelativeUrl}`;
  }
  return `${API_ROOT}/${maybeRelativeUrl}`;
}

export { API_BASE_URL };
