use serde::Deserialize;
use std::collections::BTreeMap;
use std::sync::OnceLock;

use crate::error::AppError;

#[derive(Debug, Deserialize)]
pub struct SupportedConfig {
    pub schema_version: u32,
    pub app_version: String,
    pub supported_versions: Vec<SupportedVersion>,
}

#[derive(Debug, Clone, Deserialize)]
#[allow(dead_code)]
pub struct SupportedVersion {
    pub id: String,
    pub label: String,
    pub store: String,
    pub steam_app_id: u32,
    pub game_build: String,
    pub platform: String,
    pub executable: String,
    pub executable_sha256: String,
    pub vanilla: BTreeMap<String, String>,
    pub localized: BTreeMap<String, String>,
    #[serde(default)]
    pub also_accepted_states: Vec<BTreeMap<String, String>>,
}

impl SupportedVersion {
    pub fn vanilla_hash(&self, relative: &str) -> Option<&str> {
        self.vanilla.get(relative).map(String::as_str)
    }

    pub fn localized_hash(&self, relative: &str) -> Option<&str> {
        self.localized.get(relative).map(String::as_str)
    }

}

static CONFIG: OnceLock<SupportedConfig> = OnceLock::new();

pub fn load() -> Result<&'static SupportedConfig, AppError> {
    if let Some(config) = CONFIG.get() {
        return Ok(config);
    }
    let parsed: SupportedConfig =
        serde_json::from_str(include_str!("../../../config/supported_versions.json"))
            .map_err(|error| AppError::msg(format!("config/supported_versions.json: {error}")))?;
    if parsed.schema_version != 2 {
        return Err(AppError::msg(format!(
            "unsupported config schema {}",
            parsed.schema_version
        )));
    }
    if parsed.supported_versions.is_empty() {
        return Err(AppError::msg("config has no supported versions"));
    }
    let _ = CONFIG.set(parsed);
    Ok(CONFIG.get().expect("config initialized"))
}

pub fn primary() -> Result<&'static SupportedVersion, AppError> {
    load()?
        .supported_versions
        .first()
        .ok_or_else(|| AppError::msg("config has no supported versions"))
}

pub fn app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_config_is_valid() {
        let config = load().expect("config parses");
        assert_eq!(config.schema_version, 2);
        assert!(!config.supported_versions.is_empty());
        let version = &config.supported_versions[0];
        assert_eq!(version.steam_app_id, 350080);
        assert_eq!(version.vanilla.len(), 3);
        assert_eq!(version.localized.len(), 3);
        assert_eq!(version.vanilla["base/chunk0.index"].len(), 64);
    }

    #[test]
    fn accepted_states_are_well_formed() {
        let version = &load().unwrap().supported_versions[0];
        let state = version.also_accepted_states.first().expect("accepted state");
        assert!(state
            .get("label")
            .map(|label| label.contains("runtime_complete_reviewed"))
            .unwrap_or(false));
        assert_eq!(state["base/chunk0.index"].len(), 64);
    }
}
