import { createRoot } from "react-dom/client";
import App from "./App";
import ReviewApp from "./ReviewApp";
import ReviewCatalog from "./ReviewCatalog";
import "./tokens.css";
import "./style.css";
const rootElement = document.getElementById("root");
if (rootElement === null) {
  throw new Error("RoboArc root element is missing");
}

const params = new URLSearchParams(window.location.search);
const reviewId = params.get("review");
const defaultToReview =
  document
    .querySelector('meta[name="roboarc-default-view"]')
    ?.getAttribute("content") === "review";
createRoot(rootElement).render(
  reviewId ? (
    <ReviewApp demoId={reviewId} />
  ) : params.has("review") || defaultToReview ? (
    <ReviewCatalog />
  ) : (
    <App />
  ),
);
