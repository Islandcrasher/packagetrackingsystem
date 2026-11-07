import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function MyOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listOrders()
      .then(({ orders }) => setOrders(orders))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading...</p>;
  if (error) return <p>{error}</p>;

  return (
    <div>
      <h1>My Orders</h1>
      {orders.length === 0 && <p>You have no orders yet.</p>}
      {orders.map((o) => (
        <div key={o.id}>
          <p>
            {o.pickup_location} → {o.dropoff_location}
          </p>
          <p>Status: {o.status}</p>
          <Link to={`/orders/${o.id}`}>View details</Link>
        </div>
      ))}
    </div>
  );
}
