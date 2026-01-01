// Disable SSR for the login page and handle authentication redirect in server-side load function
import { redirect } from "@sveltejs/kit";
import { authService } from "$lib/services/auth";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch }) => {
  // 如果已经登录，重定向到首页
  if (authService.isAuthenticated()) {
    throw redirect(302, "/");
  }

  // 服务端预加载 OAuth 提供商配置，避免客户端渲染时闪烁
  try {
    const response = await fetch("/oauth/providers");
    if (response.ok) {
      const data = await response.json();
      return { oauthProviders: data.providers || {} };
    }
  } catch (error) {
    console.error("Failed to load OAuth providers:", error);
  }

  return { oauthProviders: {} };
};
