use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use tauri::Manager;

use crate::backup;
use crate::config::{self, SupportedVersion};
use crate::error::{AppError, AppResult};
use crate::game::{self, Detection};
use crate::installer;
use crate::manifest::{self, ReleaseManifest};
use crate::payload;
use crate::state_store;
use crate::steam;
use crate::types::{
    AppInfo, BackupStatus, GameInfo, GameSource, GameState, InstallResult, Status, UpdateInfo,
};
use crate::version;

fn clean_path(path: PathBuf) -> PathBuf {
    let text = path.to_string_lossy().to_string();
    if let Some(rest) = text.strip_prefix(r"\\?\UNC\") {
        PathBuf::from(format!(r"\\{rest}"))
    } else if let Some(rest) = text.strip_prefix(r"\\?\") {
        PathBuf::from(rest)
    } else {
        path
    }
}

fn canonical_game(path: &str) -> AppResult<PathBuf> {
    let candidate = PathBuf::from(path);
    let canonical = fs::canonicalize(&candidate).unwrap_or(candidate);
    Ok(clean_path(canonical))
}

fn info_for(path: &Path, source: GameSource, version: &SupportedVersion) -> GameInfo {
    GameInfo {
        path: path.to_string_lossy().to_string(),
        source,
        steam_app_id: (source == GameSource::Steam).then_some(version.steam_app_id),
        build: Some(version.game_build.clone()),
    }
}

fn latest_version() -> AppResult<String> {
    Ok(config::load()?.app_version.clone())
}

fn empty_status(message: &str) -> Status {
    Status {
        state: GameState::GameNotFound,
        game: None,
        installed_version: None,
        latest_version: config::app_version(),
        update_available: false,
        backup: BackupStatus {
            exists: false,
            verified: false,
            path: None,
            created_at: None,
        },
        message: message.to_string(),
        exe_found: false,
    }
}

fn detection_status(
    game_dir: &Path,
    info: GameInfo,
    version: &SupportedVersion,
    detection: Detection,
) -> AppResult<Status> {
    let state_version = state_store::version_for(&state_store::state_path(), game_dir);
    let installed_version = match detection.state {
        GameState::ArabicInstalled => state_version.clone().or(detection.installed_version.clone()),
        GameState::ArabicUpdateAvailable => detection
            .installed_version
            .clone()
            .or(state_version.clone()),
        _ => None,
    };

    let latest = latest_version()?;
    let update_available = detection.state == GameState::ArabicUpdateAvailable
        || installed_version
            .as_deref()
            .map(|installed| version::is_newer(&latest, installed).unwrap_or(false))
            .unwrap_or(false);

    let message = if update_available {
        format!(
            "يتوفر إصدار أحدث من التعريب ({}). يمكنك التحديث الآن.",
            latest
        )
    } else {
        detection.message.clone()
    };

    Ok(Status {
        state: detection.state,
        game: Some(info),
        installed_version,
        latest_version: latest,
        update_available,
        backup: backup::info(game_dir, version),
        message,
        exe_found: game::exe_path(game_dir, version).is_file(),
    })
}

fn detect_for(path: &Path) -> AppResult<(SupportedVersion, Detection)> {
    let version = config::primary()?.clone();
    let detection = game::detect(path, &version)?;
    Ok((version, detection))
}

fn describe(state: GameState) -> &'static str {
    match state {
        GameState::ArabicInstalled => "التعريب مثبت ومحدّث.",
        GameState::ArabicUpdateAvailable => "تم تحديث التعريب بنجاح.",
        _ => "تمت العملية بنجاح.",
    }
}

fn post_install(game_dir: &Path) -> AppResult<InstallResult> {
    let (version, detection) = detect_for(game_dir)?;
    let status = detection_status(
        game_dir,
        info_for(game_dir, GameSource::Manual, &version),
        &version,
        detection.clone(),
    )?;
    Ok(InstallResult {
        ok: true,
        state: detection.state,
        message: describe(status.state).to_string(),
    })
}

#[tauri::command]
pub fn detect_game() -> Result<Option<GameInfo>, String> {
    let version = config::primary().map_err(|error| error.to_string())?;
    Ok(steam::detect_game(
        version.steam_app_id,
        &version.executable,
        steam::INSTALL_DIR_NAME,
    )
    .map(|path| info_for(&path, GameSource::Steam, version)))
}

#[tauri::command]
pub fn validate_game(path: String) -> Result<GameInfo, String> {
    let version = config::primary().map_err(|error| error.to_string())?;
    let game_dir = canonical_game(&path).map_err(|error| error.to_string())?;
    if !game_dir.is_dir() {
        return Err("المجلد المحدد غير موجود.".into());
    }
    if !game::exe_path(&game_dir, version).is_file() {
        return Err(format!(
            "المجلد لا يحتوي على {}. اختر مجلد تثبيت اللعبة الصحيح.",
            version.executable
        ));
    }
    Ok(info_for(&game_dir, GameSource::Manual, version))
}

