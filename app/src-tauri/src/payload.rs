use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use serde::Deserialize;

use crate::error::{AppError, AppResult};
use crate::game::{hash_file, INDEX_FILE, LOOSE_FILE, RESOURCES_FILE};
use crate::state_store;

#[derive(Debug, Clone, Deserialize)]
pub struct PayloadManifest {
    #[serde(default)]
    pub version: Option<String>,
    pub files: BTreeMap<String, String>,
}

#[derive(Debug, Clone)]
pub struct Payload {
    pub dir: PathBuf,
    pub version: String,
    pub files: BTreeMap<String, String>,
}

impl Payload {
    pub fn hashes(&self) -> &BTreeMap<String, String> {
        &self.files
    }

    pub fn source_for(&self, relative: &str) -> PathBuf {
        let bare = relative.strip_prefix("base/").unwrap_or(relative);
        self.dir.join(bare)
    }
}

pub fn resolve(
    resource_dir: &Path,
    game_dir: &Path,
    baseline: Option<&Path>,
) -> AppResult<Payload> {
    let assets = resource_dir.join("resources");
    let mut candidates = vec![
        assets.join("localization"),
        resource_dir.join("localization"),
        assets.join("localization-data"),
        resource_dir.join("localization-data"),
    ];
    if cfg!(debug_assertions) {
        candidates.push(
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../workspace/runtime_complete"),
        );
    }

    for candidate in candidates {
        if candidate.join("manifest.json").is_file() {
            return load(&candidate);
        }
    }

    let sidecar = sidecar_path(resource_dir);
    if sidecar.is_file() {
        let output = state_store::data_dir()
            .join("cache")
            .join(format!("build-{}", crate::config::app_version()));
        let payload = build_with_sidecar(&sidecar, game_dir, &output, baseline)?;
        return Ok(payload);
    }

    Err(AppError::msg(
        "حزمة التعريب غير موجودة في التطبيق. أعد تثبيت الإصدار الكامل أو استخدم زر التحديث.",
    ))
}

pub fn sidecar_path(resource_dir: &Path) -> PathBuf {
    if let Ok(override_path) = std::env::var("WTOB_SIDECAR") {
        return PathBuf::from(override_path);
    }
    let bundled = resource_dir.join("resources").join("sidecar");
    if bundled.is_dir() {
        return bundled.join("wtob-build.exe");
    }
    resource_dir.join("sidecar").join("wtob-build.exe")
}

fn build_with_sidecar(
    sidecar: &Path,
    game_dir: &Path,
    output: &Path,
    baseline: Option<&Path>,
) -> AppResult<Payload> {
    if output.exists() {
        if load(output).is_ok() {
            return load(output);
        }
        fs::remove_dir_all(output)?;
    }
    fs::create_dir_all(output)?;

    let mut command = Command::new(sidecar);
    command
        .arg("--game")
        .arg(game_dir)
        .arg("--out")
        .arg(output);
    if let Some(baseline) = baseline {
        command.arg("--baseline").arg(baseline);
    }

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }

    let result = command
        .output()
        .map_err(|error| AppError::msg(format!("تعذر تشغيل أداة بناء التعريب: {error}")))?;
    if !result.status.success() {
        let stderr = String::from_utf8_lossy(&result.stderr);
        let tail: String = stderr.chars().rev().take(800).collect::<String>().chars().rev().collect();
        return Err(AppError::msg(format!(
            "فشل بناء حزمة التعريب من ملفات اللعبة. {tail}"
        )));
    }
    if !output.join("manifest.json").is_file() {
        return Err(AppError::msg(
            "أداة البناء انتهت دون إنتاج manifest.json.",
        ));
    }
    load(output)
}

