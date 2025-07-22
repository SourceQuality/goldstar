import { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [users, setUsers] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [recipient, setRecipient] = useState("");
  const [starCounts, setStarCounts] = useState({});

  useEffect(() => {
    axios.get("/api/auth/me", {
      headers: { "X-User-Email": "alice@example.com" }
    }).then((res) => setCurrentUser(res.data));
    axios.get("/api/users").then((res) => setUsers(res.data));
    axios.get("/api/user_stars").then((res) => setStarCounts(res.data));
    if (Notification.permission !== "granted") {
      Notification.requestPermission();
    }
  }, []);

  const handleSendStar = () => {
    if (!recipient) return;
    axios.post("/api/stars", { from_: currentUser.id, to: recipient }).then(() => {
      const toUser = users.find((u) => u.id === recipient);
      alert(`⭐ Star sent to ${toUser.name}`);
      new Notification(`⭐ ${currentUser.name} sent a gold star to ${toUser.name}`);
      setStarCounts((prev) => ({ ...prev, [recipient]: (prev[recipient] || 0) + 1 }));
    });
  };

  return (
    <div style={{ padding: 30, fontFamily: 'sans-serif', maxWidth: 600, margin: '0 auto' }}>
      <h1>⭐ Gold Star Exchange</h1>
      <p>Welcome, {currentUser?.name}</p>
      <input
        list="users"
        placeholder="Send a star to..."
        value={recipient}
        onChange={(e) => setRecipient(e.target.value)}
      />
      <datalist id="users">
        {users.filter((u) => u.id !== currentUser?.id).map((user) => (
          <option key={user.id} value={user.id}>{user.name}</option>
        ))}
      </datalist>
      <button onClick={handleSendStar}>Send Star</button>
      <h2 style={{ marginTop: 20 }}>Leaderboard</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>User</th>
            <th style={{ textAlign: 'right', borderBottom: '1px solid #ccc' }}>Stars</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>{user.name}</td>
              <td style={{ textAlign: 'right' }}>{starCounts[user.id] || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;
