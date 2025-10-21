import { useState, useMemo } from "react";
import {
    Key,
    Plus,
    Trash2,
    RefreshCw,
    Info,
    Loader2,
    Copy,
    Check,
    Globe,
    Workflow as WorkflowIcon,
    CalendarDays,
    Clock,
    AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
    useWorkflowKeys,
    useCreateWorkflowKey,
    useRevokeWorkflowKey,
} from "@/hooks/useWorkflowKeys";
import { useWorkflowsMetadata } from "@/hooks/useWorkflows";
import { toast } from "sonner";
import type { WorkflowKeyResponse } from "@/services/workflowKeys";

interface CreateFormData {
    workflowId: string;
    expiresInDays: string;
    description: string;
    isGlobal: boolean;
}

export function WorkflowKeys() {
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
    const [isRevokeDialogOpen, setIsRevokeDialogOpen] = useState(false);
    const [isKeyDisplayDialogOpen, setIsKeyDisplayDialogOpen] = useState(false);
    const [selectedKey, setSelectedKey] = useState<
        WorkflowKeyResponse | undefined
    >();
    const [createdKey, setCreatedKey] = useState<
        WorkflowKeyResponse | undefined
    >();
    const [copied, setCopied] = useState(false);
    const [formData, setFormData] = useState<CreateFormData>({
        workflowId: "",
        expiresInDays: "90",
        description: "",
        isGlobal: false,
    });

    const {
        data: keys,
        isFetching,
        refetch,
    } = useWorkflowKeys({ includeRevoked: false });
    const { data: workflowsData } = useWorkflowsMetadata();
    const createMutation = useCreateWorkflowKey();
    const revokeMutation = useRevokeWorkflowKey();

    // Get workflow names for dropdown - only show endpoint-enabled non-public workflows
    const workflows = useMemo(() => {
        if (!workflowsData?.workflows) return [];
        return workflowsData.workflows
            .filter((w) => w.endpointEnabled && !w.publicEndpoint) // Only endpoint-enabled non-public workflows
            .map((w) => w.name)
            .filter(Boolean)
            .sort();
    }, [workflowsData]);

    // Get workflows available for key creation (endpoint-enabled, non-public, and no existing key)
    const availableWorkflows = useMemo(() => {
        if (!workflowsData?.workflows || !keys) return [];

        // Get set of workflow IDs that already have keys
        const workflowsWithKeys = new Set(
            keys.filter((k) => k.workflowId).map((k) => k.workflowId)
        );

        return workflowsData.workflows
            .filter((w) => w.endpointEnabled && !w.publicEndpoint && !workflowsWithKeys.has(w.name ?? ''))
            .map((w) => w.name)
            .filter(Boolean)
            .sort();
    }, [workflowsData, keys]);

    // Sort and categorize keys
    const sortedKeys = useMemo(() => {
        if (!keys) return [];

        const workflowNames = new Set(workflows);

        return [...keys].sort((a, b) => {
            // Global keys first
            const aIsGlobal = !a.workflowId;
            const bIsGlobal = !b.workflowId;
            if (aIsGlobal && !bIsGlobal) return -1;
            if (!aIsGlobal && bIsGlobal) return 1;

            // Then check for orphaned keys (workflow-specific but workflow doesn't exist)
            const aIsOrphaned =
                a.workflowId && !workflowNames.has(a.workflowId);
            const bIsOrphaned =
                b.workflowId && !workflowNames.has(b.workflowId);
            if (!aIsOrphaned && bIsOrphaned) return -1;
            if (aIsOrphaned && !bIsOrphaned) return 1;

            // Otherwise sort by creation date (newest first)
            return (
                new Date(b.createdAt || 0).getTime() -
                new Date(a.createdAt || 0).getTime()
            );
        });
    }, [keys, workflows]);

    // Check if a key is orphaned
    const isOrphaned = (key: WorkflowKeyResponse) => {
        if (!key.workflowId) return false;
        return !workflows.includes(key.workflowId);
    };

    // Check if form is valid
    const isFormValid = useMemo(() => {
        if (!formData.description.trim()) return false;
        if (!formData.isGlobal && !formData.workflowId) return false;
        return true;
    }, [formData]);

    const handleCreate = () => {
        setFormData({
            workflowId: "",
            expiresInDays: "90",
            description: "",
            isGlobal: false,
        });
        setIsCreateDialogOpen(true);
    };

    const handleRevoke = (key: WorkflowKeyResponse) => {
        setSelectedKey(key);
        setIsRevokeDialogOpen(true);
    };

    const handleSubmitCreate = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!isFormValid) return;

        try {
            const result = await createMutation.mutateAsync({
                workflowId: formData.isGlobal ? undefined : formData.workflowId,
                expiresInDays: formData.expiresInDays
                    ? parseInt(formData.expiresInDays)
                    : undefined,
                description: formData.description,
            });

            setIsCreateDialogOpen(false);
            setCreatedKey(result);
            setIsKeyDisplayDialogOpen(true);
        } catch {
            // Error toast is handled by the hook
        }
    };

    const handleConfirmRevoke = async () => {
        if (!selectedKey?.id) return;

        await revokeMutation.mutateAsync(selectedKey.id);
        setIsRevokeDialogOpen(false);
        setSelectedKey(undefined);
    };

    const handleCopyKey = () => {
        if (!createdKey?.rawKey) return;

        navigator.clipboard.writeText(createdKey.rawKey);
        setCopied(true);
        toast.success("API key copied to clipboard");
        setTimeout(() => setCopied(false), 2000);
    };

    const formatDate = (dateString?: string | null) => {
        if (!dateString) return "-";
        const date = new Date(dateString);
        return date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    const isExpired = (expiresAt?: string | null) => {
        if (!expiresAt) return false;
        return new Date(expiresAt) < new Date();
    };

    return (
        <div className="flex flex-col h-full">
            <Card className="flex-1 flex flex-col overflow-hidden">
                <CardHeader className="flex-shrink-0">
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle>Workflow Keys</CardTitle>
                            <CardDescription>
                                Generate API keys for external systems to trigger workflows. Global keys work with all workflows, workflow-specific keys are scoped to individual workflows.
                            </CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="outline"
                                size="icon"
                                onClick={handleCreate}
                                title="Create API Key"
                            >
                                <Plus className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="outline"
                                size="icon"
                                onClick={() => refetch()}
                                disabled={isFetching}
                                title="Refresh"
                            >
                                <RefreshCw
                                    className={`h-4 w-4 ${
                                        isFetching ? "animate-spin" : ""
                                    }`}
                                />
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="flex-1 overflow-hidden flex flex-col">
                    {isFetching ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                        </div>
                    ) : sortedKeys && sortedKeys.length > 0 ? (
                        <div className="border rounded-lg overflow-hidden flex-1">
                            <div className="overflow-auto max-h-full">
                                <Table>
                                    <TableHeader className="sticky top-0 bg-background z-10">
                                        <TableRow>
                                            <TableHead>Scope</TableHead>
                                            <TableHead>Description</TableHead>
                                            <TableHead>Key</TableHead>
                                            <TableHead>Created</TableHead>
                                            <TableHead>Last Used</TableHead>
                                            <TableHead>Expires</TableHead>
                                            <TableHead className="text-right">
                                                Actions
                                            </TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {sortedKeys.map((key) => {
                                            const orphaned = isOrphaned(key);
                                            return (
                                                <TableRow
                                                    key={key.id}
                                                    className="hover:bg-muted/50"
                                                >
                                                    <TableCell>
                                                        {!key.workflowId ? (
                                                            <Badge
                                                                variant="default"
                                                                className="text-xs font-semibold"
                                                            >
                                                                <Globe className="mr-1 h-3 w-3" />
                                                                Global
                                                            </Badge>
                                                        ) : orphaned ? (
                                                            <Badge
                                                                variant="destructive"
                                                                className="font-mono text-xs"
                                                            >
                                                                <AlertTriangle className="mr-1 h-3 w-3" />
                                                                {key.workflowId}
                                                            </Badge>
                                                        ) : (
                                                            <Badge
                                                                variant="outline"
                                                                className="font-mono text-xs"
                                                            >
                                                                <WorkflowIcon className="mr-1 h-3 w-3" />
                                                                {key.workflowId}
                                                            </Badge>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="max-w-xs">
                                                        <div className="flex flex-col gap-1">
                                                            <span className="text-sm">
                                                                {key.description || (
                                                                    <span className="text-muted-foreground italic">
                                                                        No
                                                                        description
                                                                    </span>
                                                                )}
                                                            </span>
                                                            {orphaned && (
                                                                <span className="text-xs text-destructive">
                                                                    Warning:
                                                                    Workflow no
                                                                    longer
                                                                    exists
                                                                </span>
                                                            )}
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="font-mono text-sm">
                                                        {key.maskedKey}
                                                    </TableCell>
                                                    <TableCell className="text-sm text-muted-foreground">
                                                        {formatDate(
                                                            key.createdAt
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-sm text-muted-foreground">
                                                        {key.lastUsedAt ? (
                                                            <div className="flex items-center gap-1">
                                                                <Clock className="h-3 w-3" />
                                                                {formatDate(
                                                                    key.lastUsedAt
                                                                )}
                                                            </div>
                                                        ) : (
                                                            <span className="text-muted-foreground/50">
                                                                Never
                                                            </span>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-sm">
                                                        {key.expiresAt ? (
                                                            isExpired(
                                                                key.expiresAt
                                                            ) ? (
                                                                <Badge
                                                                    variant="destructive"
                                                                    className="text-xs"
                                                                >
                                                                    <AlertTriangle className="mr-1 h-3 w-3" />
                                                                    Expired
                                                                </Badge>
                                                            ) : (
                                                                <div className="flex items-center gap-1 text-muted-foreground">
                                                                    <CalendarDays className="h-3 w-3" />
                                                                    {formatDate(
                                                                        key.expiresAt
                                                                    )}
                                                                </div>
                                                            )
                                                        ) : (
                                                            <span className="text-muted-foreground/50">
                                                                Never
                                                            </span>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            onClick={() =>
                                                                handleRevoke(
                                                                    key
                                                                )
                                                            }
                                                            title="Revoke key"
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })}
                                    </TableBody>
                                </Table>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <Key className="h-12 w-12 text-muted-foreground" />
                            <h3 className="mt-4 text-lg font-semibold">
                                No API keys found
                            </h3>
                            <p className="mt-2 text-sm text-muted-foreground">
                                Create your first API key to enable HTTP access
                                to workflows
                            </p>
                            <Button
                                variant="outline"
                                size="icon"
                                onClick={handleCreate}
                                title="Create API Key"
                                className="mt-4"
                            >
                                <Plus className="h-4 w-4" />
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Create Dialog */}
            <Dialog
                open={isCreateDialogOpen}
                onOpenChange={setIsCreateDialogOpen}
            >
                <DialogContent className="sm:max-w-xl">
                    <form onSubmit={handleSubmitCreate}>
                        <DialogHeader>
                            <DialogTitle>Create Workflow API Key</DialogTitle>
                            <DialogDescription>
                                Generate a new API key for external systems to
                                trigger workflows. The key will only be shown
                                once - make sure to copy it.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            {/* Description Field - Required */}
                            <div className="space-y-2">
                                <Label htmlFor="description">
                                    Description{" "}
                                    <span className="text-destructive">*</span>
                                </Label>
                                <Input
                                    id="description"
                                    value={formData.description}
                                    onChange={(e) =>
                                        setFormData({
                                            ...formData,
                                            description: e.target.value,
                                        })
                                    }
                                    placeholder="Production API Key for CRM"
                                    maxLength={32}
                                    required
                                />
                                <p className="text-xs text-muted-foreground">
                                    Brief description (max 32 characters)
                                </p>
                            </div>

                            {/* Global Key Toggle */}
                            <div className="flex items-center space-x-2">
                                <Checkbox
                                    id="isGlobal"
                                    checked={formData.isGlobal}
                                    onCheckedChange={(checked) =>
                                        setFormData({
                                            ...formData,
                                            isGlobal: checked === true,
                                            workflowId:
                                                checked === true
                                                    ? ""
                                                    : formData.workflowId,
                                        })
                                    }
                                />
                                <div className="flex flex-col">
                                    <Label
                                        htmlFor="isGlobal"
                                        className="cursor-pointer font-medium"
                                    >
                                        Global Key
                                    </Label>
                                    <p className="text-xs text-muted-foreground">
                                        Allow this key to execute any workflow
                                    </p>
                                </div>
                            </div>

                            {/* Workflow Selector - Conditionally Required */}
                            {!formData.isGlobal && (
                                <div className="space-y-2">
                                    <Label htmlFor="workflowId">
                                        Workflow{" "}
                                        <span className="text-destructive">
                                            *
                                        </span>
                                    </Label>
                                    <Select
                                        value={formData.workflowId}
                                        onValueChange={(value) =>
                                            setFormData({
                                                ...formData,
                                                workflowId: value,
                                            })
                                        }
                                    >
                                        <SelectTrigger id="workflowId">
                                            <SelectValue placeholder="Select a workflow..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {availableWorkflows.length > 0 ? (
                                                availableWorkflows.map((workflow) => (
                                                    <SelectItem
                                                        key={workflow}
                                                        value={workflow}
                                                    >
                                                        {workflow}
                                                    </SelectItem>
                                                ))
                                            ) : (
                                                <SelectItem
                                                    value="_empty_"
                                                    disabled
                                                >
                                                    No workflows available
                                                </SelectItem>
                                            )}
                                        </SelectContent>
                                    </Select>
                                    <p className="text-xs text-muted-foreground">
                                        Restrict this key to a specific workflow
                                    </p>
                                </div>
                            )}

                            {/* Expiration Field - Optional */}
                            <div className="space-y-2">
                                <Label htmlFor="expiresInDays">
                                    Expiration (days)
                                </Label>
                                <Select
                                    value={formData.expiresInDays}
                                    onValueChange={(value) =>
                                        setFormData({
                                            ...formData,
                                            expiresInDays: value,
                                        })
                                    }
                                >
                                    <SelectTrigger id="expiresInDays">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="0">Never</SelectItem>
                                        <SelectItem value="30">
                                            30 days
                                        </SelectItem>
                                        <SelectItem value="60">
                                            60 days
                                        </SelectItem>
                                        <SelectItem value="90">
                                            90 days
                                        </SelectItem>
                                        <SelectItem value="180">
                                            180 days
                                        </SelectItem>
                                        <SelectItem value="365">
                                            365 days
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                                <p className="text-xs text-muted-foreground">
                                    How long until the key expires (optional)
                                </p>
                            </div>
                        </div>
                        <DialogFooter>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => setIsCreateDialogOpen(false)}
                            >
                                Cancel
                            </Button>
                            <Button
                                type="submit"
                                disabled={
                                    createMutation.isPending || !isFormValid
                                }
                            >
                                {createMutation.isPending
                                    ? "Creating..."
                                    : "Create API Key"}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* Key Display Dialog (One-Time Display) */}
            <Dialog
                open={isKeyDisplayDialogOpen}
                onOpenChange={setIsKeyDisplayDialogOpen}
            >
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Check className="h-5 w-5 text-green-500" />
                            API Key Created Successfully
                        </DialogTitle>
                        <DialogDescription>
                            This is the only time you'll be able to view this
                            key. Copy it now and store it securely.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <Alert variant="destructive">
                            <AlertTriangle className="h-4 w-4" />
                            <AlertDescription>
                                <strong>Important:</strong> This key will not be
                                shown again. Make sure to copy it before closing
                                this dialog.
                            </AlertDescription>
                        </Alert>

                        <div className="space-y-2">
                            <Label>Your API Key</Label>
                            <div className="flex gap-2">
                                <Input
                                    value={createdKey?.rawKey || ""}
                                    readOnly
                                    className="font-mono text-sm"
                                />
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="icon"
                                    onClick={handleCopyKey}
                                    className="flex-shrink-0"
                                >
                                    {copied ? (
                                        <Check className="h-4 w-4" />
                                    ) : (
                                        <Copy className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>Usage Example</Label>
                            <div className="bg-muted p-3 rounded-md">
                                <pre className="text-xs overflow-x-auto">
                                    <code>{`curl -X POST ${
                                        window.location.protocol
                                    }//${window.location.host}/api/workflows/${
                                        createdKey?.workflowId ||
                                        "{workflowName}"
                                    } \\
  -H "Authorization: Bearer ${createdKey?.rawKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"input": "your data"}'`}</code>
                                </pre>
                            </div>
                        </div>

                        {createdKey?.description && (
                            <div className="space-y-2">
                                <Label>Description</Label>
                                <p className="text-sm text-muted-foreground">
                                    {createdKey.description}
                                </p>
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <Label className="text-xs text-muted-foreground">
                                    Scope
                                </Label>
                                <p className="mt-1">
                                    {createdKey?.workflowId ? (
                                        <Badge
                                            variant="outline"
                                            className="font-mono"
                                        >
                                            {createdKey.workflowId}
                                        </Badge>
                                    ) : (
                                        <Badge variant="default">Global</Badge>
                                    )}
                                </p>
                            </div>
                            <div>
                                <Label className="text-xs text-muted-foreground">
                                    Expires
                                </Label>
                                <p className="mt-1">
                                    {createdKey?.expiresAt
                                        ? formatDate(createdKey.expiresAt)
                                        : "Never"}
                                </p>
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            type="button"
                            onClick={() => {
                                setIsKeyDisplayDialogOpen(false);
                                setCreatedKey(undefined);
                                setCopied(false);
                            }}
                        >
                            I've Copied the Key
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Revoke Confirmation Dialog */}
            <AlertDialog
                open={isRevokeDialogOpen}
                onOpenChange={setIsRevokeDialogOpen}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Revoke API Key?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will immediately revoke the API key ending in{" "}
                            <strong className="font-mono">
                                {selectedKey?.maskedKey}
                            </strong>
                            . Any systems using this key will no longer be able
                            to execute workflows. This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleConfirmRevoke}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {revokeMutation.isPending
                                ? "Revoking..."
                                : "Revoke Key"}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
