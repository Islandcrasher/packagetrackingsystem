// Feature #8 - Update Order Status page (courier).
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { NEXT_STATUS, formatDate, statusLabel } from "./courierShared";
import "./courier.css";

const STEPS = ["accepted", "picked_up", "in_transit", "delivered"];

export default function CourierOrderStatus() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .courierOrder(id)
      .then((data) => {
        if (!active) return;
        setOrder(data.order);
        setHistory(data.history);
      })
      .catch((e) => active && setError(e.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [id]);

  async function handleUpdate(status) {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const data = await api.updateOrderStatus(id, status);
      setOrder(data.order);
      setHistory(data.history);
      setNotice(data.message);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="page-loader">Loading...</div>;

  if (!order) {
    return (
      <div className="courier-page">
        <Link to="/courier/orders">← Back to assigned orders</Link>
        <div className="alert alert-error" style={{ marginTop: 16 }}>
          {error || "Order not found"}
        </div>
      </div>
    );
  }

  const next = NEXT_STATUS[order.status];
  const currentIndex = STEPS.indexOf(order.status);

  return (
    <div className="courier-page">
      <Link to="/courier/orders">← Back to assigned orders</Link>

      <section className="card" style={{ marginTop: 16 }}>
        <div className="courier-card-top">
          <h2 style={{ margin: 0 }}>Order #{order.id}</h2>
          <span className={`badge badge-${order.status}`}>{statusLabel(order.status)}</span>
        </div>

        {error && <div className="alert alert-error" style={{ marginTop: 16 }}>{error}</div>}
        {notice && <div className="alert alert-success" style={{ marginTop: 16 }}>{notice}</div>}

        {currentIndex >= 0 && (
          <ol className="stepper">
            {STEPS.map((s, i) => (
              <li key={s} className={i <= currentIndex ? "step step-done" : "step"}>
                {statusLabel(s)}
              </li>
            ))}
          </ol>
        )}

        <dl className="detail-grid">
          <dt>Pickup</dt>
          <dd>{order.pickup_location}</dd>
          <dt>Drop-off</dt>
          <dd>{order.dropoff_location}</dd>
          <dt>Package</dt>
          <dd>{order.package_details}</dd>
          <dt>Delivery time</dt>
          <dd>{formatDate(order.delivery_time)}</dd>
          <dt>Customer</dt>
          <dd>
            {order.customer_name}
            {order.customer_phone && (
              <>
                {" "}
                · <a href={`tel:${order.customer_phone}`}>{order.customer_phone}</a>
              </>
            )}
          </dd>
        </dl>

        <div className="courier-actions">
          {next && (
            <button
              type="button"
              className="btn btn-primary"
              disabled={saving}
              onClick={() => handleUpdate(next)}
            >
              {saving ? "Updating..." : `Mark as ${statusLabel(next)}`}
            </button>
          )}
          {order.status === "pending" && (
            <p className="muted" style={{ margin: 0 }}>
              Accept this order from the <Link to="/courier/orders">assigned orders</Link> page
              before updating its status.
            </p>
          )}
          {order.status === "delivered" && (
            <p className="muted" style={{ margin: 0 }}>This order has been delivered. 🎉</p>
          )}
          {order.status === "cancelled" && (
            <p className="muted" style={{ margin: 0 }}>This order was cancelled by the customer.</p>
          )}
        </div>
      </section>

      {history.length > 0 && (
        <section className="card" style={{ marginTop: 20 }}>
          <h2>Status history</h2>
          <ul className="history-list">
            {history.map((h) => (
              <li key={h.id}>
                <strong>{statusLabel(h.status)}</strong>
                <span className="muted">{formatDate(h.changed_at)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
