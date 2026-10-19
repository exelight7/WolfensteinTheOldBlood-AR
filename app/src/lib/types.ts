export type GameState =
  | "GAME_NOT_FOUND"
  | "SUPPORTED_ORIGINAL"
  | "NOT_INSTALLED"
  | "ARABIC_INSTALLED"
  | "ARABIC_UPDATE_AVAILABLE"
  | "UNKNOWN_MODIFIED_GAME"
  | "BROKEN_INSTALL";

export interface GameInfo {
  path: string;
  source: "steam" | "manual";
  steamAppId?: number | null;
  build?: string | null;
}

export interface BackupStatus {
  exists: boolean;
  verified: boolean;
  path?: string | null;
  createdAt?: string | null;
}

export interface Status {
  state: GameState;
  game?: GameInfo | null;
  installedVersion?: string | null;
  latestVersion: string;
  updateAvailable: boolean;
  backup: BackupStatus;
  message: string;
  exeFound: boolean;
}

export interface InstallResult {
  ok: boolean;
  state: GameState;
  message: string;
}

export interface UpdateInfo {
  appVersion: string;
  latestAppVersion: string;
  localizationVersion: string;
  latestLocalizationVersion: string;
  appUpdateAvailable: boolean;
  dataUpdateAvailable: boolean;
  changelogUrl: string;
  releaseUrl: string;
}

export interface AppInfo {
  appVersion: string;
  localizationVersion: string;
  github: string;
  license: string;
  issueUrl: string;
}
