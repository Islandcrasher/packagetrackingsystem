# Courier features (#7 Assigned Orders, #8 Update Order Status)

## Run

```bash
# backend
cd backend
python -m venv venv && venv\Scripts\activate      # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python seed_demo.py        # creates a demo courier + customer + 3 assigned orders
python app.py              # http://127.0.0.1:5000

# frontend (new terminal)
cd frontend
npm install
npm run dev                # http://localhost:5173
```

Demo accounts: `courier@swiftship.com / Courier@123` and `customer@swiftship.com / Customer@123`.

Tests: `cd backend && python -m unittest test_courier -v`

## API (all need the login cookie, role = courier)

| Method | Endpoint | Feature |
|---|---|---|
| GET | `/api/courier/<courier_id>/orders` | #7 orders assigned to a courier |
| GET | `/api/courier/orders/<id>` | #7/#8 one order + status history |
| POST | `/api/courier/orders/<id>/accept` | #7 accept (`pending` -> `accepted`) |
| POST | `/api/courier/orders/<id>/decline` | #7 decline (order returns to the admin) |
| PATCH | `/api/courier/orders/<id>/status` body `{"status": "picked_up"}` | #8 |

Status flow: `pending -> accepted -> picked_up -> in_transit -> delivered` (one step at a time).
Every change is stored in the `order_status_history` table.

## For the Admin features (#9 / #10)

* `users.role` is `user` (default), `courier` or `admin`.
* To assign an order to a courier set `orders.courier_id` (leave `status = 'pending'`; the courier
  then accepts or declines). `courier_name` / `courier_phone` are filled automatically on accept.
* From the command line: `python seed_demo.py assign ORDER_ID courier@swiftship.com`
  and `python seed_demo.py make-courier someone@example.com`.
