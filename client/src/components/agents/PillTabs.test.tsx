import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { PillTabs } from "./PillTabs";

it("moves focus and selection with arrows, skips disabled tabs, and supports Home and End", async () => {
 function Fixture() {
  const [value, setValue] = useState("overview");
  return <PillTabs items={[{value:"overview",label:"Overview"},{value:"disabled",label:"Unavailable",disabled:true},{value:"runs",label:"Runs"},{value:"settings",label:"Settings"}]} value={value} onValueChange={setValue} />;
 }
 const user = userEvent.setup();
 render(<Fixture />);
 await user.tab();
 expect(screen.getByRole("tab", {name:"Overview"})).toHaveFocus();
 await user.keyboard("{ArrowRight}");
 expect(screen.getByRole("tab", {name:"Runs"})).toHaveFocus();
 expect(screen.getByRole("tab", {name:"Runs"})).toHaveAttribute("aria-selected", "true");
 await user.keyboard("{End}");
 expect(screen.getByRole("tab", {name:"Settings"})).toHaveFocus();
 await user.keyboard("{ArrowRight}");
 expect(screen.getByRole("tab", {name:"Overview"})).toHaveFocus();
 await user.keyboard("{ArrowLeft}{Home}");
 expect(screen.getByRole("tab", {name:"Overview"})).toHaveFocus();
});
