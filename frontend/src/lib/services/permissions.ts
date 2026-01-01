import { apiClient } from "./api";
import type {
  PermissionCategory,
  PermissionInfo,
  UserPermissions,
  PermissionListResponse,
} from "$types/permission";

export const permissionsService = {
  /**
   * Get list of all available permissions
   */
  async getAllPermissions(): Promise<PermissionInfo[]> {
    const response = await apiClient.get<PermissionListResponse>(
      "/api/admin/permissions"
    );
    return response.permissions;
  },

  /**
   * Get permissions for a specific user
   */
  async getUserPermissions(userId: number): Promise<UserPermissions> {
    return apiClient.get<UserPermissions>(
      `/api/admin/permissions/user/${userId}`
    );
  },

  /**
   * Update permissions for a specific user
   */
  async updateUserPermissions(
    userId: number,
    permissions: Record<PermissionCategory, boolean>
  ): Promise<{
    success: boolean;
    message: string;
    permissions: Record<string, boolean>;
  }> {
    return apiClient.put<{
      success: boolean;
      message: string;
      permissions: Record<string, boolean>;
    }>(`/api/admin/permissions/user/${userId}`, {
      user_id: userId,
      permissions,
    });
  },

  /**
   * Reset user permissions to default
   */
  async resetUserPermissions(userId: number): Promise<{
    success: boolean;
    message: string;
    permissions: Record<string, boolean>;
  }> {
    return apiClient.post<{
      success: boolean;
      message: string;
      permissions: Record<string, boolean>;
    }>(`/api/admin/permissions/user/${userId}/reset`);
  },
};
