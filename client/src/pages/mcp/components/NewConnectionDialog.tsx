import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { $api } from "@/lib/api-client";
import { useOrganizations } from "@/hooks/useOrganizations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

/**
 * Lightweight new-connection dialog: pick org + initial credentials.
 * The full edit page (with availability flags + tool catalog) opens
 * automatically after create.
 */
export function NewConnectionDialog({
	open,
	onOpenChange,
	serverId,
}: {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	serverId: string;
}) {
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const {
		data: organizations = [],
		isError: orgError,
		isLoading: orgLoading,
		isFetching: orgFetching,
		refetch: reloadOrganizations,
	} = useOrganizations({ enabled: open });

	const [createError, setCreateError] = useState<string | null>(null);
	const errorRef = useRef<HTMLParagraphElement>(null);
	const busy = useRef(false);
	useEffect(() => {
		if (createError) errorRef.current?.focus();
	}, [createError]);
	const [orgId, setOrgId] = useState<string>("");
	const [clientId, setClientId] = useState("");
	const [clientSecret, setClientSecret] = useState("");

	const create = $api.useMutation("post", "/api/mcp-connections");

	const handleCreate = async () => {
		if (busy.current || orgLoading || orgError) return;
		setCreateError(null);
		if (!orgId || !clientId || !clientSecret) {
			setCreateError(
				"Organization, client ID, and client secret are required",
			);
			return;
		}
		busy.current = true;
		try {
			const result = await create.mutateAsync({
				body: {
					server_id: serverId,
					organization_id: orgId,
					client_id: clientId,
					client_secret: clientSecret,
					available_in_chat: false,
					available_to_autonomous: false,
				},
			});
			toast.success("Connection created");
			queryClient.invalidateQueries({
				queryKey: ["get", "/api/mcp-servers/{server_id}"],
			});
			onOpenChange(false);
			navigate(`/mcp-servers/${serverId}/connections/${result.id}/edit`);
		} catch (err) {
			setCreateError(
				err instanceof Error
					? err.message
					: "Failed to create connection",
			);
		} finally {
			busy.current = false;
		}
	};

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!busy.current) onOpenChange(next);
			}}
		>
			<DialogContent
				className="flex max-h-[90dvh] flex-col overflow-hidden"
				onEscapeKeyDown={(event) => {
					if (busy.current) event.preventDefault();
				}}
				onPointerDownOutside={(event) => {
					if (busy.current) event.preventDefault();
				}}
			>
				<DialogHeader className="shrink-0">
					<DialogTitle>New MCP Connection</DialogTitle>
					<DialogDescription>
						Link this server template to an organization. You'll
						configure availability and OAuth on the next page.
					</DialogDescription>
				</DialogHeader>

				<div className="min-h-0 overflow-y-auto">
					<fieldset
						disabled={create.isPending}
						className="min-w-0 space-y-4"
					>
						<div className="space-y-2">
							<Label htmlFor="connection-org">Organization</Label>
							{orgError && (
								<div
									role="alert"
									className="space-y-2 text-sm text-destructive"
								>
									<p>Could not load organizations.</p>
									<Button
										type="button"
										variant="outline"
										className="min-h-11"
										disabled={orgFetching}
										onClick={() =>
											void reloadOrganizations()
										}
									>
										{orgFetching
											? "Retrying…"
											: "Retry organizations"}
									</Button>
								</div>
							)}
							{orgLoading && (
								<p
									role="status"
									className="text-sm text-muted-foreground"
								>
									Loading organizations…
								</p>
							)}
							{!orgLoading &&
								!orgError &&
								organizations.length === 0 && (
									<p className="text-sm text-muted-foreground">
										No organizations are available for this
										connection.
									</p>
								)}
							<Select
								value={orgId}
								onValueChange={setOrgId}
								disabled={orgLoading || orgError}
							>
								<SelectTrigger
									id="connection-org"
									className="min-h-11 w-full"
								>
									<SelectValue placeholder="Select organization..." />
								</SelectTrigger>
								<SelectContent>
									{organizations.map((o) => (
										<SelectItem
											key={o.id}
											value={o.id}
											className="min-h-11 [overflow-wrap:anywhere]"
										>
											{o.name}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>

						<div className="space-y-2">
							<Label htmlFor="client_id">Client ID</Label>
							<Input
								id="client_id"
								value={clientId}
								onChange={(e) => setClientId(e.target.value)}
								placeholder="abc123..."
								className="min-h-11 font-mono"
							/>
						</div>

						<div className="space-y-2">
							<Label htmlFor="client_secret">Client Secret</Label>
							<Input
								id="client_secret"
								className="min-h-11"
								autoComplete="new-password"
								type="password"
								value={clientSecret}
								onChange={(e) =>
									setClientSecret(e.target.value)
								}
								placeholder="••••••••••••••••"
							/>
						</div>
					</fieldset>
				</div>
				{createError && (
					<p
						ref={errorRef}
						tabIndex={-1}
						role="alert"
						className="shrink-0 outline-none text-sm text-destructive [overflow-wrap:anywhere]"
					>
						{createError}
					</p>
				)}
				<DialogFooter className="shrink-0">
					<Button
						type="button"
						className="min-h-11"
						variant="outline"
						onClick={() => {
							if (!busy.current) onOpenChange(false);
						}}
						disabled={create.isPending}
					>
						Cancel
					</Button>
					<Button
						type="button"
						className="min-h-11"
						onClick={handleCreate}
						disabled={
							create.isPending ||
							orgLoading ||
							orgError ||
							organizations.length === 0
						}
					>
						{create.isPending
							? "Creating..."
							: createError
								? "Retry create"
								: "Create"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
