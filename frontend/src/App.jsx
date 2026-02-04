import { useEffect, useMemo, useState } from "react";
import {
  authTelegram,
  completeTask,
  fetchMe,
  fetchReferrals,
  fetchTasks,
  fetchUsers,
  setBanUser,
} from "./api.js";

const tabs = ["dashboard", "tasks", "profile", "admin"];

const TabButton = ({ active, onClick, children }) => (
  <button
    className={`px-3 py-2 rounded-full text-sm transition ${
      active ? "bg-cyan-400 text-slate-900" : "text-slate-200"
    }`}
    onClick={onClick}
  >
    {children}
  </button>
);

const Card = ({ children }) => (
  <div className="rounded-2xl border border-white/10 bg-white/10 p-4 shadow-lg backdrop-blur">
    {children}
  </div>
);

const App = () => {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [me, setMe] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [referrals, setReferrals] = useState([]);
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");

  const initData = useMemo(() => window.Telegram?.WebApp?.initData || "", []);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        if (initData) {
          await authTelegram(initData);
        }
        const user = await fetchMe();
        setMe(user);
        const [taskList, referralList] = await Promise.all([
          fetchTasks(),
          fetchReferrals(),
        ]);
        setTasks(taskList);
        setReferrals(referralList);
      } catch (err) {
        setError(err.message);
      }
    };
    bootstrap();
  }, [initData]);

  useEffect(() => {
    if (!me || !initData) return;
    const ws = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/user/${
        me.id
      }?initData=${encodeURIComponent(initData)}`
    );
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setMe((prev) => (prev ? { ...prev, balance: payload.balance } : prev));
      } catch (err) {
        console.error(err);
      }
    };
    return () => ws.close();
  }, [me, initData]);

  useEffect(() => {
    if (activeTab === "admin" && me?.role === "admin") {
      fetchUsers().then(setUsers).catch((err) => setError(err.message));
    }
  }, [activeTab, me]);

  const handleCompleteTask = async (taskId) => {
    try {
      await completeTask(taskId);
      const updated = await fetchTasks();
      setTasks(updated);
      const user = await fetchMe();
      setMe(user);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggleBan = async (user) => {
    try {
      await setBanUser(user.id, !user.is_banned);
      const updated = await fetchUsers();
      setUsers(updated);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
      <div className="mx-auto max-w-md px-4 py-6">
        <h1 className="text-2xl font-semibold">Telegram Mini App</h1>
        <p className="text-sm text-slate-300">Secure account and task hub</p>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-100">
            {error}
          </div>
        )}

        <div className="mt-6 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <TabButton key={tab} active={activeTab === tab} onClick={() => setActiveTab(tab)}>
              {tab}
            </TabButton>
          ))}
        </div>

        {activeTab === "dashboard" && (
          <div className="mt-6 space-y-4">
            <Card>
              <p className="text-sm text-slate-300">Balance</p>
              <p className="text-3xl font-bold text-cyan-300">{me?.balance ?? "0.00"}</p>
            </Card>
            <Card>
              <p className="text-sm text-slate-300">Referrals</p>
              <p className="text-lg">{referrals.length}</p>
            </Card>
          </div>
        )}

        {activeTab === "tasks" && (
          <div className="mt-6 space-y-4">
            {tasks.map((task) => (
              <Card key={task.id}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{task.title}</p>
                    <p className="text-xs text-slate-300">Reward: {task.reward}</p>
                  </div>
                  <button
                    className={`rounded-full px-3 py-1 text-xs ${
                      task.completed
                        ? "bg-emerald-400/20 text-emerald-200"
                        : "bg-cyan-400 text-slate-900"
                    }`}
                    onClick={() => handleCompleteTask(task.id)}
                    disabled={task.completed}
                  >
                    {task.completed ? "Completed" : "Complete"}
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}

        {activeTab === "profile" && (
          <div className="mt-6 space-y-4">
            <Card>
              <p className="text-sm text-slate-300">Username</p>
              <p className="text-lg">@{me?.username || "anonymous"}</p>
            </Card>
            <Card>
              <p className="text-sm text-slate-300">User ID</p>
              <p className="text-lg">{me?.id}</p>
            </Card>
            <Card>
              <p className="text-sm text-slate-300">Role</p>
              <p className="text-lg capitalize">{me?.role}</p>
            </Card>
          </div>
        )}

        {activeTab === "admin" && (
          <div className="mt-6 space-y-4">
            {me?.role !== "admin" ? (
              <Card>
                <p className="text-sm">Admin access required.</p>
              </Card>
            ) : (
              users.map((user) => (
                <Card key={user.id}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">@{user.username || "anonymous"}</p>
                      <p className="text-xs text-slate-300">ID: {user.id}</p>
                      <p className="text-xs text-slate-300">Balance: {user.balance}</p>
                    </div>
                    <button
                      className={`rounded-full px-3 py-1 text-xs ${
                        user.is_banned
                          ? "bg-emerald-400/20 text-emerald-200"
                          : "bg-rose-500 text-white"
                      }`}
                      onClick={() => handleToggleBan(user)}
                    >
                      {user.is_banned ? "Unban" : "Ban"}
                    </button>
                  </div>
                </Card>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
