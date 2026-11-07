import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

const initialForm = {
  pickup_location: "",
  dropoff_location: "",
  package_details: "",
  delivery_time: "",
};

function pad(value) {
  return String(value).padStart(2, "0");
}

function toDateTimeInputValue(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function CreateOrder() {
  const { logout } = useAuth();

  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [orders, setOrders] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(true);

  const minDeliveryTime = useMemo(
    () => toDateTimeInputValue(new Date(Date.now() + 5 * 60 * 1000)),
    []
  );

  const loadOrders = useCallback(async () => {
    setOrdersLoading(true);
    try {
      const data = await api.listOrders();
      setOrders(data.orders);
    } catch (err) {
      if (err.status === 401) logout();
      else setFormError(err.message);
    } finally {
      setOrdersLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: undefined }));
    setSuccess("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    setSuccess("");
    setErrors({});
    setSubmitting(true);

    try {
      const data = await api.createOrder({
        ...form,
        delivery_time: new Date(form.delivery_time).toISOString(),
      });
      setSuccess(`Order #${data.order.id} scheduled successfully.`);
      setForm(initialForm);
      await loadOrders();
    } catch (err) {
      if (err.status === 401) {
        logout();
        return;
      }
      setErrors(err.details || {});
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="order-layout">
      <section className="card">
        <h2>Create an order</h2>
        <p className="card-subtitle">
          Tell us where to pick up and where it needs to go.
        </p>

        {formError && <div className="alert alert-error">{formError}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="pickup_location">Pickup location</label>
            <input
              id="pickup_location"
              name="pickup_location"
              type="text"
              placeholder="123 Market St, San Francisco"
              value={form.pickup_location}
              onChange={handleChange}
              className={
                errors.pickup_location ? "input input-error" : "input"
              }
            />
            {errors.pickup_location && (
              <span className="field-error">{errors.pickup_location}</span>
            )}
          </div>

          <div className="field">
            <label htmlFor="dropoff_location">Drop-off location</label>
            <input
              id="dropoff_location"
              name="dropoff_location"
              type="text"
              placeholder="500 Mission St, San Francisco"
              value={form.dropoff_location}
              onChange={handleChange}
              className={
                errors.dropoff_location ? "input input-error" : "input"
              }
            />
            {errors.dropoff_location && (
              <span className="field-error">{errors.dropoff_location}</span>
            )}
          </div>

          <div className="field">
            <label htmlFor="package_details">Package details</label>
            <textarea
              id="package_details"
              name="package_details"
              rows="4"
              placeholder="Small box, 2 kg, fragile electronics"
              value={form.package_details}
              onChange={handleChange}
              className={
                errors.package_details ? "input input-error" : "input"
              }
            />
            {errors.package_details && (
              <span className="field-error">{errors.package_details}</span>
            )}
          </div>

          <div className="field">
            <label htmlFor="delivery_time">Delivery time</label>
            <input
              id="delivery_time"
              name="delivery_time"
              type="datetime-local"
              min={minDeliveryTime}
              value={form.delivery_time}
              onChange={handleChange}
              className={errors.delivery_time ? "input input-error" : "input"}
            />
            {errors.delivery_time && (
              <span className="field-error">{errors.delivery_time}</span>
            )}
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={submitting}
          >
            {submitting ? "Scheduling..." : "Schedule delivery"}
          </button>
        </form>
      </section>

      <section className="card orders-card">
        <div className="orders-header">
          <h2>Your orders</h2>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={loadOrders}
            disabled={ordersLoading}
          >
            Refresh
          </button>
        </div>

        {ordersLoading ? (
          <p className="muted">Loading orders...</p>
        ) : orders.length === 0 ? (
          <p className="muted">No orders yet. Schedule your first delivery.</p>
        ) : (
          <ul className="order-list">
            {orders.map((order) => (
              <li key={order.id} className="order-item">
                <div className="order-item-top">
                  <span className="order-id">#{order.id}</span>
                  <span className={`badge badge-${order.status}`}>
                    {order.status}
                  </span>
                </div>
                <p className="order-route">
                  {order.pickup_location} <span aria-hidden="true">-&gt;</span>{" "}
                  {order.dropoff_location}
                </p>
                <p className="order-meta">{order.package_details}</p>
                <p className="order-meta">
                  Delivery: {formatDate(order.delivery_time)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
