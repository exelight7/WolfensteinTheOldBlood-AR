use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

use crate::error::AppError;
use crate::version;

pub const REPO: &str = "https://github.com/exelight7/WolfensteinTheOldBlood-AR";
pub const LATEST_MANIFEST_URL: &str =
    "https://github.com/exelight7/WolfensteinTheOldBlood-AR/releases/latest/download/release-manifest.json";
pub const CHANGELOG_URL: &str =
    "https://github.com/exelight7/WolfensteinTheOldBlood-AR/blob/main/CHANGELOG.md";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReleaseManifest {
    pub version: String,
    pub channel: String,
    #[serde(default)]
    pub minimum_app_version: Option<String>,
    #[serde(default)]
    pub game_version: Option<String>,
    #[serde(default)]
    pub release_date: Option<String>,
    #[serde(default)]
    pub files: Vec<ManifestFile>,
    #[serde(default)]
    pub changelog_url: Option<String>,
    #[serde(default)]
    pub download_url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ManifestFile {
    pub name: String,
    #[serde(default)]
    pub kind: Option<String>,
    #[serde(default)]
    pub size: Option<u64>,
    pub sha256: String,
    #[serde(default)]
    pub download_url: Option<String>,
}

impl ReleaseManifest {
    pub fn validate(&self) -> Result<(), AppError> {
        version::parse(&self.version)?;
        if self.channel != "stable" {
            return Err(AppError::msg(format!(
                "unsupported channel '{}' (only stable is accepted)",
                self.channel
            )));
        }
        if let Some(minimum) = &self.minimum_app_version {
            version::parse(minimum)?;
        }
        if self.files.is_empty() {
            return Err(AppError::msg("manifest has no files"));
        }
        let mut seen = BTreeMap::new();
        for file in &self.files {
            validate_relative_name(&file.name)?;
            if !is_sha256(&file.sha256) {
                return Err(AppError::msg(format!(
                    "invalid sha256 for '{}'",
                    file.name
                )));
            }
            if seen.insert(file.name.clone(), ()).is_some() {
                return Err(AppError::msg(format!("duplicate file '{}'", file.name)));
            }
        }
        for url in [
            self.changelog_url.as_deref(),
            self.download_url.as_deref(),
            self.files.iter().find_map(|f| f.download_url.as_deref()),
        ]
        .into_iter()
        .flatten()
        {
            if !url.starts_with("https://") {
                return Err(AppError::msg(format!("insecure URL '{url}'")));
            }
        }
        Ok(())
    }

    #[allow(dead_code)]
    pub fn file(&self, relative: &str) -> Option<&ManifestFile> {
        self.files.iter().find(|file| file.name == relative)
    }

    pub fn changelog(&self) -> &str {
        self.changelog_url.as_deref().unwrap_or(CHANGELOG_URL)
    }
}

pub fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

pub fn validate_relative_name(name: &str) -> Result<(), AppError> {
    let normalized = name.replace('\\', "/");
    if normalized.is_empty()
        || normalized.starts_with('/')
        || normalized.contains(':')
        || normalized.split('/').any(|part| part == ".." || part.is_empty())
    {
        return Err(AppError::msg(format!("unsafe manifest file name '{name}'")));
    }
    Ok(())
}

pub fn parse(text: &str) -> Result<ReleaseManifest, AppError> {
    let manifest: ReleaseManifest =
        serde_json::from_str(text).map_err(|error| AppError::msg(format!("manifest JSON: {error}")))?;
    manifest.validate()?;
    Ok(manifest)
}

pub fn fetch_latest() -> Result<ReleaseManifest, AppError> {
    let agent = ureq::AgentBuilder::new()
        .timeout_connect(std::time::Duration::from_secs(10))
        .timeout_read(std::time::Duration::from_secs(20))
        .user_agent(concat!("wtob-ar-manager/", env!("CARGO_PKG_VERSION")))
        .build();
    let response = agent
        .get(LATEST_MANIFEST_URL)
        .call()
        .map_err(|error| AppError::msg(format!("تعذر الوصول إلى خادم التحديثات: {error}")))?;
    let body = response
        .into_string()
        .map_err(|error| AppError::msg(format!("تعذر قراءة استجابة التحديثات: {error}")))?;
    parse(&body)
}

pub fn release_url(version: &str) -> String {
    format!("{REPO}/releases/tag/v{}", version.trim_start_matches('v'))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn manifest_json(sha: &str) -> String {
        format!(
            r#"{{
              "version": "1.0.0",
              "channel": "stable",
              "minimumAppVersion": "1.0.0",
              "gameVersion": "616161",
              "releaseDate": "2026-10-19",
              "files": [
                {{"name": "base/chunk0.index", "kind": "chunk", "size": 10, "sha256": "{sha}"}},
                {{"name": "base/chunk0.resources", "kind": "chunk", "size": 20, "sha256": "{sha}"}}
              ],
              "changelogUrl": "https://github.com/exelight7/WolfensteinTheOldBlood-AR/blob/main/CHANGELOG.md",
              "downloadUrl": "https://github.com/exelight7/WolfensteinTheOldBlood-AR/releases/download/v1.0.0/localization.zip"
            }}"#
        )
    }

    const SHA: &str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    #[test]
    fn parses_valid_manifest() {
        let manifest = parse(&manifest_json(SHA)).expect("valid");
        assert_eq!(manifest.version, "1.0.0");
        assert_eq!(manifest.files.len(), 2);
        assert!(manifest.file("base/chunk0.index").is_some());
        assert!(manifest.changelog().contains("CHANGELOG"));
    }

    #[test]
    fn rejects_unsafe_names() {
        for name in ["../chunk0.index", "/abs", "C:\\\\x", "base//x", ""] {
            assert!(validate_relative_name(name).is_err(), "{name}");
        }
        assert!(validate_relative_name("base/chunk0.index").is_ok());
    }

    #[test]
    fn rejects_bad_hashes_and_channels() {
        let mut manifest = parse(&manifest_json(SHA)).unwrap();
        manifest.channel = "beta".into();
        assert!(manifest.validate().is_err());

        let bad = manifest_json("XYZ");
        assert!(parse(&bad).is_err());

        let uppercase = manifest_json(&SHA.to_uppercase());
        assert!(parse(&uppercase).is_err());
    }

    #[test]
    fn rejects_insecure_urls() {
        let json = manifest_json(SHA).replace("https://github.com", "http://github.com");
        assert!(parse(&json).is_err());
    }

    #[test]
    fn release_url_normalizes_prefix() {
        assert_eq!(
            release_url("v1.0.0"),
            "https://github.com/exelight7/WolfensteinTheOldBlood-AR/releases/tag/v1.0.0"
        );
    }
}
