import { createRoot } from "react-dom/client";
import App from "./App";
import ReviewApp from "./ReviewApp";
import "./tokens.css";
import "./style.css";
const rootElement = document.getElementById("root");
if (rootElement === null) {
  throw new Error("RoboArc root element is missing");
}

const review = new URLSearchParams(window.location.search).has("review");
createRoot(rootElement).render(review ? <ReviewApp /> : <App />);
