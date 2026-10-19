import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import type { AppInfo, GameInfo, InstallResult, Status, UpdateInfo } from "./types";

export const api = {
  detectGame: () => invoke<GameInfo | null>("detect_game"),
  validateGame: (path: string) => invoke<GameInfo>("validate_game", { path }),
  status: (path?: string) => invoke<Status>("get_status", { path: path ?? null }),
  install: (path: string) => invoke<InstallResult>("install", { path }),
  repair: (path: string) => invoke<InstallResult>("repair", { path }),
  restore: (path: string) => invoke<InstallResult>("restore", { path }),
  verifyBackup: (path: string) => invoke<Status>("verify_backup", { path }),
  checkUpdates: () => invoke<UpdateInfo>("check_updates"),
  appInfo: () => invoke<AppInfo>("app_info"),
  openUrl: (url: string) => invoke<void>("open_url", { url }),
  async browseFolder(): Promise<string | null> {
    const selected = await open({ directory: true, multiple: false, title: "اختر مجلد اللعبة" });
    return typeof selected === "string" ? selected : null;
  },
};

export function errorText(error: unknown): string {
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  return "حدث خطأ غير متوقع.";
}
