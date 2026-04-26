import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-[var(--color-bg-base)]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent" />
      </div>
    );
  }

  return user?.authenticated ? <Outlet /> : <Navigate to="/login" replace />;
}
