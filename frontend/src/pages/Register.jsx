import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const initialForm = { name: "", email: "", phone: "", password: "" };

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: undefined }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    setErrors({});
    setSubmitting(true);

    try {
      await register(form);
      navigate("/orders/new", { replace: true });
    } catch (err) {
      setErrors(err.details || {});
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-layout">
      <section className="hero">
        <h1>Deliveries, without the drama.</h1>
        <p>
          Create an account, schedule a pickup, and track every package from door
          to door.
        </p>
        <ul className="hero-points">
          <li>Same-day and scheduled pickups</li>
          <li>Live order history</li>
          <li>Secure, hashed passwords</li>
        </ul>
      </section>

      <section className="card">
        <h2>Create your account</h2>
        <p className="card-subtitle">It only takes a minute.</p>

        {formError && <div className="alert alert-error">{formError}</div>}

        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="name">Full name</label>
            <input
              id="name"
              name="name"
              type="text"
              autoComplete="name"
              placeholder="Jane Doe"
              value={form.name}
              onChange={handleChange}
              className={errors.name ? "input input-error" : "input"}
            />
            {errors.name && <span className="field-error">{errors.name}</span>}
          </div>

          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              placeholder="jane@example.com"
              value={form.email}
              onChange={handleChange}
              className={errors.email ? "input input-error" : "input"}
            />
            {errors.email && <span className="field-error">{errors.email}</span>}
          </div>

          <div className="field">
            <label htmlFor="phone">Phone number</label>
            <input
              id="phone"
              name="phone"
              type="tel"
              autoComplete="tel"
              placeholder="+1 555 123 4567"
              value={form.phone}
              onChange={handleChange}
              className={errors.phone ? "input input-error" : "input"}
            />
            {errors.phone && <span className="field-error">{errors.phone}</span>}
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              placeholder="At least 8 characters"
              value={form.password}
              onChange={handleChange}
              className={errors.password ? "input input-error" : "input"}
            />
            {errors.password && (
              <span className="field-error">{errors.password}</span>
            )}
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="switch-auth">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </section>
    </div>
  );
}
