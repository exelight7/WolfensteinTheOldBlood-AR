import type { AppInfo, Status, UpdateInfo } from "./types";

export type ToastKind = "success" | "error" | "info";

export interface Controller {
  status: Status | null;
  updates: UpdateInfo | null;
  info: AppInfo | null;
  busy: string | null;
  refresh: () => Promise<void>;
  browse: () => Promise<void>;
  install: () => Promise<void>;
  update: () => Promise<void>;
  repair: () => Promise<void>;
  restore: () => Promise<void>;
  verifyBackup: () => Promise<void>;
  checkUpdates: () => Promise<void>;
  openUrl: (url: string) => void;
  notify: (kind: ToastKind, message: string) => void;
}
