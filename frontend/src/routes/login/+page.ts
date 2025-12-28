// Disable SSR for the login page and handle authentication redirect in server-side load function
import { redirect } from "@sveltejs/kit";
import { authService } from "$lib/services/auth";

export function load() {
  // 如果已经登录，重定向到首页
  if (authService.isAuthenticated()) {
    throw redirect(302, "/");
  }

  return {};
}
