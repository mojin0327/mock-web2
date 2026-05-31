import React, { useEffect, useMemo, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL =
  import.meta.env.VITE_API_URL ||
  (window.location.hostname === "localhost" ? "http://localhost:8000" : "/backend");
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

const supabase =
  SUPABASE_URL && SUPABASE_ANON_KEY ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY) : null;

function App() {
  const [session, setSession] = useState(null);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const token = session?.access_token;
  const isAuthConfigured = Boolean(supabase);

  const userLabel = useMemo(() => session?.user?.email ?? "", [session]);

  useEffect(() => {
    if (!supabase) return;

    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session ?? null);
    });

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession ?? null);
    });

    return () => data.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (token) {
      loadTasks();
    } else {
      setTasks([]);
    }
  }, [token]);

  async function request(path, options = {}) {
    if (!token) {
      throw new Error("ログインが必要です。");
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers ?? {}),
      },
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `API error: ${response.status}`);
    }
    return response.json();
  }

  async function loadTasks() {
    try {
      setError("");
      setTasks(await request("/tasks"));
    } catch (err) {
      setError("タスクを読み込めません。ログイン状態かAPI設定を確認してください。");
    }
  }

  async function signUp(event) {
    event.preventDefault();
    if (!supabase) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const { error: authError } = await supabase.auth.signUp({
        email: authEmail,
        password: authPassword,
      });
      if (authError) throw authError;
      setMessage("登録しました。確認メールが届いた場合はメール内のリンクを開いてください。");
    } catch (err) {
      setError(err.message || "登録に失敗しました。");
    } finally {
      setLoading(false);
    }
  }

  async function signIn(event) {
    event.preventDefault();
    if (!supabase) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const { error: authError } = await supabase.auth.signInWithPassword({
        email: authEmail,
        password: authPassword,
      });
      if (authError) throw authError;
      setAuthPassword("");
    } catch (err) {
      setError(err.message || "ログインに失敗しました。");
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    if (!supabase) return;
    await supabase.auth.signOut();
    setSession(null);
    setTasks([]);
  }

  async function createTask(event) {
    event.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    try {
      await request("/tasks", {
        method: "POST",
        body: JSON.stringify({ title, description }),
      });
      setTitle("");
      setDescription("");
      await loadTasks();
    } finally {
      setLoading(false);
    }
  }

  async function toggleTask(task) {
    await request(`/tasks/${task.id}`, {
      method: "PATCH",
      body: JSON.stringify({ done: !task.done }),
    });
    await loadTasks();
  }

  async function deleteTask(taskId) {
    await request(`/tasks/${taskId}`, { method: "DELETE" });
    await loadTasks();
  }

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">React + FastAPI + Supabase Auth + PostgreSQL</p>
        <h1>ログインユーザーごとに分かれるタスク管理</h1>
        <p className="lead">
          Supabase Authでログインし、FastAPIがトークンを検証して、自分のタスクだけをPostgreSQLから取得します。
        </p>
      </section>

      <section className="workspace">
        {!isAuthConfigured && (
          <p className="error">Supabaseの環境変数が未設定です。VITE_SUPABASE_URL と VITE_SUPABASE_ANON_KEY を設定してください。</p>
        )}

        {isAuthConfigured && !session && (
          <form className="auth-form" onSubmit={signIn}>
            <input value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} placeholder="メールアドレス" type="email" />
            <input value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} placeholder="パスワード" type="password" />
            <div className="auth-actions">
              <button type="submit" disabled={loading}>ログイン</button>
              <button type="button" className="secondary" disabled={loading} onClick={signUp}>新規登録</button>
            </div>
          </form>
        )}

        {message && <p className="empty">{message}</p>}
        {error && <p className="error">{error}</p>}

        {session && (
          <>
            <div className="session-bar">
              <span>{userLabel}</span>
              <button className="secondary" onClick={signOut}>ログアウト</button>
            </div>

            <form className="task-form" onSubmit={createTask}>
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="タスク名" />
              <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="説明" />
              <button disabled={loading}>{loading ? "保存中" : "追加"}</button>
            </form>

            <div className="task-list">
              {tasks.map((task) => (
                <article className={task.done ? "task done" : "task"} key={task.id}>
                  <label>
                    <input type="checkbox" checked={task.done} onChange={() => toggleTask(task)} />
                    <span>{task.title}</span>
                  </label>
                  <p>{task.description || "説明なし"}</p>
                  <div className="meta">
                    <span>ID: {task.id}</span>
                    <span>{task.updated_at}</span>
                  </div>
                  <button className="delete" onClick={() => deleteTask(task.id)}>削除</button>
                </article>
              ))}
              {tasks.length === 0 && <p className="empty">まだタスクはありません。</p>}
            </div>
          </>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