fn load(dir: &Path) -> AppResult<Payload> {
    let text = fs::read_to_string(dir.join("manifest.json"))?;
    let manifest: PayloadManifest =
        serde_json::from_str(&text).map_err(|error| AppError::msg(format!("payload manifest: {error}")))?;

    for required in [INDEX_FILE, RESOURCES_FILE] {
        if !manifest
            .files
            .keys()
            .any(|key| normalize_key(key).map(|value| value == required).unwrap_or(false))
        {
            return Err(AppError::msg(format!(
                "حزمة التعريب لا تحتوي على {required}."
            )));
        }
    }

    let mut files = BTreeMap::new();
    for (key, hash) in &manifest.files {
        let normalized = normalize_key(key)?;
        if !crate::manifest::is_sha256(hash) {
            return Err(AppError::msg(format!("بصمة غير صالحة للملف {normalized}")));
        }
        let source = dir.join(normalized.strip_prefix("base/").unwrap_or(&normalized));
        if !source.is_file() {
            return Err(AppError::msg(format!(
                "ملف الحزمة مفقود: {}",
                source.display()
            )));
        }
        let actual = hash_file(&source)?;
        if &actual != hash {
            return Err(AppError::msg(format!(
                "بصمة ملف الحزمة غير مطابقة: {normalized}"
            )));
        }
        files.insert(normalized, hash.clone());
    }

    if files.contains_key(LOOSE_FILE) {
        let loose = dir.join("graphicsdriverwarningloc.json");
        if !loose.is_file() {
            return Err(AppError::msg("ملف التعريب المرئي مفقود من الحزمة."));
        }
    }

    Ok(Payload {
        dir: dir.to_path_buf(),
        version: manifest.version.unwrap_or_else(crate::config::app_version),
        files,
    })
}

pub fn normalize_key(key: &str) -> AppResult<String> {
    let formatted = key.replace('\\', "/");
    let trimmed = formatted.trim_start_matches("./");
    crate::manifest::validate_relative_name(trimmed)?;
    if trimmed.starts_with("base/") {
        Ok(trimmed.to_string())
    } else {
        Ok(format!("base/{trimmed}"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "wtob-payload-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn make_payload(dir: &Path, tamper: bool) -> String {
        let index = dir.join("chunk0.index");
        let resources = dir.join("chunk0.resources");
        fs::write(&index, b"payload-index").unwrap();
        fs::write(&resources, b"payload-resources").unwrap();
        let index_hash = hash_file(&index).unwrap();
        let resources_hash = hash_file(&resources).unwrap();
        let manifest = format!(
            r#"{{"schema":1,"version":"1.0.0","files":{{"chunk0.index":"{index_hash}","base/chunk0.resources":"{resources_hash}"}}}}"#
        );
        fs::write(dir.join("manifest.json"), &manifest).unwrap();
        if tamper {
            fs::write(&index, b"tampered").unwrap();
        }
        manifest
    }

    #[test]
    fn loads_and_verifies_payload() {
        let dir = temp_dir("load");
        make_payload(&dir, false);
        let payload = load(&dir).unwrap();
        assert_eq!(payload.version, "1.0.0");
        assert!(payload.hashes().contains_key(INDEX_FILE));
        assert_eq!(payload.source_for(INDEX_FILE), dir.join("chunk0.index"));
        fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn rejects_tampered_payload() {
        let dir = temp_dir("tamper");
        make_payload(&dir, true);
        assert!(load(&dir).is_err());
        fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn requires_both_chunk_files() {
        let dir = temp_dir("missing");
        fs::write(dir.join("chunk0.index"), b"x").unwrap();
        let hash = hash_file(&dir.join("chunk0.index")).unwrap();
        fs::write(
            dir.join("manifest.json"),
            format!(r#"{{"files":{{"chunk0.index":"{hash}"}}}}"#),
        )
        .unwrap();
        assert!(load(&dir).is_err());
        fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn normalizes_and_rejects_paths() {
        assert_eq!(normalize_key("chunk0.index").unwrap(), "base/chunk0.index");
        assert_eq!(normalize_key("base\\chunk0.index").unwrap(), "base/chunk0.index");
        assert!(normalize_key("../evil").is_err());
        assert!(normalize_key("C:/evil").is_err());
    }
}
