import { createRoot } from "react-dom/client";
import App from "./App";
import "./tokens.css";
import "./style.css";
const rootElement = document.getElementById("root");
if (rootElement === null) {
  throw new Error("RoboArc root element is missing");
}

createRoot(rootElement).render(<App />);
