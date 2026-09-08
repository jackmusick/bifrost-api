import type { ReactNode } from "react";

interface RunDetailHeadingProps {
	title: ReactNode;
	metadata: ReactNode;
	actions?: ReactNode;
	actionsLabel: string;
}

/** Keeps run actions aligned with the title, independent of metadata height. */
export function RunDetailHeading({ title, metadata, actions, actionsLabel }: RunDetailHeadingProps) {
	return (
		<div className="@container">
			<div className="grid min-w-0 grid-cols-1 gap-4 @2xl:grid-cols-[minmax(0,1fr)_auto] @2xl:items-center @2xl:gap-x-6 @2xl:gap-y-2">
				<div className="min-w-0 space-y-2 @2xl:contents @2xl:space-y-0">
					<h1 className="min-w-0 font-display text-2xl font-semibold leading-tight tracking-tight [overflow-wrap:anywhere] sm:text-[28px] @2xl:col-start-1 @2xl:row-start-1">{title}</h1>
					<div className="min-w-0 @2xl:col-start-1 @2xl:row-start-2">{metadata}</div>
				</div>
				{actions && <div role="group" aria-label={actionsLabel} className="grid auto-cols-fr grid-flow-col gap-2 @2xl:col-start-2 @2xl:row-start-1 @2xl:flex @2xl:justify-self-end">{actions}</div>}
			</div>
		</div>
	);
}
