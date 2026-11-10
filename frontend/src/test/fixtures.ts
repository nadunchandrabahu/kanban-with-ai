import type { BoardData } from "@/lib/kanban";

export const sampleBoard: BoardData = {
  columns: [
    { id: "col-backlog", title: "Backlog", cardIds: ["card-1", "card-2"] },
    { id: "col-progress", title: "In Progress", cardIds: ["card-3"] },
    { id: "col-review", title: "Review", cardIds: ["card-4"] },
    { id: "col-done", title: "Done", cardIds: ["card-5"] },
  ],
  cards: {
    "card-1": {
      id: "card-1",
      title: "Align roadmap themes",
      details: "Draft quarterly themes with impact statements and metrics.",
    },
    "card-2": {
      id: "card-2",
      title: "Gather customer signals",
      details: "Review support tags, sales notes, and churn feedback.",
    },
    "card-3": {
      id: "card-3",
      title: "Prototype analytics view",
      details: "Sketch initial dashboard layout and key drill-downs.",
    },
    "card-4": {
      id: "card-4",
      title: "QA micro-interactions",
      details: "Verify hover, focus, and loading states.",
    },
    "card-5": {
      id: "card-5",
      title: "Close onboarding sprint",
      details: "Document release notes and share internally.",
    },
  },
};
