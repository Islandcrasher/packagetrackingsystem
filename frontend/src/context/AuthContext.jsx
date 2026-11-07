import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    localStorage.removeItem("swiftship_token");
    localStorage.removeItem("swiftship_user");

    let active = true;
    api
      .me()
      .then(({ user: current }) => {
        if (!active) return;
        setUser(current);
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function register(payload) {
    const data = await api.register(payload);
    setUser(data.user);
    return data.user;
  }

  async function login(payload) {
    const data = await api.login(payload);
    setUser(data.user);
    return data.user;
  }

  async function logout() {
    setUser(null);
    try {
      await api.logout();
    } catch {
      // The local UI should still log out if the server is unreachable.
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, register, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
