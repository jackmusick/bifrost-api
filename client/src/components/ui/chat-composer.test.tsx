import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ChatComposer } from "./chat-composer";

describe("ChatComposer", () => {
	it("calls onSend on Enter (no shift)", async () => {
		const user = userEvent.setup();
		const onSend = vi.fn();
		render(<ChatComposer placeholder="say something" onSend={onSend} />);
		const ta = screen.getByPlaceholderText("say something");
		await user.click(ta);
		await user.keyboard("hi{Enter}");
		expect(onSend).toHaveBeenCalledWith("hi");
	});

	it("does NOT call onSend on Shift+Enter", async () => {
		const user = userEvent.setup();
		const onSend = vi.fn();
		render(<ChatComposer placeholder="say something" onSend={onSend} />);
		const ta = screen.getByPlaceholderText("say something");
		await user.click(ta);
		await user.keyboard("hi{Shift>}{Enter}{/Shift}");
		expect(onSend).not.toHaveBeenCalled();
	});

	it("clears the textarea after sending", async () => {
		const user = userEvent.setup();
		render(<ChatComposer onSend={() => {}} />);
		const ta = screen.getByRole("textbox");
		await user.type(ta, "hello{Enter}");
		expect(ta).toHaveValue("");
	});

	it("disables send when value is empty", () => {
		render(<ChatComposer onSend={() => {}} />);
		expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
	});

	it("disables send while pending", () => {
		render(<ChatComposer onSend={() => {}} pending />);
		expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
	});

	it("clicking send button submits the value", async () => {
		const user = userEvent.setup();
		const onSend = vi.fn();
		render(<ChatComposer onSend={onSend} />);
		await user.type(screen.getByRole("textbox"), "click test");
		await user.click(screen.getByRole("button", { name: /send/i }));
		expect(onSend).toHaveBeenCalledWith("click test");
	});
	it("does not send an Enter used to confirm composed text", () => {
		const onSend = vi.fn();
		render(<ChatComposer onSend={onSend} />);
		const input = screen.getByRole("textbox");
		fireEvent.change(input, { target: { value: "日本語" } });
		fireEvent.keyDown(input, { key: "Enter", isComposing: true });
		expect(onSend).not.toHaveBeenCalled();
		expect(input).toHaveValue("日本語");
		fireEvent.keyDown(input, { key: "Enter", keyCode: 229 });
		expect(onSend).not.toHaveBeenCalled();
		fireEvent.keyDown(input, { key: "Enter" });
		expect(onSend).toHaveBeenCalledWith("日本語");
	});
});


it("retains failed async messages and clears them only after retry succeeds",async()=>{
 const user=userEvent.setup();const onSend=vi.fn().mockRejectedValueOnce(new Error("Synthetic failure")).mockResolvedValueOnce(undefined);
 render(<ChatComposer onSend={onSend}/>);const input=screen.getByRole("textbox");await user.type(input,"Keep my message");await user.click(screen.getByRole("button",{name:"Send"}));expect(input).toHaveValue("Keep my message");expect(screen.getByRole("alert")).toHaveTextContent("Message could not be sent");await user.click(screen.getByRole("button",{name:"Send"}));expect(input).toHaveValue("");expect(onSend).toHaveBeenNthCalledWith(2,"Keep my message");
});
