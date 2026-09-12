import {
	FileSpreadsheet,
	FileText,
	Download,
	Image,
	Presentation,
	Video,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import {
	attachmentContentUrl,
	downloadChatAttachment,
	formatBytes,
	isImageAttachment,
	isVideoAttachment,
	type AttachmentPublic,
} from "@/services/chatAttachments";
import { FilePreviewSheet } from "./FilePreviewSheet";

function FileIcon({ attachment }: { attachment: AttachmentPublic }) {
	if (isImageAttachment(attachment.content_type)) {
		return <Image className="h-5 w-5" />;
	}
	if (isVideoAttachment(attachment.content_type)) {
		return <Video className="h-5 w-5" />;
	}
	if (attachment.content_type.includes("spreadsheet")) {
		return <FileSpreadsheet className="h-5 w-5" />;
	}
	if (attachment.content_type.includes("presentation")) {
		return <Presentation className="h-5 w-5" />;
	}
	return <FileText className="h-5 w-5" />;
}

export function ChatAttachmentList({
	conversationId,
	attachments,
	variant = "attachment",
}: {
	conversationId: string;
	attachments: AttachmentPublic[];
	variant?: "attachment" | "artifact";
}) {
	const [preview, setPreview] = useState<AttachmentPublic | null>(null);
	if (attachments.length === 0) return null;

	return (
		<>
			<div
				className={cn(
					"mb-2 flex gap-2",
					variant === "attachment"
						? "flex-wrap justify-end"
						: "w-full flex-col items-stretch px-3 sm:px-4",
				)}
			>
				{attachments.map((attachment) => {
					const previewUrl = attachmentContentUrl(
						conversationId,
						attachment.id,
					);
					return (
						<div
							key={attachment.id}
							className={cn(
								"group/file flex min-w-0 items-stretch rounded-[var(--bf-radius-surface)] border p-1.5 text-left transition-colors duration-[var(--bf-motion-feedback)] motion-reduce:transition-none",
								variant === "attachment"
									? "max-w-[min(100%,18rem)] border-border/70 bg-muted/30 hover:bg-muted/50"
									: "w-full max-w-none animate-in fade-in-0 slide-in-from-bottom-1 border-border/70 bg-card text-card-foreground shadow-sm hover:bg-accent/40 motion-reduce:animate-none",
							)}
						>
							<button
								type="button"
								onClick={() => setPreview(attachment)}
								aria-label={`Preview ${attachment.filename}`}
								className={cn(
									"flex min-h-11 min-w-0 flex-1 items-center gap-2.5 rounded-[var(--bf-radius-control)] p-1.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring",
									variant === "artifact" && "w-full max-w-none",
								)}
							>
							{isImageAttachment(attachment.content_type) ? (
								<img
									src={previewUrl}
									alt=""
									className="h-11 w-11 rounded-[var(--bf-radius-control)] object-cover"
								/>
							) : (
								<span
									className={cn(
										"flex h-11 w-11 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)]",
										variant === "attachment"
											? "bg-background/70 text-foreground"
											: "bg-primary/10 text-primary",
									)}
								>
									<FileIcon attachment={attachment} />
								</span>
							)}
							<span className="min-w-0 flex-1">
								<span className="block text-xs font-medium leading-5 [overflow-wrap:anywhere]">
									{attachment.filename}
								</span>
								<span className="block text-[11px] leading-4 text-muted-foreground [overflow-wrap:anywhere]">
									{variant === "artifact"
										? "Generated file · "
										: ""}
									{formatBytes(attachment.size_bytes)}
								</span>
							</span>
							</button>
							<button
								type="button"
								className="flex size-11 shrink-0 items-center justify-center rounded-[var(--bf-radius-control)] border border-border/70 bg-background/80 text-muted-foreground opacity-80 hover:bg-muted/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
								onClick={() => {
									void downloadChatAttachment(conversationId, attachment).catch(() =>
										toast.error("Download failed"),
									);
								}}
								aria-label={`Download ${attachment.filename}`}
							>
								<Download className="h-4 w-4" />
							</button>
						</div>
					);
				})}
			</div>

			<FilePreviewSheet
				conversationId={conversationId}
				attachment={preview}
				attachments={attachments}
				onAttachmentChange={setPreview}
				onOpenChange={(open) => !open && setPreview(null)}
			/>
		</>
	);
}
