use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use crate::backup;
use crate::config::SupportedVersion;
use crate::error::{AppError, AppResult};
use crate::game::{self, hash_file};
use crate::payload::Payload;
use crate::state_store;
use crate::types::GameState;

pub fn install(
    game_dir: &Path,
    version: &SupportedVersion,
    payload: &Payload,
    state: GameState,
) -> AppResult<BTreeMap<String, String>> {
    if !game::can_install(state) && state != GameState::ArabicInstalled {
        return Err(AppError::msg(match state {
            GameState::BrokenInstall => "التثبيت تالف؛ استخدم «إصلاح» لاستعادة الأصل ثم التثبيت.",
            GameState::UnknownModifiedGame => "ملفات اللعبة غير معروفة؛ لن يتم تعديلها.",
            _ => "لا يمكن التثبيت في الحالة الحالية.",
        }));
    }
    if is_game_running(&version.executable) {
        return Err(AppError::msg("أغلق اللعبة أولًا ثم أعد المحاولة."));
    }

    if state == GameState::SupportedOriginal {
        backup::create(game_dir, version)?;
    } else {
        backup::require_valid(game_dir, version)?;
    }

    let hashes = apply_payload(game_dir, payload)?;
    if let Err(error) = state_store::write(game_dir, &payload.version, hashes.clone()) {
        let _ = backup::restore(game_dir, version);
        return Err(AppError::msg(format!(
            "تعذر حفظ حالة التثبيت؛ تمت استعادة الملفات الأصلية. {error}"
        )));
    }
    Ok(hashes)
}

pub fn apply_payload(
    game_dir: &Path,
    payload: &Payload,
) -> AppResult<BTreeMap<String, String>> {
    let base = game_dir.join("base");
    if !base.is_dir() {
        return Err(AppError::msg("مجلد base غير موجود داخل اللعبة."));
    }

    let staging = base.join(format!(
        ".wtob-ar-staging-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0)
    ));
    fs::create_dir_all(&staging)?;

    let result = (|| -> AppResult<BTreeMap<String, String>> {
        for (relative, expected) in payload.hashes() {
            let bare = relative.strip_prefix("base/").unwrap_or(relative);
            let staged = staging.join(bare);
            if let Some(parent) = staged.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::copy(payload.source_for(relative), &staged)?;
            let staged_hash = hash_file(&staged)?;
            if &staged_hash != expected {
                return Err(AppError::msg(format!(
                    "تلف في ملف الحزمة أثناء التجهيز: {relative}"
                )));
            }
        }

        let mut applied: Vec<Applied> = Vec::new();
        let mut installed = BTreeMap::new();

        for (relative, expected) in payload.hashes() {
            let target = game_dir.join(relative);
            let bare = relative.strip_prefix("base/").unwrap_or(relative);
            let staged = staging.join(bare);
            let parent = target
                .parent()
                .ok_or_else(|| AppError::msg("مسار هدف غير صالح"))?;
            let file_name = target
                .file_name()
                .ok_or_else(|| AppError::msg("اسم ملف غير صالح"))?
                .to_string_lossy()
                .to_string();
            let rollback = parent.join(format!(".{file_name}.ar-old-{}", std::process::id()));

            let existed = target.exists();
            if existed {
                if rollback.exists() {
                    fs::remove_file(&rollback)?;
                }
                fs::rename(&target, &rollback)?;
            }

            if let Err(error) = fs::rename(&staged, &target) {
                if existed {
                    let _ = fs::rename(&rollback, &target);
                }
                revert(&applied);
                return Err(error.into());
            }

            applied.push(Applied {
                target: target.clone(),
                rollback,
                existed,
            });

            let actual = hash_file(&target)?;
            if &actual != expected {
                revert(&applied);
                return Err(AppError::msg(format!(
                    "فشل التحقق بعد الكتابة: {relative}"
                )));
            }
            installed.insert(relative.clone(), actual);
        }

        for entry in &applied {
            if entry.existed {
                let _ = fs::remove_file(&entry.rollback);
            }
        }

        Ok(installed)
    })();

    let _ = fs::remove_dir_all(&staging);
    result
}

struct Applied {
    target: PathBuf,
    rollback: PathBuf,
    existed: bool,
}

fn revert(applied: &[Applied]) {
    for entry in applied.iter().rev() {
        let _ = fs::remove_file(&entry.target);
        if entry.existed {
            let _ = fs::rename(&entry.rollback, &entry.target);
        }
    }
}

