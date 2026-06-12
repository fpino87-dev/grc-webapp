import { useQuery } from "@tanstack/react-query";
import { controlsApi } from "../../../api/endpoints/controls";
import i18n from "../../../i18n";

export function useDetailInfo(instanceId: string | null) {
  return useQuery({
    queryKey: ["control-detail", instanceId, i18n.language],
    queryFn: () => controlsApi.detailInfo(instanceId!, i18n.language),
    enabled: !!instanceId,
    retry: false,
  });
}
