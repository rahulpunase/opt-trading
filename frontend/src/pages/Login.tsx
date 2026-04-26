import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [searchParams] = useSearchParams();
  const hasError = searchParams.get("error") === "1";

  const handleLogin = async () => {
    setLoading(true);
    try {
      const { login_url } = await api.authLoginUrl();
      window.location.href = login_url;
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full min-h-screen items-center justify-center bg-[var(--color-bg-base)]">
      <div className="w-full max-w-sm rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg-surface)] p-8 shadow-2xl">
        {/* Logo / brand */}
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex h-14 w-14 items-center justify-center rounded-xl bg-[var(--color-accent)]/10">
            <svg
              className="h-8 w-8 text-[var(--color-accent)]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 3v1.5M3 21v-6m0 0 2.77-.693a9 9 0 0 1 6.208.682l.108.054a9 9 0 0 0 6.086.71l3.114-.732a48.524 48.524 0 0 1-.005-10.499l-3.11.732a9 9 0 0 1-6.085-.711l-.108-.054a9 9 0 0 0-6.208-.682L3 4.5M3 15V4.5"
              />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">
            Kite Trader Platform
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Connect your Zerodha account to continue
          </p>
        </div>

        {hasError && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            Authentication failed. Please try again.
          </div>
        )}

        <button
          onClick={handleLogin}
          disabled={loading}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--color-accent)] px-4 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {loading ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 10.5V6.75a4.5 4.5 0 1 1 9 0v3.75M3.75 21.75h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H3.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
            </svg>
          )}
          {loading ? "Redirecting to Kite…" : "Login with Kite Connect"}
        </button>

        <p className="mt-6 text-center text-xs text-[var(--color-text-muted)]">
          You'll be redirected to Zerodha to authenticate.
          <br />
          No credentials are stored by this platform.
        </p>
      </div>
    </div>
  );
}
