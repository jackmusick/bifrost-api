import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { JsxTemplateRenderer } from "./jsx-template-renderer";

const context = {
	workflow: { count: 0, enabled: false },
	query: { search: "query" },
	field: { name: "field" },
};

describe("JsxTemplateRenderer", () => {
	it("renders real compiled JSX with each context namespace and falsy values", () => {
		render(
			<JsxTemplateRenderer
				context={context}
				template={
					"<p>{context.workflow.count} / {String(context.workflow.enabled)} / {context.query.search} / {context.field.name}</p>"
				}
			/>,
		);
		expect(
			screen.getByText("0 / false / query / field"),
		).toBeInTheDocument();
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
	});
	it("recovers from a compilation error after the template is corrected", () => {
		const { rerender } = render(
			<JsxTemplateRenderer context={context} template="<div>{</div>" />,
		);
		expect(screen.getByRole("alert")).toHaveTextContent("Template error");
		rerender(
			<JsxTemplateRenderer
				context={context}
				template="<p>Corrected template</p>"
			/>,
		);
		expect(screen.queryByRole("alert")).not.toBeInTheDocument();
		expect(screen.getByText("Corrected template")).toBeInTheDocument();
	});
});
