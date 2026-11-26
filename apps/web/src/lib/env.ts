/** Public browser-safe configuration. Never store secrets in NEXT_PUBLIC_* variables. */
export const publicEnv = {
  apiBaseUrl:
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000",
  wsBaseUrl:
    process.env.NEXT_PUBLIC_WS_BASE_URL?.replace(/\/$/, "") ||
    "ws://127.0.0.1:8000",
  appEnv: process.env.NEXT_PUBLIC_APP_ENV || "development",
} as const;
