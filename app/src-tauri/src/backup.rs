use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::config::SupportedVersion;
use crate::error::{AppError, AppResult};
use crate::game::{hash_opt, INDEX_FILE, LOOSE_FILE, RESOURCES_FILE};
use crate::state_store;
use crate::types::BackupStatus;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BackupManifest {
    pub schema: u32,
    pub game_path: String,
    pub created_at: String,
    pub index_sha256: String,
    pub resources_sha256: String,
    #[serde(default)]
    pub loose_sha256: Option<String>,
}

pub fn backup_root() -> PathBuf {
    state_store::data_dir().join("backup")
}

fn dir_in(root: &Path, game_dir: &Path) -> PathBuf {
    let key = game_dir.to_string_lossy().to_lowercase();
    let digest = hex::encode(Sha256::digest(key.as_bytes()));
    root.join(format!("backup-{}", &digest[..16]))
}

pub fn info(game_dir: &Path, version: &SupportedVersion) -> BackupStatus {
    info_in(&backup_root(), game_dir, version)
}

pub fn create(game_dir: &Path, version: &SupportedVersion) -> AppResult<PathBuf> {
    create_in(&backup_root(), game_dir, version)
}

pub fn require_valid(game_dir: &Path, version: &SupportedVersion) -> AppResult<PathBuf> {
    require_valid_in(&backup_root(), game_dir, version)
}

pub fn restore(game_dir: &Path, version: &SupportedVersion) -> AppResult<()> {
    restore_in(&backup_root(), game_dir, version)
}

fn info_in(root: &Path, game_dir: &Path, version: &SupportedVersion) -> BackupStatus {
    let dir = dir_in(root, game_dir);
    let exists = dir.join("backup.json").is_file();
    let manifest = read_manifest(&dir);
    let verified = exists
        && manifest
            .as_ref()
            .map(|m| verify_manifest(&dir, game_dir, version, m))
            .unwrap_or(false);
    BackupStatus {
        exists,
        verified,
        path: exists.then(|| dir.to_string_lossy().to_string()),
        created_at: manifest.map(|m| m.created_at),
    }
}

fn read_manifest(dir: &Path) -> Option<BackupManifest> {
    let text = fs::read_to_string(dir.join("backup.json")).ok()?;
    serde_json::from_str(&text).ok()
}

fn create_in(root: &Path, game_dir: &Path, version: &SupportedVersion) -> AppResult<PathBuf> {
    let dir = dir_in(root, game_dir);
    if dir.join("backup.json").exists() {
        let manifest = read_manifest(&dir).ok_or_else(|| {
            AppError::msg("النسخة الاحتياطية موجودة لكن بيانها تالف؛ لن تتم الكتابة فوقها.")
        })?;
        if verify_manifest(&dir, game_dir, version, &manifest) {
            return Ok(dir);
        }
        return Err(AppError::msg(
            "توجد نسخة احتياطية لكنها لا تطابق البصمات المعروفة؛ تم رفض الكتابة فوقها.",
        ));
    }

    let index = game_dir.join(INDEX_FILE);
    let resources = game_dir.join(RESOURCES_FILE);
    let index_hash = hash_opt(&index)?.ok_or_else(|| {
        AppError::msg("ملف chunk0.index غير موجود؛ لا يمكن إنشاء نسخة احتياطية أصلية.")
    })?;
    let resources_hash = hash_opt(&resources)?.ok_or_else(|| {
        AppError::msg("ملف chunk0.resources غير موجود؛ لا يمكن إنشاء نسخة احتياطية أصلية.")
    })?;

    if version.vanilla_hash(INDEX_FILE) != Some(index_hash.as_str())
        || version.vanilla_hash(RESOURCES_FILE) != Some(resources_hash.as_str())
    {
        return Err(AppError::msg(
            "ملفات اللعبة ليست أصلية؛ لا يمكن إنشاء نسخة احتياطية موثوقة. استعد الأصلية أولًا.",
        ));
    }

    let loose = game_dir.join(LOOSE_FILE);
    let loose_hash = hash_opt(&loose)?;
    let original_loose = loose_hash.filter(|hash| {
        version
            .vanilla_hash(LOOSE_FILE)
            .map(|vanilla| vanilla == hash.as_str())
            .unwrap_or(false)
    });

    fs::create_dir_all(root)?;
    let staging = root.join(format!(
        "staging-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0)
    ));
    if staging.exists() {
        fs::remove_dir_all(&staging)?;
    }
    fs::create_dir_all(&staging)?;

    fs::copy(&index, staging.join("chunk0.index"))?;
    fs::copy(&resources, staging.join("chunk0.resources"))?;
    if original_loose.is_some() {
        fs::copy(&loose, staging.join("graphicsdriverwarningloc.json"))?;
    }

    let manifest = BackupManifest {
        schema: 1,
        game_path: game_dir.to_string_lossy().to_string(),
        created_at: state_store::now(),
        index_sha256: index_hash,
        resources_sha256: resources_hash,
        loose_sha256: original_loose,
    };
    fs::write(
        staging.join("backup.json"),
        serde_json::to_vec_pretty(&manifest)?,
    )?;

    fs::rename(&staging, &dir)?;
    Ok(dir)
}

