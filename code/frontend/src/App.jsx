import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";

import "./App.css";
import apiClient from "./api/client.js";
import {
  createTrial,
  deleteTrial,
  fetchTrials,
  updateTrial,
} from "./features/trials/trialsSlice.js";

function Navigation() {
  return (
    <header className="site-header">
      <div>
        <p className="eyebrow">Haozhe Wang · DATA 260 · HW5</p>
        <h1>Clinical Trial Registry</h1>
      </div>
      <nav>
        <Link to="/">Home</Link>
        <Link to="/create">Create Trial</Link>
        <Link to="/login">Login</Link>
      </nav>
    </header>
  );
}

function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("hw4test20260926@example.com");
  const [password, setPassword] = useState("TestPass123!");
  const [message, setMessage] = useState("");

  async function handleLogin(event) {
    event.preventDefault();

    try {
      await apiClient.post("/auth/login", { email, password });
      navigate("/");
    } catch (error) {
      setMessage(error.response?.data?.detail || error.message);
    }
  }

  return (
    <main className="page narrow-page">
      <section className="card">
        <p className="eyebrow">Secure MySQL session</p>
        <h2>Login</h2>
        <form onSubmit={handleLogin} className="form-grid">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button type="submit">Login</button>
        </form>
        {message && <p className="error-banner">{message}</p>}
      </section>
    </main>
  );
}

function Home() {
  const dispatch = useDispatch();
  const { items, loading, error } = useSelector((state) => state.trials);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (items.length === 0) {
      dispatch(fetchTrials());
    }
  }, [dispatch, items.length]);

  async function handleDelete(id) {
    if (!window.confirm(`Delete Trial ${id}?`)) {
      return;
    }

    try {
      await dispatch(deleteTrial(id)).unwrap();
      setMessage(`Deleted Trial ${id}. Redux state updated automatically.`);
    } catch {
      setMessage("");
    }
  }

  return (
    <main className="page">
      <section className="summary-row">
        <div>
          <p className="eyebrow">Redux Toolkit state</p>
          <h2>Trial Home</h2>
          <p>Showing {items.length} records from FastAPI + MySQL.</p>
        </div>
        <div className="summary-actions">
          <button
            className="secondary"
            onClick={() => dispatch(fetchTrials())}
            disabled={loading}
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
          <Link className="button-link" to="/create">
            Create Trial
          </Link>
        </div>
      </section>

      {error && <p className="error-banner">{error}</p>}
      {message && <p className="success-banner">{message}</p>}

      <section className="table-card">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>NCT Code</th>
              <th>Title</th>
              <th>Participants</th>
              <th>Sponsor</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((trial) => (
              <tr key={trial.id}>
                <td>{trial.id}</td>
                <td><code>{trial.nct_code}</code></td>
                <td>{trial.brief_title}</td>
                <td>{trial.participant_count}</td>
                <td>{trial.sponsor}</td>
                <td className="row-actions">
                  <Link to={`/update/${trial.id}`}>Update</Link>
                  <button
                    className="danger-link"
                    onClick={() => handleDelete(trial.id)}
                    disabled={loading}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}

function TrialForm({ heading, submitLabel, initialValues, onSubmit, loading }) {
  const [form, setForm] = useState(initialValues);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    onSubmit({
      brief_title: form.brief_title,
      nct_code: form.nct_code,
      participant_count: Number(form.participant_count),
      sponsor_id: Number(form.sponsor_id),
    });
  }

  return (
    <section className="card">
      <p className="eyebrow">Redux async thunk + Axios</p>
      <h2>{heading}</h2>
      <form onSubmit={handleSubmit} className="form-grid two-column-form">
        <label className="wide-field">
          Brief title
          <input
            name="brief_title"
            value={form.brief_title}
            onChange={updateField}
            minLength="1"
            maxLength="500"
            required
          />
        </label>
        <label>
          NCT code
          <input
            name="nct_code"
            value={form.nct_code}
            onChange={updateField}
            pattern="NCT[0-9]{8}"
            placeholder="NCT85611001"
            required
          />
        </label>
        <label>
          Participant count
          <input
            name="participant_count"
            type="number"
            min="0"
            value={form.participant_count}
            onChange={updateField}
            required
          />
        </label>
        <label>
          Sponsor ID
          <input
            name="sponsor_id"
            type="number"
            min="1"
            value={form.sponsor_id}
            onChange={updateField}
            required
          />
        </label>
        <div className="form-actions wide-field">
          <button type="submit" disabled={loading}>
            {loading ? "Saving…" : submitLabel}
          </button>
          <Link to="/">Cancel</Link>
        </div>
      </form>
    </section>
  );
}

const blankTrial = {
  brief_title: "HW5 Redux Trial by Haozhe Wang",
  nct_code: "NCT85611001",
  participant_count: 150,
  sponsor_id: 1,
};

function CreateRecord() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error } = useSelector((state) => state.trials);

  async function handleCreate(trialData) {
    try {
      await dispatch(createTrial(trialData)).unwrap();
      navigate("/");
    } catch {
      // Redux stores and displays the API error.
    }
  }

  return (
    <main className="page narrow-page">
      {error && <p className="error-banner">{error}</p>}
      <TrialForm
        heading="Create Trial"
        submitLabel="Create Trial"
        initialValues={blankTrial}
        onSubmit={handleCreate}
        loading={loading}
      />
    </main>
  );
}

function UpdateRecord() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { id } = useParams();
  const { items, loading, error } = useSelector((state) => state.trials);
  const selected = items.find((trial) => trial.id === Number(id));
  const initialValues = selected
    ? {
        brief_title: selected.brief_title,
        nct_code: selected.nct_code,
        participant_count: selected.participant_count,
        sponsor_id: selected.sponsor_id,
      }
    : blankTrial;

  async function handleUpdate(trialData) {
    try {
      await dispatch(updateTrial({ id: Number(id), trialData })).unwrap();
      navigate("/");
    } catch {
      // Redux stores and displays the API error.
    }
  }

  return (
    <main className="page narrow-page">
      {error && <p className="error-banner">{error}</p>}
      <TrialForm
        heading={`Update Trial ${id}`}
        submitLabel="Update Trial"
        initialValues={initialValues}
        onSubmit={handleUpdate}
        loading={loading}
      />
    </main>
  );
}

function DeleteRecord() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { id } = useParams();
  const { loading, error } = useSelector((state) => state.trials);

  async function handleDelete() {
    try {
      await dispatch(deleteTrial(Number(id))).unwrap();
      navigate("/");
    } catch {
      // Redux stores and displays the API error.
    }
  }

  return (
    <main className="page narrow-page">
      <section className="card">
        <p className="eyebrow">Compatibility route</p>
        <h2>Delete Trial {id}</h2>
        <p>Delete buttons are also available beside every Home row.</p>
        {error && <p className="error-banner">{error}</p>}
        <button className="danger" onClick={handleDelete} disabled={loading}>
          {loading ? "Deleting…" : "Delete Trial"}
        </button>
      </section>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Navigation />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/create" element={<CreateRecord />} />
        <Route path="/update/:id" element={<UpdateRecord />} />
        <Route path="/delete/:id" element={<DeleteRecord />} />
      </Routes>
    </BrowserRouter>
  );
}
