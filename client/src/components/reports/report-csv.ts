/** Preserve labels containing CSV delimiters, quotes, or line breaks. */
export function serializeReportCSV(rows: (string | number)[][]): string {
	return rows
		.map((row) =>
			row
				.map((value) => {
					const cell = String(value);
					return /[",\r\n]/.test(cell)
						? `"${cell.replaceAll('"', '""')}"`
						: cell;
				})
				.join(","),
		)
		.join("\n");
}

export function downloadReportCSV(
	filename: string,
	headers: string[],
	rows: (string | number)[][],
) {
	const blob = new Blob([serializeReportCSV([headers, ...rows])], {
		type: "text/csv",
	});
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = filename;
	a.click();
	URL.revokeObjectURL(url);
}