fn verify_manifest(
    dir: &Path,
    game_dir: &Path,
    version: &SupportedVersion,
    manifest: &BackupManifest,
) -> bool {
    if manifest.schema != 1 {
        return false;
    }
    if !manifest
        .game_path
        .eq_ignore_ascii_case(&game_dir.to_string_lossy())
    {
        return false;
    }
    if version.vanilla_hash(INDEX_FILE) != Some(manifest.index_sha256.as_str())
        || version.vanilla_hash(RESOURCES_FILE) != Some(manifest.resources_sha256.as_str())
    {
        return false;
    }
    let index_ok = hash_opt(&dir.join("chunk0.index"))
        .ok()
        .flatten()
        .map(|hash| hash == manifest.index_sha256)
        .unwrap_or(false);
    let resources_ok = hash_opt(&dir.join("chunk0.resources"))
        .ok()
        .flatten()
        .map(|hash| hash == manifest.resources_sha256)
        .unwrap_or(false);
    if !index_ok || !resources_ok {
        return false;
    }
    match &manifest.loose_sha256 {
        Some(expected) => {
            if version.vanilla_hash(LOOSE_FILE) != Some(expected.as_str()) {
                return false;
            }
            hash_opt(&dir.join("graphicsdriverwarningloc.json"))
                .ok()
                .flatten()
                .map(|hash| &hash == expected)
                .unwrap_or(false)
        }
        None => true,
    }
}

#[cfg(test)]
fn verify_in(root: &Path, game_dir: &Path, version: &SupportedVersion) -> AppResult<bool> {
    let dir = dir_in(root, game_dir);
    let manifest = read_manifest(&dir).ok_or_else(|| AppError::msg("لا توجد نسخة احتياطية."))?;
    Ok(verify_manifest(&dir, game_dir, version, &manifest))
}

fn require_valid_in(
    root: &Path,
    game_dir: &Path,
    version: &SupportedVersion,
) -> AppResult<PathBuf> {
    let dir = dir_in(root, game_dir);
    let manifest = read_manifest(&dir).ok_or_else(|| {
        AppError::msg("لا توجد نسخة احتياطية أصلية؛ لا يمكن المتابعة بأمان.")
    })?;
    if !verify_manifest(&dir, game_dir, version, &manifest) {
        return Err(AppError::msg(
            "النسخة الاحتياطية غير مطابقة للبصمات؛ تم إيقاف العملية.",
        ));
    }
    Ok(dir)
}

fn restore_in(root: &Path, game_dir: &Path, version: &SupportedVersion) -> AppResult<()> {
    let dir = require_valid_in(root, game_dir, version)?;
    let manifest = read_manifest(&dir).expect("validated manifest");

    replace_from(&dir.join("chunk0.index"), &game_dir.join(INDEX_FILE))?;
    replace_from(
        &dir.join("chunk0.resources"),
        &game_dir.join(RESOURCES_FILE),
    )?;

    let loose_target = game_dir.join(LOOSE_FILE);
    match &manifest.loose_sha256 {
        Some(_) => replace_from(&dir.join("graphicsdriverwarningloc.json"), &loose_target)?,
        None => {
            if loose_target.exists() {
                fs::remove_file(&loose_target)?;
            }
        }
    }

    let index_ok =
        hash_opt(&game_dir.join(INDEX_FILE))?.as_deref() == version.vanilla_hash(INDEX_FILE);
    let resources_ok = hash_opt(&game_dir.join(RESOURCES_FILE))?.as_deref()
        == version.vanilla_hash(RESOURCES_FILE);
    if !index_ok || !resources_ok {
        return Err(AppError::msg(
            "فشل التحقق بعد الاستعادة؛ الملفات لا تطابق الأصل.",
        ));
    }

    Ok(())
}

