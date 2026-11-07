// Feature #7 - Assigned Orders page (courier): list, accept or decline.
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import { formatDate, statusLabel } from "./courierShared";
import "./courier.css";

const ACTIVE = ["accepted", "picked_up", "in_transit"];

export default function CourierOrders() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await api.courierOrders(user.id);
      setOrders(data.orders);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [user.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleAccept(order) {
    setBusyId(order.id);
    setError("");
    setNotice("");
    try {
      const { order: updated } = await api.acceptOrder(order.id);
      setOrders((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
      setNotice(`Order #${order.id} accepted.`);
    } catch (e) {
      setError(e.message);
      load();
    } finally {
      setBusyId(null);
    }
  }

  async function handleDecline(order) {
    if (!window.confirm(`Decline order #${order.id}?`)) return;
    setBusyId(order.id);
    setError("");
    setNotice("");
    try {
      await api.declineOrder(order.id);
      setOrders((prev) => prev.filter((o) => o.id !== order.id));
      setNotice(`Order #${order.id} declined.`);
    } catch (e) {
      setError(e.message);
      load();
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <div className="page-loader">Loading...</div>;

  const awaiting = orders.filter((o) => o.status === "pending");
  const active = orders.filter((o) => ACTIVE.includes(o.status));
  const done = orders.filter((o) => o.status === "delivered" || o.status === "cancelled");

  function renderCard(order) {
    const busy = busyId === order.id;
    return (
      <li key={order.id} className="courier-card">
        <div className="courier-card-top">
          <span className="order-id">Order #{order.id}</span>
          <span className={`badge badge-${order.status}`}>{statusLabel(order.status)}</span>
        </div>
        <p className="order-route">
          {order.pickup_location} → {order.dropoff_location}
        </p>
        <p className="order-meta">Package: {order.package_details}</p>
        <p className="order-meta">Delivery time: {formatDate(order.delivery_time)}</p>
        <p className="order-meta">
          Customer: {order.customer_name}
          {order.customer_phone && (
            <>
              {" "}
              · <a href={`tel:${order.customer_phone}`}>{order.customer_phone}</a>
            </>
          )}
        </p>

        <div className="courier-actions">
          {order.status === "pending" && (
            <>
              <button
                type="button"
                className="btn btn-success btn-sm"
                disabled={busy}
                onClick={() => handleAccept(order)}
              >
                {busy ? "Please wait..." : "Accept"}
              </button>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                disabled={busy}
                onClick={() => handleDecline(order)}
              >
                Decline
              </button>
            </>
          )}
          {ACTIVE.includes(order.status) && (
            <Link to={`/courier/orders/${order.id}`} className="btn btn-primary btn-sm btn-link">
              Update status
            </Link>
          )}
          {(order.status === "delivered" || order.status === "cancelled") && (
            <Link to={`/courier/orders/${order.id}`} className="btn btn-ghost btn-sm btn-link">
              View details
            </Link>
          )}
        </div>
      </li>
    );
  }

  function renderSection(title, list) {
    if (list.length === 0) return null;
    return (
      <section className="courier-section">
        <h3>
          {title} ({list.length})
        </h3>
        <ul className="courier-list">{list.map(renderCard)}</ul>
      </section>
    );
  }

  return (
    <div className="courier-page">
      <div className="courier-head">
        <div>
          <h1>Assigned Orders</h1>
          <p>Accept or decline the orders assigned to you.</p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={load}>
          Refresh
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      {orders.length === 0 && !error && (
        <div className="card courier-empty">No orders are assigned to you yet.</div>
      )}

      {renderSection("Waiting for your response", awaiting)}
      {renderSection("In progress", active)}
      {renderSection("Completed", done)}
    </div>
  );
}
