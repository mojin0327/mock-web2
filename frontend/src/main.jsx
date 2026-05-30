import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL =
  import.meta.env.VITE_API_URL ||
  (window.location.hostname === "localhost" ? "http://localhost:8000" : "/backend");

function App() {
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function request(path, options) {
    const response = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json();
  }

  async function loadTasks() {
    try {
      setError("");
      setTasks(await request("/tasks"));
    } catch (err) {
      setError("バックエンドに接続できません。FastAPIが動いているか、VITE_API_URLが正しいか確認してください。");
    }
  }

  useEffect(() => {
    loadTasks();
  }, []);

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
        <p className="eyebrow">React + FastAPI + SQLite</p>
        <h1>画面からAPIとDBを操作するタスク管理</h1>
        <p className="lead">POSTで作成、GETで表示、PATCHで完了切り替え、DELETEで削除します。</p>
      </section>

      <section className="workspace">
        <form className="task-form" onSubmit={createTask}>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="タスク名" />
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="説明" />
          <button disabled={loading}>{loading ? "保存中" : "追加"}</button>
        </form>

        {error && <p className="error">{error}</p>}

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
          {tasks.length === 0 && !error && <p className="empty">まだタスクはありません。</p>}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
