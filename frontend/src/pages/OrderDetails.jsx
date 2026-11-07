import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";

export default function OrderDetails() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getOrder(id)
      .then(({ order }) => setOrder(order))
      .catch((e) => setError(e.message));
  }, [id]);

  const handleCancel = async () => {
    if (!window.confirm("Cancel this order?")) return;
    try {
      const { order: updated } = await api.cancelOrder(id);
      setOrder(updated);
    } catch (e) {
      setError(e.message);
    }
  };

  if (error) return <p>{error}</p>;
  if (!order) return <p>Loading...</p>;

  return (
    <div>
      <Link to="/orders">← Back to my orders</Link>
      <h1>Order #{order.id}</h1>
      <p>Status: {order.status}</p>
      <p>Pickup: {order.pickup_location}</p>
      <p>Drop-off: {order.dropoff_location}</p>
      <p>Package: {order.package_details}</p>
      <p>Delivery time: {new Date(order.delivery_time).toLocaleString()}</p>
      <p>
        Courier:{" "}
        {order.courier_name
          ? `${order.courier_name} (${order.courier_phone})`
          : "Not assigned yet"}
      </p>
      {order.status === "pending" && (
        <button onClick={handleCancel}>Cancel order</button>
      )}
    </div>
  );
}
