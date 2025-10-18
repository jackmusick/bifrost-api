import { useState } from "react";
import { Pencil, Plus, Trash2, UserCog, RefreshCw, Users } from "lucide-react";
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
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRoles, useDeleteRole } from "@/hooks/useRoles";
import { RoleDialog } from "@/components/roles/RoleDialog";
import { RoleDetailsDialog } from "@/components/roles/RoleDetailsDialog";
import type { components } from "@/lib/v1";
type Role = components["schemas"]["Role"];

export function Roles() {
    const [selectedRole, setSelectedRole] = useState<Role | undefined>();
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [detailsRole, setDetailsRole] = useState<Role | undefined>();
    const [isDetailsOpen, setIsDetailsOpen] = useState(false);

    const { data: roles, isLoading, refetch } = useRoles();
    const deleteRole = useDeleteRole();

    const handleEdit = (role: Role) => {
        setSelectedRole(role);
        setIsDialogOpen(true);
    };

    const handleAdd = () => {
        setSelectedRole(undefined);
        setIsDialogOpen(true);
    };

    const handleDelete = (role: Role) => {
        if (confirm(`Are you sure you want to delete role "${role.name}"?`)) {
            deleteRole.mutate(role.id);
        }
    };

    const handleViewDetails = (role: Role) => {
        setDetailsRole(role);
        setIsDetailsOpen(true);
    };

    const handleDialogClose = () => {
        setIsDialogOpen(false);
        setSelectedRole(undefined);
    };

    const handleDetailsClose = () => {
        setIsDetailsOpen(false);
        setDetailsRole(undefined);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight">
                        Roles
                    </h1>
                    <p className="mt-2 text-muted-foreground">
                        Manage roles for organization users and control form
                        access
                    </p>
                </div>
                <Button variant="outline" size="icon" onClick={handleAdd} title="Create Role">
                    <Plus className="h-4 w-4" />
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle>All Roles</CardTitle>
                            <CardDescription>
                                Roles control which forms organization users can
                                access
                            </CardDescription>
                        </div>
                        <Button
                            variant="outline"
                            size="icon"
                            onClick={() => refetch()}
                        >
                            <RefreshCw className="h-4 w-4" />
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <div className="space-y-2">
                            {[...Array(5)].map((_, i) => (
                                <Skeleton key={i} className="h-12 w-full" />
                            ))}
                        </div>
                    ) : roles && roles.length > 0 ? (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Name</TableHead>
                                    <TableHead>Description</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Created</TableHead>
                                    <TableHead className="text-right">
                                        Actions
                                    </TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {roles.map((role) => (
                                    <TableRow key={role.id}>
                                        <TableCell className="font-medium">
                                            {role.name}
                                        </TableCell>
                                        <TableCell className="max-w-xs truncate text-muted-foreground">
                                            {role.description || "-"}
                                        </TableCell>
                                        <TableCell>
                                            <Badge
                                                variant={
                                                    role.isActive
                                                        ? "default"
                                                        : "secondary"
                                                }
                                            >
                                                {role.isActive
                                                    ? "Active"
                                                    : "Inactive"}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-sm text-muted-foreground">
                                            {new Date(
                                                role.createdAt
                                            ).toLocaleDateString()}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className="flex justify-end gap-2">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() =>
                                                        handleViewDetails(role)
                                                    }
                                                    title="View users and forms"
                                                >
                                                    <Users className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() =>
                                                        handleEdit(role)
                                                    }
                                                >
                                                    <Pencil className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() =>
                                                        handleDelete(role)
                                                    }
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <UserCog className="h-12 w-12 text-muted-foreground" />
                            <h3 className="mt-4 text-lg font-semibold">
                                No roles found
                            </h3>
                            <p className="mt-2 text-sm text-muted-foreground">
                                Get started by creating your first role
                            </p>
                            <Button variant="outline" size="icon" onClick={handleAdd} title="Create Role" className="mt-4">
                                <Plus className="h-4 w-4" />
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            <RoleDialog
                role={selectedRole}
                open={isDialogOpen}
                onClose={handleDialogClose}
            />

            <RoleDetailsDialog
                role={detailsRole}
                open={isDetailsOpen}
                onClose={handleDetailsClose}
            />
        </div>
    );
}
