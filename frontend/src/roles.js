// Where each role lands after logging in.
export function homePath(user) {
  if (user?.role === "courier") return "/courier/orders";
  return "/orders/new";
}
