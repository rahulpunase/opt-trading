import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const requestToken = searchParams.get("request_token");
    const status = searchParams.get("status");

    if (!requestToken || status !== "success") {
      navigate("/login?error=1", { replace: true });
      return;
    }

    api
      .authExchange(requestToken)
      .then(() => refresh())
      .then(() => navigate("/", { replace: true }))
      .catch(() => navigate("/login?error=1", { replace: true }));
  }, [searchParams, navigate, refresh]);

  return (
    <div className="flex h-full min-h-screen flex-col items-center justify-center gap-4 bg-bg-base">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      <p className="text-sm text-text-muted">
        Completing authentication…
      </p>
    </div>
  );
}