pub fn restore(game_dir: &Path, version: &SupportedVersion) -> AppResult<()> {
    if is_game_running(&version.executable) {
        return Err(AppError::msg("أغلق اللعبة أولًا ثم أعد المحاولة."));
    }
    backup::restore(game_dir, version)?;
    let _ = state_store::clear();
    Ok(())
}

pub fn is_game_running(executable: &str) -> bool {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let filter = format!("IMAGENAME eq {executable}");
        let output = std::process::Command::new("tasklist")
            .args(["/FI", &filter, "/NH"])
            .creation_flags(0x0800_0000)
            .output();
        if let Ok(output) = output {
            let text = String::from_utf8_lossy(&output.stdout).to_lowercase();
            return text.contains(&executable.to_lowercase());
        }
        false
    }
    #[cfg(not(windows))]
    {
        let _ = executable;
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::game::{INDEX_FILE, LOOSE_FILE, RESOURCES_FILE};
    use crate::payload::{normalize_key, Payload};

    fn temp_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "wtob-installer-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(dir.join("game").join("base")).unwrap();
        fs::create_dir_all(dir.join("payload")).unwrap();
        dir
    }

    fn payload_for(dir: &Path) -> Payload {
        let mut files = BTreeMap::new();
        for (name, bytes) in [
            ("chunk0.index", b"new-index".as_slice()),
            ("chunk0.resources", b"new-resources".as_slice()),
            ("graphicsdriverwarningloc.json", b"new-loose".as_slice()),
        ] {
            let path = dir.join(name);
            fs::write(&path, bytes).unwrap();
            files.insert(
                normalize_key(name).unwrap(),
                hash_file(&path).unwrap(),
            );
        }
        Payload {
            dir: dir.to_path_buf(),
            version: "1.0.0".into(),
            files,
        }
    }

    #[test]
    fn applies_payload_transactionally() {
        let base = temp_dir("apply");
        let game_dir = base.join("game");
        fs::write(game_dir.join(INDEX_FILE), b"old-index").unwrap();
        fs::write(game_dir.join(RESOURCES_FILE), b"old-resources").unwrap();
        fs::write(game_dir.join(LOOSE_FILE), b"old-loose").unwrap();

        let payload = payload_for(&base.join("payload"));
        let installed = apply_payload(&game_dir, &payload).unwrap();

        assert_eq!(fs::read(game_dir.join(INDEX_FILE)).unwrap(), b"new-index");
        assert_eq!(
            fs::read(game_dir.join(RESOURCES_FILE)).unwrap(),
            b"new-resources"
        );
        assert_eq!(
            fs::read(game_dir.join(LOOSE_FILE)).unwrap(),
            b"new-loose"
        );
        assert_eq!(installed.len(), 3);
        let leftovers: Vec<_> = fs::read_dir(game_dir.join("base"))
            .unwrap()
            .filter_map(Result::ok)
            .filter(|entry| entry.file_name().to_string_lossy().contains("ar-old"))
            .collect();
        assert!(leftovers.is_empty());
        fs::remove_dir_all(base).ok();
    }

    #[test]
    fn revert_restores_previous_files() {
        let base = temp_dir("revert");
        let target = base.join("target.txt");
        let rollback = base.join("rollback.txt");
        fs::write(&target, b"new").unwrap();
        fs::write(&rollback, b"old").unwrap();
        revert(&[Applied {
            target: target.clone(),
            rollback,
            existed: true,
        }]);
        assert_eq!(fs::read(&target).unwrap(), b"old");
        fs::remove_dir_all(base).ok();
    }

    #[test]
    fn rejects_unknown_state_without_touching_files() {
        let base = temp_dir("guard");
        let game_dir = base.join("game");
        fs::write(game_dir.join(INDEX_FILE), b"original").unwrap();
        let payload = payload_for(&base.join("payload"));
        let version = SupportedVersion {
            id: "test".into(),
            label: "test".into(),
            store: "steam".into(),
            steam_app_id: 350080,
            game_build: "616161".into(),
            platform: "windows-x64".into(),
            executable: "does-not-exist.exe".into(),
            executable_sha256: "0".repeat(64),
            vanilla: BTreeMap::new(),
            localized: BTreeMap::new(),
            also_accepted_states: vec![],
        };
        let error = install(
            &game_dir,
            &version,
            &payload,
            GameState::UnknownModifiedGame,
        )
        .unwrap_err();
        assert!(error.to_string().contains("غير معروفة"));
        assert_eq!(fs::read(game_dir.join(INDEX_FILE)).unwrap(), b"original");
        fs::remove_dir_all(base).ok();
    }
}
