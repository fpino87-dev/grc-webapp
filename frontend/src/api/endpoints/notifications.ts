import { apiClient } from "../client";

export interface NotificationSubscription {
  id: string;
  event_type: string;
  channel: string;
  enabled: boolean;
}

export const notificationsApi = {
  subscriptions: () =>
    apiClient.get<{ results: NotificationSubscription[] }>("/notifications/subscriptions/").then(r => r.data.results),
  updateSubscription: (id: string, data: Partial<NotificationSubscription>) =>
    apiClient.patch<NotificationSubscription>(`/notifications/subscriptions/${id}/`, data).then(r => r.data),
};