#[tauri::command]
pub fn get_status(path: Option<String>) -> Result<Status, String> {
    get_status_inner(path).map_err(|error| error.to_string())
}

fn get_status_inner(path: Option<String>) -> AppResult<Status> {
    let version = config::primary()?;

    let (game_dir, source) = match path.filter(|value| !value.trim().is_empty()) {
        Some(value) => (canonical_game(&value)?, GameSource::Manual),
        None => match steam::detect_game(
            version.steam_app_id,
            &version.executable,
            steam::INSTALL_DIR_NAME,
        ) {
            Some(found) => (clean_path(found), GameSource::Steam),
            None => {
                return Ok(empty_status(
                    "لم يتم العثور على Wolfenstein: The Old Blood. اختر مجلد اللعبة يدويًا.",
                ))
            }
        },
    };

    if !game_dir.is_dir() || !game::exe_path(&game_dir, version).is_file() {
        return Ok(empty_status(
            "المسار المحفوظ لا يحتوي على اللعبة. اختر المجلد الصحيح.",
        ));
    }

    let detection = game::detect(&game_dir, version)?;
    detection_status(&game_dir, info_for(&game_dir, source, version), version, detection)
}

#[tauri::command]
pub async fn install(app: tauri::AppHandle, path: String) -> Result<InstallResult, String> {
    install_inner(app, path).await.map_err(|error| error.to_string())
}

async fn install_inner(app: tauri::AppHandle, path: String) -> AppResult<InstallResult> {
    let game_dir = canonical_game(&path)?;
    let (version, detection) = detect_for(&game_dir)?;
    if !game::can_install(detection.state) && detection.state != GameState::ArabicInstalled {
        return Err(AppError::msg(match detection.state {
            GameState::BrokenInstall => "التثبيت تالف؛ استخدم «إصلاح» أولًا.",
            GameState::UnknownModifiedGame => "ملفات اللعبة غير معروفة؛ لن يتم تعديلها.",
            GameState::NotInstalled => "ملفات اللعبة الأصلية غير مكتملة؛ تحقق من اللعبة عبر Steam.",
            _ => "لا يمكن التثبيت في الحالة الحالية.",
        }));
    }

    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|error| AppError::msg(format!("تعذر تحديد مجلد موارد التطبيق: {error}")))?;

    let backup_dir = if detection.state == GameState::SupportedOriginal {
        backup::create(&game_dir, &version)?
    } else {
        backup::require_valid(&game_dir, &version)?
    };
    let baseline = (detection.state != GameState::SupportedOriginal).then_some(backup_dir.as_path());

    let payload = payload::resolve(&resource_dir, &game_dir, baseline)?;
    installer::install(&game_dir, &version, &payload, detection.state)?;
    post_install(&game_dir)
}

#[tauri::command]
pub async fn repair(app: tauri::AppHandle, path: String) -> Result<InstallResult, String> {
    repair_inner(app, path).await.map_err(|error| error.to_string())
}

async fn repair_inner(app: tauri::AppHandle, path: String) -> AppResult<InstallResult> {
    let game_dir = canonical_game(&path)?;
    let (version, detection) = detect_for(&game_dir)?;

    if detection.state == GameState::UnknownModifiedGame {
        return Err(AppError::msg(
            "ملفات اللعبة غير معروفة؛ لن يقوم الإصلاح بتعديلها. استعد نسخة أصلية موثوقة أولًا.",
        ));
    }
    if detection.state == GameState::NotInstalled {
        return Err(AppError::msg(
            "ملفات اللعبة الأصلية غير مكتملة؛ أعد التحقق من اللعبة عبر Steam.",
        ));
    }

    if detection.state == GameState::BrokenInstall {
        backup::require_valid(&game_dir, &version)?;
        backup::restore(&game_dir, &version)?;
        let (_, restored) = detect_for(&game_dir)?;
        if restored.state != GameState::SupportedOriginal {
            return Err(AppError::msg(
                "تعذر إرجاع اللعبة إلى حالة أصلية موثوقة؛ تم إيقاف الإصلاح.",
            ));
        }
    }

    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|error| AppError::msg(format!("تعذر تحديد مجلد موارد التطبيق: {error}")))?;
    let state = if detection.state == GameState::BrokenInstall {
        GameState::SupportedOriginal
    } else {
        detection.state
    };

    let backup_dir = if state == GameState::SupportedOriginal {
        backup::create(&game_dir, &version)?
    } else {
        backup::require_valid(&game_dir, &version)?
    };
    let baseline = (state != GameState::SupportedOriginal).then_some(backup_dir.as_path());

    let payload = payload::resolve(&resource_dir, &game_dir, baseline)?;
    installer::install(&game_dir, &version, &payload, state)?;
    post_install(&game_dir)
}

