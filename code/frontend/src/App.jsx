import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Link,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }

  return data;
}

function Navigation() {
  return (
    <nav>
      <Link to="/">Home</Link>{" | "}
      <Link to="/create">Create Trial</Link>{" | "}
      <Link to="/update/1">Update Trial</Link>{" | "}
      <Link to="/delete/1">Delete Trial</Link>{" | "}
      <Link to="/login">Login</Link>
    </nav>
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
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      navigate("/");
    } catch (error) {
      setMessage(error.message);
    }
  }

  return (
    <main>
      <h1>Clinical Trials Login</h1>

      <form onSubmit={handleLogin}>
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email"
        />

        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
        />

        <button type="submit">Login</button>
      </form>

      {message && <p>{message}</p>}
    </main>
  );
}

function Home() {
  const [trials, setTrials] = useState([]);
  const [message, setMessage] = useState("");

  async function loadTrials() {
    try {
      const data = await api("/api/trials");
      setTrials(data);
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    }
  }

  useEffect(() => {
    loadTrials();
  }, []);

  return (
    <main>
      <h1>Clinical Trials</h1>

      {message && <p>Login required: {message}</p>}

      <button onClick={loadTrials}>Refresh</button>

      <ul>
        {trials.map((trial) => (
          <li key={trial.id}>
            {trial.id}: {trial.brief_title} — {trial.sponsor}
          </li>
        ))}
      </ul>
    </main>
  );
}

function CreateRecord() {
  const navigate = useNavigate();
  const [briefTitle, setBriefTitle] = useState("");
  const [sponsor, setSponsor] = useState("");
  const [message, setMessage] = useState("");

  async function handleCreate(event) {
    event.preventDefault();

    try {
      await api("/api/trials", {
        method: "POST",
        body: JSON.stringify({
          brief_title: briefTitle,
          sponsor,
        }),
      });

      navigate("/");
    } catch (error) {
      setMessage(error.message);
    }
  }

  return (
    <main>
      <h1>Create Trial</h1>

      <form onSubmit={handleCreate}>
        <input
          value={briefTitle}
          onChange={(event) => setBriefTitle(event.target.value)}
          placeholder="Brief title"
        />

        <input
          value={sponsor}
          onChange={(event) => setSponsor(event.target.value)}
          placeholder="Sponsor"
        />

        <button type="submit">Create Trial</button>
      </form>

      {message && <p>{message}</p>}
    </main>
  );
}

function UpdateRecord() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [briefTitle, setBriefTitle] = useState("");
  const [sponsor, setSponsor] = useState("");
  const [message, setMessage] = useState("");

  async function handleUpdate(event) {
    event.preventDefault();

    try {
      await api(`/api/trials/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          brief_title: briefTitle,
          sponsor,
        }),
      });

      navigate("/");
    } catch (error) {
      setMessage(error.message);
    }
  }

  return (
    <main>
      <h1>Update Trial {id}</h1>

      <form onSubmit={handleUpdate}>
        <input
          value={briefTitle}
          onChange={(event) => setBriefTitle(event.target.value)}
          placeholder="New brief title"
        />

        <input
          value={sponsor}
          onChange={(event) => setSponsor(event.target.value)}
          placeholder="New sponsor"
        />

        <button type="submit">Update Trial</button>
      </form>

      {message && <p>{message}</p>}
    </main>
  );
}

function DeleteRecord() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [message, setMessage] = useState("");

  async function handleDelete() {
    try {
      await api(`/api/trials/${id}`, {
        method: "DELETE",
      });

      navigate("/");
    } catch (error) {
      setMessage(error.message);
    }
  }

  return (
    <main>
      <h1>Delete Trial {id}</h1>

      <button onClick={handleDelete}>Delete Trial</button>

      {message && <p>{message}</p>}
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
