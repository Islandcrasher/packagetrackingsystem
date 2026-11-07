import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Register from "./pages/Register";
import Login from "./pages/Login";
import CreateOrder from "./pages/CreateOrder";
import MyOrders from "./pages/MyOrders";
import OrderDetails from "./pages/OrderDetails";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loader">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function GuestRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loader">Loading...</div>;
  if (user) return <Navigate to="/orders/new" replace />;
  return children;
}

function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <header className="site-header">
      <Link to={user ? "/orders/new" : "/login"} className="brand">
        <span className="brand-mark">S</span>
        SwiftShip
      </Link>

      <nav className="nav">
        {user ? (
          <>
	    <Link to="/orders" classname="nav-link">
		My Orders
	    </Link>
            <span className="nav-user">
              Hi, <strong>{user.name.split(" ")[0]}</strong>
            </span>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={handleLogout}
            >
              Log out
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="nav-link">
              Log in
            </Link>
            <Link to="/register" className="btn btn-primary btn-sm">
              Sign up
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}

export default function App() {
  return (
    <div className="app-shell">
      <Header />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/orders/new" replace />} />
          <Route
            path="/register"
            element={
              <GuestRoute>
                <Register />
              </GuestRoute>
            }
          />
          <Route
            path="/login"
            element={
              <GuestRoute>
                <Login />
              </GuestRoute>
            }
          />
          <Route
            path="/orders/new"
            element={
              <ProtectedRoute>
                <CreateOrder />
              </ProtectedRoute>
            }
          />
	            <Route
            path="/orders"
            element={
              <ProtectedRoute>
                <MyOrders />
              </ProtectedRoute>
            }
          />
          <Route
            path="/orders/:id"
            element={
              <ProtectedRoute>
                <OrderDetails />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
