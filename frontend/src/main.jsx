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
  const [activeView, setActiveView] = useState("tasks");
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [workspaceItems, setWorkspaceItems] = useState([]);
  const [workspaceType, setWorkspaceType] = useState("project");
  const [workspaceTitle, setWorkspaceTitle] = useState("");
  const [workspaceContent, setWorkspaceContent] = useState("");
  const [workspaceStatus, setWorkspaceStatus] = useState("todo");
  const [workspaceDueDate, setWorkspaceDueDate] = useState("");
  const [workspaceGoal, setWorkspaceGoal] = useState("");
  const [workspaceBudget, setWorkspaceBudget] = useState("");
  const [workspaceSource, setWorkspaceSource] = useState("");
  const [workspaceScore, setWorkspaceScore] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const token = session?.access_token;
  const isAuthConfigured = Boolean(supabase);

  const userLabel = useMemo(() => session?.user?.email ?? "", [session]);
  const profile = useMemo(() => {
    const metadata = session?.user?.user_metadata ?? {};
    const email = session?.user?.email ?? "";
    const name = metadata.full_name || metadata.name || email || "ログイン中";
    const avatarUrl = metadata.avatar_url || metadata.picture || "";
    const initial = name.trim().charAt(0).toUpperCase() || "?";
    return { avatarUrl, email, initial, name };
  }, [session]);

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
      setWorkspaceItems([]);
    }
  }, [token]);

  useEffect(() => {
    if (token && activeView === "workspace") {
      loadWorkspaceItems();
    }
  }, [token, activeView]);

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

  async function loadWorkspaceItems() {
    try {
      setError("");
      setWorkspaceItems(await request("/workspace/items"));
    } catch (err) {
      setError("Workspace実験データを読み込めません。migrationが未実行の可能性があります。");
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

  async function signInWithProvider(provider) {
    if (!supabase) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const { error: authError } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: window.location.origin,
        },
      });
      if (authError) throw authError;
    } catch (err) {
      setError(err.message || `${provider}ログインに失敗しました。`);
      setLoading(false);
    }
  }

  async function signOut() {
    if (!supabase) return;
    await supabase.auth.signOut();
    setSession(null);
    setTasks([]);
    setWorkspaceItems([]);
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

  async function createWorkspaceItem(event) {
    event.preventDefault();
    if (!workspaceTitle.trim()) return;
    setLoading(true);
    setError("");
    try {
      const payload = {
        type: workspaceType,
        title: workspaceTitle,
        content: workspaceContent,
      };

      if (workspaceType === "project") {
        payload.goal = workspaceGoal;
        payload.budget = workspaceBudget ? Number(workspaceBudget) : null;
      }
      if (workspaceType === "task") {
        payload.status = workspaceStatus;
        payload.due_date = workspaceDueDate || null;
      }
      if (workspaceType === "idea") {
        payload.source = workspaceSource;
        payload.score = workspaceScore ? Number(workspaceScore) : null;
      }

      await request("/workspace/items", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setWorkspaceTitle("");
      setWorkspaceContent("");
      setWorkspaceGoal("");
      setWorkspaceBudget("");
      setWorkspaceDueDate("");
      setWorkspaceSource("");
      setWorkspaceScore("");
      await loadWorkspaceItems();
    } finally {
      setLoading(false);
    }
  }

  async function deleteWorkspaceItem(itemId) {
    await request(`/workspace/items/${itemId}`, { method: "DELETE" });
    await loadWorkspaceItems();
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
            <div className="oauth-actions">
              <button
                type="button"
                className="oauth-button google"
                disabled={loading}
                onClick={() => signInWithProvider("google")}
              >
                Googleでログイン
              </button>
            </div>
          </form>
        )}

        {message && <p className="empty">{message}</p>}
        {error && <p className="error">{error}</p>}

        {session && (
          <>
            <div className="session-bar">
              <div className="profile">
                {profile.avatarUrl ? (
                  <img src={profile.avatarUrl} alt="" className="profile-avatar" />
                ) : (
                  <span className="profile-avatar fallback">{profile.initial}</span>
                )}
                <div>
                  <strong>{profile.name}</strong>
                  <span>{userLabel}</span>
                </div>
              </div>
              <button className="secondary" onClick={signOut}>ログアウト</button>
            </div>

            <div className="view-tabs">
              <button className={activeView === "tasks" ? "active" : ""} onClick={() => setActiveView("tasks")}>タスク</button>
              <button className={activeView === "workspace" ? "active" : ""} onClick={() => setActiveView("workspace")}>Workspace実験</button>
            </div>

            {activeView === "tasks" && (
              <>
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

            {activeView === "workspace" && (
              <>
                <form className="workspace-form" onSubmit={createWorkspaceItem}>
                  <select value={workspaceType} onChange={(e) => setWorkspaceType(e.target.value)}>
                    <option value="project">project</option>
                    <option value="task">task</option>
                    <option value="idea">idea</option>
                    <option value="log">log</option>
                  </select>
                  <input value={workspaceTitle} onChange={(e) => setWorkspaceTitle(e.target.value)} placeholder="タイトル" />
                  <input value={workspaceContent} onChange={(e) => setWorkspaceContent(e.target.value)} placeholder="内容" />

                  {workspaceType === "project" && (
                    <>
                      <input value={workspaceGoal} onChange={(e) => setWorkspaceGoal(e.target.value)} placeholder="ゴール" />
                      <input value={workspaceBudget} onChange={(e) => setWorkspaceBudget(e.target.value)} placeholder="予算" type="number" />
                    </>
                  )}

                  {workspaceType === "task" && (
                    <>
                      <select value={workspaceStatus} onChange={(e) => setWorkspaceStatus(e.target.value)}>
                        <option value="todo">todo</option>
                        <option value="doing">doing</option>
                        <option value="done">done</option>
                        <option value="archived">archived</option>
                      </select>
                      <input value={workspaceDueDate} onChange={(e) => setWorkspaceDueDate(e.target.value)} type="date" />
                    </>
                  )}

                  {workspaceType === "idea" && (
                    <>
                      <input value={workspaceSource} onChange={(e) => setWorkspaceSource(e.target.value)} placeholder="発想元" />
                      <input value={workspaceScore} onChange={(e) => setWorkspaceScore(e.target.value)} placeholder="面白さ 1-10" type="number" min="1" max="10" />
                    </>
                  )}

                  <button disabled={loading}>{loading ? "保存中" : "追加"}</button>
                </form>

                <div className="task-list">
                  {workspaceItems.map((item) => (
                    <article className="task workspace-item" key={item.id}>
                      <label>
                        <span className={`type-badge ${item.type}`}>{item.type}</span>
                        <span>{item.title}</span>
                      </label>
                      <p>{item.content || "内容なし"}</p>
                      <div className="meta">
                        <span>ID: {item.id}</span>
                        <span>parent: {item.parent_id || "なし"}</span>
                        {item.detail?.status && <span>status: {item.detail.status}</span>}
                        {item.detail?.budget !== null && item.detail?.budget !== undefined && <span>budget: {item.detail.budget}</span>}
                        {item.detail?.score && <span>score: {item.detail.score}</span>}
                      </div>
                      <button className="delete" onClick={() => deleteWorkspaceItem(item.id)}>削除</button>
                    </article>
                  ))}
                  {workspaceItems.length === 0 && <p className="empty">Workspace実験データはまだありません。</p>}
                </div>
              </>
            )}
          </>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