fn replace_from(source: &Path, target: &Path) -> AppResult<()> {
    let parent = target
        .parent()
        .ok_or_else(|| AppError::msg("مسار هدف غير صالح"))?;
    fs::create_dir_all(parent)?;
    let file_name = target
        .file_name()
        .ok_or_else(|| AppError::msg("اسم ملف غير صالح"))?
        .to_string_lossy()
        .to_string();
    let rollback = parent.join(format!(".{file_name}.ar-old-{}", std::process::id()));
    let mut had_original = false;
    if target.exists() {
        if rollback.exists() {
            fs::remove_file(&rollback)?;
        }
        fs::rename(target, &rollback)?;
        had_original = true;
    }
    match fs::copy(source, target) {
        Ok(_) => {
            if had_original {
                let _ = fs::remove_file(&rollback);
            }
            Ok(())
        }
        Err(error) => {
            let _ = fs::remove_file(target);
            if had_original {
                let _ = fs::rename(&rollback, target);
            }
            Err(error.into())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::game::hash_file;
    use std::collections::BTreeMap;

    fn temp_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "wtob-backup-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(dir.join("game").join("base")).unwrap();
        std::fs::create_dir_all(dir.join("root")).unwrap();
        dir
    }

    struct Fixture {
        base: PathBuf,
        game: PathBuf,
        root: PathBuf,
        version: SupportedVersion,
    }

    fn fixture(tag: &str) -> Fixture {
        let base = temp_dir(tag);
        let game = base.join("game");
        let root = base.join("root");
        let index = game.join(INDEX_FILE);
        let resources = game.join(RESOURCES_FILE);
        let loose = game.join(LOOSE_FILE);
        std::fs::write(&index, b"original-index").unwrap();
        std::fs::write(&resources, b"original-resources").unwrap();
        std::fs::write(&loose, b"original-english").unwrap();
        let mut version = SupportedVersion {
            id: "test".into(),
            label: "test".into(),
            store: "steam".into(),
            steam_app_id: 350080,
            game_build: "616161".into(),
            platform: "windows-x64".into(),
            executable: "WolfOldBlood_x64.exe".into(),
            executable_sha256: "0".repeat(64),
            vanilla: BTreeMap::new(),
            localized: BTreeMap::new(),
            also_accepted_states: vec![],
        };
        version
            .vanilla
            .insert(INDEX_FILE.into(), hash_file(&index).unwrap());
        version
            .vanilla
            .insert(RESOURCES_FILE.into(), hash_file(&resources).unwrap());
        version
            .vanilla
            .insert(LOOSE_FILE.into(), hash_file(&loose).unwrap());
        Fixture {
            base,
            game,
            root,
            version,
        }
    }

    #[test]
    fn creates_and_verifies_backup() {
        let f = fixture("create");
        let backup = create_in(&f.root, &f.game, &f.version).unwrap();
        assert!(backup.join("backup.json").is_file());
        assert!(verify_in(&f.root, &f.game, &f.version).unwrap());
        assert!(info_in(&f.root, &f.game, &f.version).verified);
        std::fs::remove_dir_all(f.base).ok();
    }

    #[test]
    fn refuses_to_backup_modified_files() {
        let f = fixture("modified");
        std::fs::write(f.game.join(INDEX_FILE), b"arabic").unwrap();
        assert!(create_in(&f.root, &f.game, &f.version).is_err());
        std::fs::remove_dir_all(f.base).ok();
    }

    #[test]
    fn refuses_to_overwrite_corrupt_backup() {
        let f = fixture("corrupt");
        let backup = create_in(&f.root, &f.game, &f.version).unwrap();
        std::fs::write(backup.join("chunk0.index"), b"tampered").unwrap();
        assert!(!verify_in(&f.root, &f.game, &f.version).unwrap());
        assert!(create_in(&f.root, &f.game, &f.version).is_err());
        std::fs::remove_dir_all(f.base).ok();
    }

    #[test]
    fn restores_vanilla_files() {
        let f = fixture("restore");
        create_in(&f.root, &f.game, &f.version).unwrap();
        std::fs::write(f.game.join(INDEX_FILE), b"arabic-index").unwrap();
        std::fs::write(f.game.join(RESOURCES_FILE), b"arabic-resources").unwrap();
        std::fs::write(f.game.join(LOOSE_FILE), b"arabic-loose").unwrap();
        restore_in(&f.root, &f.game, &f.version).unwrap();
        assert_eq!(
            std::fs::read(f.game.join(INDEX_FILE)).unwrap(),
            b"original-index"
        );
        assert_eq!(
            std::fs::read(f.game.join(RESOURCES_FILE)).unwrap(),
            b"original-resources"
        );
        assert_eq!(
            std::fs::read(f.game.join(LOOSE_FILE)).unwrap(),
            b"original-english"
        );
        std::fs::remove_dir_all(f.base).ok();
    }

    #[test]
    fn removes_loose_file_when_original_had_none() {
        let mut f = fixture("no-loose");
        std::fs::remove_file(f.game.join(LOOSE_FILE)).unwrap();
        f.version.vanilla.remove(LOOSE_FILE);
        create_in(&f.root, &f.game, &f.version).unwrap();
        std::fs::write(f.game.join(LOOSE_FILE), b"arabic-loose").unwrap();
        restore_in(&f.root, &f.game, &f.version).unwrap();
        assert!(!f.game.join(LOOSE_FILE).exists());
        std::fs::remove_dir_all(f.base).ok();
    }

    #[test]
    fn missing_backup_fails_closed() {
        let f = fixture("missing");
        assert!(restore_in(&f.root, &f.game, &f.version).is_err());
        assert!(verify_in(&f.root, &f.game, &f.version).is_err());
        std::fs::remove_dir_all(f.base).ok();
    }
}
