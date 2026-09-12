import { createElement, type ReactNode } from "react";
import { AppWindow, Bot, FileInput, Plug } from "lucide-react";

import { EntityLogo } from "@/components/EntityLogo";
import { getIcon } from "@/lib/icons";
import { cn } from "@/lib/utils";

type ResourceKind = "app" | "form" | "agent" | "integration";
type ResourceIconSize = "card" | "table" | "inline";

type EntityLogoKind = Extract<
	ResourceKind,
	"app" | "form" | "agent" | "integration"
>;

const KIND_FALLBACK = {
	app: AppWindow,
	form: FileInput,
	agent: Bot,
	integration: Plug,
};

const SIZE_STYLES: Record<
	ResourceIconSize,
	{
		box: string;
		glyph: string;
		pixels: number;
	}
> = {
	card: {
		box: "size-12 rounded-[var(--bf-radius-control)]",
		glyph: "size-6",
		pixels: 48,
	},
	table: {
		box: "size-8 rounded-[var(--bf-radius-control)]",
		glyph: "size-4",
		pixels: 32,
	},
	inline: {
		box: "size-6 rounded-[var(--bf-radius-control)]",
		glyph: "size-3.5",
		pixels: 24,
	},
};

export type ResourceIconProps = {
	kind: ResourceKind;
	id?: string;
	icon?: string | null;
	logo?: string | null;
	cacheKey?: string;
	size?: ResourceIconSize;
	"aria-label"?: string;
	className?: string;
	fallback?: ReactNode;
};

export function ResourceIcon({
	kind,
	id,
	icon,
	logo,
	cacheKey,
	size = "card",
	"aria-label": ariaLabel,
	className,
	fallback,
}: ResourceIconProps) {
	const styles = SIZE_STYLES[size];
	const hidden = ariaLabel ? undefined : true;
	const fallbackIcon =
		fallback ??
		createElement(getIcon(icon, KIND_FALLBACK[kind]), {
			className: cn(styles.glyph, "text-primary"),
			"aria-hidden": true,
		});
	const boxClassName = cn(
		"inline-grid shrink-0 place-items-center overflow-hidden border border-primary/15 bg-primary/10 text-primary",
		styles.box,
		className,
	);

	if (id) {
		return (
			<EntityLogo
				entityType={kind as EntityLogoKind}
				entityId={id}
				logo={logo}
				cacheKey={cacheKey}
				size={styles.pixels}
				fallback={fallbackIcon}
				className={boxClassName}
				imageClassName="object-contain"
				aria-label={ariaLabel}
				aria-hidden={hidden}
			/>
		);
	}

	return (
		<span
			className={boxClassName}
			aria-label={ariaLabel}
			aria-hidden={hidden}
		>
			{fallbackIcon}
		</span>
	);
}
