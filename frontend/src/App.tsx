import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { WsProvider } from "@/lib/ws";
import { AuthProvider } from "@/lib/auth";
import ProtectedRoute from "@/router";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import AuthCallback from "@/pages/AuthCallback";
import Dashboard from "@/pages/Dashboard";
import Strategies from "@/pages/Strategies";
import Positions from "@/pages/Positions";
import Trades from "@/pages/Trades";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <WsProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/strategies" element={<Strategies />} />
                <Route path="/positions" element={<Positions />} />
                <Route path="/trades" element={<Trades />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </WsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
