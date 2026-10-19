use std::fs::File;
use std::io::Read;
use std::path::Path;

use sha2::{Digest, Sha256};

use crate::config::SupportedVersion;
use crate::error::{AppError, AppResult};
use crate::types::GameState;

pub const INDEX_FILE: &str = "base/chunk0.index";
pub const RESOURCES_FILE: &str = "base/chunk0.resources";
pub const LOOSE_FILE: &str = "base/graphicsdriverwarningloc.json";

#[derive(Debug, Clone)]
pub struct Detection {
    pub state: GameState,
    pub installed_version: Option<String>,
    pub message: String,
    #[allow(dead_code)]
    pub index_hash: Option<String>,
    #[allow(dead_code)]
    pub resources_hash: Option<String>,
}

pub fn hash_file(path: &Path) -> AppResult<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = vec![0u8; 1024 * 1024];
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(hex::encode(hasher.finalize()))
}

pub fn hash_opt(path: &Path) -> AppResult<Option<String>> {
    if path.is_file() {
        Ok(Some(hash_file(path)?))
    } else {
        Ok(None)
    }
}

pub fn exe_path(game_dir: &Path, version: &SupportedVersion) -> std::path::PathBuf {
    game_dir.join(&version.executable)
}

pub fn detect(game_dir: &Path, version: &SupportedVersion) -> AppResult<Detection> {
    if !game_dir.is_dir() {
        return Err(AppError::msg(format!(
            "مجلد اللعبة غير موجود: {}",
            game_dir.display()
        )));
    }
    if !exe_path(game_dir, version).is_file() {
        return Err(AppError::msg(format!(
            "لم يتم العثور على {} داخل المجلد المحدد.",
            version.executable
        )));
    }

    let index = hash_opt(&game_dir.join(INDEX_FILE))?;
    let resources = hash_opt(&game_dir.join(RESOURCES_FILE))?;

    if index.is_none() && resources.is_none() {
        return Ok(Detection {
            state: GameState::NotInstalled,
            installed_version: None,
            message: "ملفات اللعبة الأساسية (chunk0) غير موجودة. أعد التحقق من اللعبة عبر Steam أولًا.".into(),
            index_hash: index,
            resources_hash: resources,
        });
    }

    let index_is = |hash: Option<&str>| index.as_deref().is_some() && index.as_deref() == hash;
    let resources_is =
        |hash: Option<&str>| resources.as_deref().is_some() && resources.as_deref() == hash;

    let vanilla_index = version.vanilla_hash(INDEX_FILE);
    let vanilla_resources = version.vanilla_hash(RESOURCES_FILE);
    let localized_index = version.localized_hash(INDEX_FILE);
    let localized_resources = version.localized_hash(RESOURCES_FILE);

    if index_is(localized_index) && resources_is(localized_resources) {
        return Ok(Detection {
            state: GameState::ArabicInstalled,
            installed_version: Some(crate::config::app_version()),
            message: "التعريب مثبت ومطابق لأحدث إصدار.".into(),
            index_hash: index,
            resources_hash: resources,
        });
    }

    for state in &version.also_accepted_states {
        let matches_index = state
            .get(INDEX_FILE)
            .map(|hash| index_is(Some(hash)))
            .unwrap_or(false);
        let matches_resources = state
            .get(RESOURCES_FILE)
            .map(|hash| resources_is(Some(hash)))
            .unwrap_or(false);
        if matches_index && matches_resources {
            let label = state.get("label").cloned().unwrap_or_else(|| "سابق".into());
            return Ok(Detection {
                state: GameState::ArabicUpdateAvailable,
                installed_version: Some(
                    state
                        .get("localization_version")
                        .cloned()
                        .unwrap_or_else(|| "0.9.0".into()),
                ),
                message: format!("لديك إصدار سابق من التعريب ({label}). يمكنك التحديث إلى 1.0.0."),
                index_hash: index,
                resources_hash: resources,
            });
        }
    }

    if index_is(vanilla_index) && resources_is(vanilla_resources) {
        return Ok(Detection {
            state: GameState::SupportedOriginal,
            installed_version: None,
            message: "تم العثور على نسخة أصلية مدعومة. يمكنك تثبيت التعريب بأمان.".into(),
            index_hash: index,
            resources_hash: resources,
        });
    }

    let index_known = index_is(vanilla_index) || index_is(localized_index);
    let resources_known = resources_is(vanilla_resources) || resources_is(localized_resources);

    if (index_known && resources.is_none()) || (resources_known && index.is_none()) {
        return Ok(Detection {
            state: GameState::BrokenInstall,
            installed_version: None,
            message: "أحد ملفي chunk0 مفقود. أوقف اللعبة وأعد الإصلاح أو الاستعادة.".into(),
            index_hash: index,
            resources_hash: resources,
        });
    }

    if (index_known && !resources_known) || (resources_known && !index_known) {
        return Ok(Detection {
            state: GameState::BrokenInstall,
            installed_version: None,
            message: "ملفات التعريب غير متطابقة (خليط بين الأصلي والمعدّل). استخدم الإصلاح أو الاستعادة.".into(),
            index_hash: index,
            resources_hash: resources,
        });
    }

    Ok(Detection {
        state: GameState::UnknownModifiedGame,
        installed_version: None,
        message: "ملفات اللعبة غير معروفة ولن يتم تعديلها تلقائيًا. قد تكون معدّلة بأداة أخرى أو من إصدار مختلف.".into(),
        index_hash: index,
        resources_hash: resources,
    })
}

