async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };

  let response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers,
      credentials: "include",
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Cannot reach the server");
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const err = new Error(data?.error || "Something went wrong");
    err.status = response.status;
    err.details = data?.details || {};
    throw err;
  }

  return data;
}

export const api = {
  register: (payload) =>
    request("/auth/register", { method: "POST", body: payload }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request("/auth/me"),
  createOrder: (payload) =>
    request("/orders", { method: "POST", body: payload }),
  listOrders: () => request("/orders"),
  getOrder: (id) => request(`/orders/${id}`),
  cancelOrder: (id) => request(`/orders/${id}/cancel`, { method: "POST" }),
};
