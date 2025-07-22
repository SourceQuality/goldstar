import { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [users, setUsers] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [recipient, setRecipient] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      window.location.href = "/api/auth/login";
      return;
    }
    axios
      .get("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => setCurrentUser(res.data));
    axios.get("/api/users").then((res) => setUsers(res.data));
    if (Notification.permission !== "granted") {
      Notification.requestPermission();
    }
  }, []);

  const handleSendStar = () => {
    if (!recipient) return;
    const token = localStorage.getItem("token");
    axios
      .post(
        "/api/stars",
        { from_: currentUser.id, to: recipient },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      .then(() => {
        const toUser = users.find((u) => u.id === recipient);
        alert(`⭐ Star sent to ${toUser.name}`);
        new Notification(`⭐ ${currentUser.name} sent a gold star to ${toUser.name}`);
      });
  };

  return (
    <div style={{ padding: 30, fontFamily: 'sans-serif' }}>
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
    </div>
  );
}

export default App;