#[tauri::command]
pub fn restore(path: String) -> Result<InstallResult, String> {
    restore_inner(path).map_err(|error| error.to_string())
}

fn restore_inner(path: String) -> AppResult<InstallResult> {
    let game_dir = canonical_game(&path)?;
    let (version, detection) = detect_for(&game_dir)?;
    if detection.state == GameState::UnknownModifiedGame {
        return Err(AppError::msg(
            "ملفات اللعبة غير معروفة؛ تم رفض الاستعادة تلقائيًا. راجع مجلد اللعبة أولًا.",
        ));
    }
    if detection.state == GameState::NotInstalled {
        return Err(AppError::msg("لا توجد ملفات أصلية لاستعادتها."));
    }
    installer::restore(&game_dir, &version)?;
    Ok(InstallResult {
        ok: true,
        state: GameState::SupportedOriginal,
        message: "تمت استعادة الملفات الأصلية والتحقق منها.".into(),
    })
}

#[tauri::command]
pub fn verify_backup(path: String) -> Result<Status, String> {
    verify_backup_inner(path).map_err(|error| error.to_string())
}

fn verify_backup_inner(path: String) -> AppResult<Status> {
    let game_dir = canonical_game(&path)?;
    let (version, detection) = detect_for(&game_dir)?;
    let mut status =
        detection_status(&game_dir, info_for(&game_dir, GameSource::Manual, &version), &version, detection)?;
    if status.backup.exists && !status.backup.verified {
        status.message = "النسخة الاحتياطية موجودة لكنها لا تطابق البصمات المعروفة.".into();
    } else if !status.backup.exists {
        status.message = "لا توجد نسخة احتياطية لهذه اللعبة بعد.".into();
    } else {
        status.message = "النسخة الاحتياطية سليمة ومطابقة للأصل.".into();
    }
    Ok(status)
}

#[tauri::command]
pub async fn check_updates() -> Result<UpdateInfo, String> {
    check_updates_inner().await.map_err(|error| error.to_string())
}

async fn check_updates_inner() -> AppResult<UpdateInfo> {
    let current_app = config::app_version();
    let manifest: ReleaseManifest =
        tauri::async_runtime::spawn_blocking(manifest::fetch_latest)
            .await
            .map_err(|error| AppError::msg(format!("تعذر تنفيذ فحص التحديثات: {error}")))??;

    let installed_localization = state_store::read()
        .map(|state| state.version)
        .unwrap_or_else(|| current_app.clone());

    Ok(UpdateInfo {
        app_version: current_app.clone(),
        latest_app_version: manifest.version.clone(),
        localization_version: installed_localization.clone(),
        latest_localization_version: manifest.version.clone(),
        app_update_available: version::is_newer(&manifest.version, &current_app)?,
        data_update_available: version::is_newer(&manifest.version, &installed_localization)?,
        changelog_url: manifest.changelog().to_string(),
        release_url: manifest::release_url(&manifest.version),
    })
}

#[tauri::command]
pub fn app_info() -> AppInfo {
    let app_version = config::app_version();
    AppInfo {
        app_version: app_version.clone(),
        localization_version: app_version,
        github: manifest::REPO.to_string(),
        license: "MIT".into(),
        issue_url: format!("{}/issues", manifest::REPO),
    }
}

#[tauri::command]
pub fn open_url(url: String) -> Result<(), String> {
    if !url.starts_with("https://github.com/exelight7/WolfensteinTheOldBlood-AR") {
        return Err("رابط غير مسموح.".into());
    }
    tauri_plugin_opener::open_url(url, None::<&str>).map_err(|error| error.to_string())
}

#[allow(dead_code)]
fn installed_hashes(game_dir: &Path) -> Option<BTreeMap<String, String>> {
    let state = state_store::read()?;
    if state
        .game_path
        .eq_ignore_ascii_case(&game_dir.to_string_lossy())
    {
        Some(state.files)
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_verbatim_prefixes() {
        assert_eq!(
            clean_path(PathBuf::from(r"\\?\C:\Games\WTOB")),
            PathBuf::from(r"C:\Games\WTOB")
        );
        assert_eq!(
            clean_path(PathBuf::from(r"\\?\UNC\server\share\WTOB")),
            PathBuf::from(r"\\server\share\WTOB")
        );
    }

    #[test]
    fn empty_status_reports_not_found() {
        let status = empty_status("missing");
        assert_eq!(status.state, GameState::GameNotFound);
        assert!(!status.update_available);
        assert_eq!(status.latest_version, config::app_version());
    }
}
