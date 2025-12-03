import { useQuery } from "@tanstack/react-query";
import { getSystemLogs, type GetSystemLogsParams } from "@/services/logs";
import { useAuth } from "@/contexts/AuthContext";

export function useSystemLogs(params: GetSystemLogsParams = {}) {
	const { user } = useAuth();

	return useQuery({
		queryKey: ["systemLogs", params],
		queryFn: () => getSystemLogs(params),
		enabled: !!user,
		staleTime: 30000, // 30 seconds
	});
}
