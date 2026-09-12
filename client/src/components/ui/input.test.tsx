import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Input } from "./input";

describe("Input", () => {
  it("keeps the mobile touch target tall while preserving the desktop height contract", () => {
    render(<Input aria-label="Review ID" />);

    const input = screen.getByRole("textbox", { name: "Review ID" });
    const classes = input.className.split(/\s+/);

    expect(classes).toContain("h-11");
    expect(classes).toContain("md:h-[var(--bf-control-height)]");
    expect(classes).toContain("rounded-[var(--bf-radius-control)]");
    expect(classes).toContain("border-border/70");
    expect(classes).toContain("bg-background");
  });

  it("merges custom classes without dropping the base sizing contract", () => {
    render(<Input aria-label="Name" className="rounded-md" />);

    const input = screen.getByRole("textbox", { name: "Name" });
    const classes = input.className.split(/\s+/);

    expect(classes).toContain("h-11");
    expect(classes).toContain("md:h-[var(--bf-control-height)]");
    expect(classes).toContain("rounded-md");
  });
});
