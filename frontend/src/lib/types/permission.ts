/** Permission types for frontend */

export type PermissionCategory =
  | "chat"
  | "conversations"
  | "preferences"
  | "providers"
  | "api_keys"
  | "stats"
  | "health"
  | "config"
  | "users";

export interface PermissionInfo {
  code: PermissionCategory;
  name: string;
  category: "feature" | "admin" | "system";
  description: string;
}

export interface UserPermissions {
  userId: number;
  permissions: Record<PermissionCategory, boolean>;
}

export interface PermissionCategoryGroup {
  name: string;
  permissions: PermissionInfo[];
}

export interface PermissionListResponse {
  permissions: PermissionInfo[];
  categories: string[];
}
