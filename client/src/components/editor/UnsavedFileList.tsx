export function UnsavedFileList({ paths }: { paths: string[] }) {
	return (
		<ul
			aria-label="Files with unsaved changes"
			tabIndex={0}
			className="max-h-48 space-y-2 overflow-y-auto rounded-[var(--bf-radius-surface)] border border-border bg-muted p-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
		>
			{paths.map((path) => (
				<li
					key={path}
					className="font-mono text-sm leading-5 [overflow-wrap:anywhere]"
				>
					{path}
				</li>
			))}
		</ul>
	);
}
