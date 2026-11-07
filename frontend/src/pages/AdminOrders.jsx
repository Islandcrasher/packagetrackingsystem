import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import "./admin.css";

const STATUSES = ["pending", "accepted", "picked_up", "in_transit", "delivered", "cancelled"];

export default function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const [couriers, setCouriers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(async () => {
    setError("");
    try {
      const [orderData, courierData] = await Promise.all([api.adminOrders(), api.adminCouriers()]);
      setOrders(orderData.orders); setCouriers(courierData.couriers);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function changeStatus(order, status) {
    setBusy(`status-${order.id}`); setError(""); setNotice("");
    try {
      const { order: updated } = await api.adminUpdateOrderStatus(order.id, status);
      setOrders((old) => old.map((item) => item.id === order.id ? updated : item));
      setNotice(`Order #${order.id} status updated.`);
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  }
  async function changeCourier(order, value) {
    if (!value) return;
    const courierId = Number(value);
    if (order.courier_id && order.courier_id !== courierId && !window.confirm(`Reassign order #${order.id} to this courier?`)) return;
    setBusy(`courier-${order.id}`); setError(""); setNotice("");
    try {
      const { order: updated } = await api.adminAssignCourier(order.id, courierId);
      setOrders((old) => old.map((item) => item.id === order.id ? updated : item));
      setNotice(`Courier assigned to order #${order.id}.`);
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  }
  async function deleteOrder(order) {
    if (!window.confirm(`Delete order #${order.id}? This cannot be undone.`)) return;
    setBusy(`delete-${order.id}`); setError(""); setNotice("");
    try {
      await api.adminDeleteOrder(order.id);
      setOrders((old) => old.filter((item) => item.id !== order.id));
      setNotice(`Order #${order.id} deleted.`);
    } catch (e) { setError(e.message); }
    finally { setBusy(""); }
  }
  if (loading) return <div className="page-loader">Loading orders...</div>;
  return (
    <section className="admin-page">
      <div className="admin-heading"><div><p className="admin-eyebrow">ADMINISTRATION</p><h1>Manage orders</h1><p className="muted">Review deliveries, update status, and manage courier assignments.</p></div><button className="btn btn-ghost" type="button" onClick={load}>Refresh</button></div>
      {error && <div className="alert alert-error">{error}</div>}{notice && <div className="alert alert-success">{notice}</div>}
      <div className="admin-summary"><strong>{orders.length}</strong><span>total orders</span><strong>{couriers.length}</strong><span>available couriers</span></div>
      <div className="admin-table-wrap"><table className="admin-table">
        <thead><tr><th>Order</th><th>Customer</th><th>Route &amp; package</th><th>Delivery time</th><th>Status</th><th>Assigned courier</th><th>Actions</th></tr></thead>
        <tbody>{orders.map((order) => {
          const rowBusy = busy.endsWith(`-${order.id}`);
          const terminal = ["delivered", "cancelled"].includes(order.status);
          return <tr key={order.id}>
            <td><strong>#{order.id}</strong><small>{order.created_at}</small></td>
            <td>{order.customer_name}<small>{order.customer_email}</small></td>
            <td>{order.pickup_location} → {order.dropoff_location}<small>{order.package_details}</small></td>
            <td>{order.delivery_time}</td>
            <td><select aria-label={`Status for order ${order.id}`} className="input admin-select" value={order.status} disabled={rowBusy} onChange={(e) => changeStatus(order, e.target.value)}>{STATUSES.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></td>
            <td><select aria-label={`Courier for order ${order.id}`} className="input admin-select" value={order.courier_id || ""} disabled={rowBusy || terminal || couriers.length === 0} onChange={(e) => changeCourier(order, e.target.value)}><option value="">Unassigned</option>{couriers.map((courier) => <option value={courier.id} key={courier.id}>{courier.name} · {courier.email}</option>)}</select>{order.assigned_courier_phone && <small>{order.assigned_courier_phone}</small>}</td>
            <td><button className="btn btn-danger btn-sm" type="button" disabled={rowBusy} onClick={() => deleteOrder(order)}>{busy === `delete-${order.id}` ? "Deleting…" : "Delete"}</button></td>
          </tr>;
        })}</tbody>
      </table>{orders.length === 0 && <p className="admin-empty">There are no orders to display.</p>}</div>
    </section>
  );
}
