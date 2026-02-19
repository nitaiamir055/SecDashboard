import { useWebSocket } from "./hooks/useWebSocket";
import { useNotifications } from "./hooks/useNotifications";
import Dashboard from "./components/Dashboard";

const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/filings`;

export default function App() {
  const { filings, connected } = useWebSocket(WS_URL);
  useNotifications(filings);

  return <Dashboard filings={filings} connected={connected} />;
}
