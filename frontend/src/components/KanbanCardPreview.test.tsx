import { render, screen } from "@testing-library/react";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";

describe("KanbanCardPreview", () => {
  it("renders title and details", () => {
    render(
      <KanbanCardPreview
        card={{ id: "card-1", title: "Test title", details: "Test details" }}
      />
    );
    expect(screen.getByText("Test title")).toBeInTheDocument();
    expect(screen.getByText("Test details")).toBeInTheDocument();
  });
});