pub fn can_install(state: GameState) -> bool {
    matches!(
        state,
        GameState::SupportedOriginal | GameState::ArabicUpdateAvailable
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;
    use std::path::PathBuf;

    fn temp_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "wtob-game-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(dir.join("base")).unwrap();
        dir
    }

    fn write(path: &Path, bytes: &[u8]) -> String {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).unwrap();
        }
        std::fs::write(path, bytes).unwrap();
        hash_file(path).unwrap()
    }

    fn version_for(dir: &Path) -> SupportedVersion {
        let index = hash_file(&dir.join(INDEX_FILE)).unwrap();
        let resources = hash_file(&dir.join(RESOURCES_FILE)).unwrap();
        let mut vanilla = BTreeMap::new();
        vanilla.insert(INDEX_FILE.to_string(), index);
        vanilla.insert(RESOURCES_FILE.to_string(), resources);
        let mut localized = BTreeMap::new();
        localized.insert(INDEX_FILE.to_string(), "a".repeat(64));
        localized.insert(RESOURCES_FILE.to_string(), "b".repeat(64));
        SupportedVersion {
            id: "test".into(),
            label: "test".into(),
            store: "steam".into(),
            steam_app_id: 350080,
            game_build: "616161".into(),
            platform: "windows-x64".into(),
            executable: "WolfOldBlood_x64.exe".into(),
            executable_sha256: "c".repeat(64),
            vanilla,
            localized,
            also_accepted_states: vec![],
        }
    }

    #[test]
    fn hashes_known_content() {
        let dir = temp_dir("hash");
        let hash = write(&dir.join("sample.bin"), b"abc");
        assert_eq!(
            hash,
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn detects_supported_original() {
        let dir = temp_dir("original");
        write(&dir.join("WolfOldBlood_x64.exe"), b"exe");
        write(&dir.join(INDEX_FILE), b"index");
        write(&dir.join(RESOURCES_FILE), b"resources");
        let version = version_for(&dir);
        let detection = detect(&dir, &version).unwrap();
        assert_eq!(detection.state, GameState::SupportedOriginal);
        assert!(detection.installed_version.is_none());
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn detects_arabic_installed() {
        let dir = temp_dir("installed");
        write(&dir.join("WolfOldBlood_x64.exe"), b"exe");
        write(&dir.join(INDEX_FILE), b"index");
        write(&dir.join(RESOURCES_FILE), b"resources");
        let mut version = version_for(&dir);
        let index = hash_file(&dir.join(INDEX_FILE)).unwrap();
        let resources = hash_file(&dir.join(RESOURCES_FILE)).unwrap();
        version.localized.insert(INDEX_FILE.into(), index);
        version.localized.insert(RESOURCES_FILE.into(), resources);
        let detection = detect(&dir, &version).unwrap();
        assert_eq!(detection.state, GameState::ArabicInstalled);
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn detects_previous_build_as_update() {
        let dir = temp_dir("update");
        write(&dir.join("WolfOldBlood_x64.exe"), b"exe");
        let index = write(&dir.join(INDEX_FILE), b"old-index");
        let resources = write(&dir.join(RESOURCES_FILE), b"old-resources");
        let mut version = version_for(&dir);
        version.vanilla.insert(INDEX_FILE.into(), "d".repeat(64));
        version.vanilla.insert(RESOURCES_FILE.into(), "e".repeat(64));
        let mut previous = BTreeMap::new();
        previous.insert(INDEX_FILE.to_string(), index);
        previous.insert(RESOURCES_FILE.to_string(), resources);
        previous.insert("label".into(), "previous".into());
        version.also_accepted_states.push(previous);
        let detection = detect(&dir, &version).unwrap();
        assert_eq!(detection.state, GameState::ArabicUpdateAvailable);
        assert_eq!(detection.installed_version.as_deref(), Some("0.9.0"));
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn detects_mixed_and_unknown_states() {
        let dir = temp_dir("mixed");
        write(&dir.join("WolfOldBlood_x64.exe"), b"exe");
        let index = write(&dir.join(INDEX_FILE), b"index");
        write(&dir.join(RESOURCES_FILE), b"stranger");
        let mut version = version_for(&dir);
        version.vanilla.insert(INDEX_FILE.into(), index);
        version.vanilla.insert(RESOURCES_FILE.into(), "f".repeat(64));
        let detection = detect(&dir, &version).unwrap();
        assert_eq!(detection.state, GameState::BrokenInstall);

        std::fs::write(dir.join(RESOURCES_FILE), b"another").unwrap();
        std::fs::write(dir.join(INDEX_FILE), b"another-index").unwrap();
        let detection = detect(&dir, &version).unwrap();
        assert_eq!(detection.state, GameState::UnknownModifiedGame);
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn missing_chunks_is_not_installed() {
        let dir = temp_dir("empty");
        write(&dir.join("WolfOldBlood_x64.exe"), b"exe");
        write(&dir.join(INDEX_FILE), b"index");
        write(&dir.join(RESOURCES_FILE), b"resources");
        let version = version_for(&dir);
        std::fs::remove_file(dir.join(INDEX_FILE)).unwrap();
        std::fs::remove_file(dir.join(RESOURCES_FILE)).unwrap();
        let detection = detect(&dir, &version).unwrap();
        assert_eq!(detection.state, GameState::NotInstalled);
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn rejects_folder_without_exe() {
        let dir = temp_dir("no-exe");
        write(&dir.join(INDEX_FILE), b"index");
        write(&dir.join(RESOURCES_FILE), b"resources");
        let version = version_for(&dir);
        assert!(detect(&dir, &version).is_err());
        std::fs::remove_dir_all(dir).ok();
    }
}
