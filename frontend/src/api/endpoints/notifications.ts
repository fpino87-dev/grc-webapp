import { apiClient } from "../client";
import { fetchAllPages } from "../pagination";

export interface NotificationSubscription {
  id: string;
  event_type: string;
  channel: string;
  enabled: boolean;
}

export const notificationsApi = {
  subscriptions: () =>
    fetchAllPages<NotificationSubscription>("/notifications/subscriptions/"),
  updateSubscription: (id: string, data: Partial<NotificationSubscription>) =>
    apiClient.patch<NotificationSubscription>(`/notifications/subscriptions/${id}/`, data).then(r => r.data),
};
