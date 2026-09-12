import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { GeneratedEndpointKeyDialog } from "./GeneratedEndpointKeyDialog";

it("reports copy success only after confirmation and supports retry", async () => {
	const user = userEvent.setup();
	let finishCopy!: () => void;
	const writeText = vi.spyOn(navigator.clipboard, "writeText")
		.mockRejectedValueOnce(new Error("Synthetic failure"))
		.mockImplementationOnce(() => new Promise<void>((resolve) => { finishCopy = resolve; }));
	const onClose = vi.fn();
	render(<GeneratedEndpointKeyDialog workflowName="Customer reconciliation" rawKey="synthetic-test-key" onClose={onClose} />);
	expect(screen.getByLabelText("Customer reconciliation")).toHaveValue("synthetic-test-key");
	await user.click(screen.getByRole("button", { name: "Copy" }));
	expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't copy the key");
	expect(screen.queryByRole("status")).not.toBeInTheDocument();
	await user.click(screen.getByRole("button", { name: "Retry copy" }));
	expect(screen.getByRole("button", { name: "Copying…" })).toBeDisabled();
	expect(screen.getByRole("status")).toHaveTextContent("Copying endpoint key");
	finishCopy();
	expect(await screen.findByText("Endpoint key copied.")).toBeInTheDocument();
	expect(writeText).toHaveBeenCalledTimes(2);
	await user.click(screen.getByRole("button", { name: "Done" }));
	expect(onClose).toHaveBeenCalledOnce();
});
