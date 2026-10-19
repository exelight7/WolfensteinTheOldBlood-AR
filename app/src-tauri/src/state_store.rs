use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::error::AppResult;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct InstalledState {
    pub schema: u32,
    pub version: String,
    pub installed_at: String,
    pub game_path: String,
    pub files: BTreeMap<String, String>,
}

pub fn now() -> String {
    time::OffsetDateTime::now_utc()
        .format(&time::format_description::well_known::Rfc3339)
        .unwrap_or_else(|_| "unknown".to_string())
}

pub fn data_dir() -> PathBuf {
    std::env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(std::env::temp_dir)
        .join("WolfensteinAR")
}

pub fn state_path() -> PathBuf {
    data_dir().join("state.json")
}

pub fn read() -> Option<InstalledState> {
    read_at(&state_path())
}

pub fn read_at(path: &Path) -> Option<InstalledState> {
    let text = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&text).ok()
}

pub fn write(game_dir: &Path, version: &str, files: BTreeMap<String, String>) -> AppResult<()> {
    let state = InstalledState {
        schema: 1,
        version: version.to_string(),
        installed_at: now(),
        game_path: game_dir.to_string_lossy().to_string(),
        files,
    };
    let dir = data_dir();
    std::fs::create_dir_all(&dir)?;
    let target = state_path();
    let temporary = dir.join(format!("state.json.tmp-{}", std::process::id()));
    std::fs::write(&temporary, serde_json::to_vec_pretty(&state)?)?;
    if target.exists() {
        std::fs::remove_file(&target)?;
    }
    std::fs::rename(&temporary, &target)?;
    Ok(())
}

pub fn clear() -> AppResult<()> {
    let path = state_path();
    if path.exists() {
        std::fs::remove_file(path)?;
    }
    Ok(())
}

pub fn version_for(path: &Path, game_dir: &Path) -> Option<String> {
    let state = read_at(path)?;
    if state.game_path.eq_ignore_ascii_case(&game_dir.to_string_lossy()) {
        Some(state.version)
    } else {
        None
    }
}

#[cfg(test)]
pub fn write_at(dir: &Path, game_dir: &Path, version: &str) -> AppResult<()> {
    std::fs::create_dir_all(dir)?;
    let state = InstalledState {
        schema: 1,
        version: version.to_string(),
        installed_at: now(),
        game_path: game_dir.to_string_lossy().to_string(),
        files: BTreeMap::new(),
    };
    std::fs::write(dir.join("state.json"), serde_json::to_vec_pretty(&state)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::error::AppError;

    fn temp_dir(tag: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!(
            "wtob-state-{tag}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn round_trips_state() {
        let dir = temp_dir("roundtrip");
        write_at(&dir, Path::new("C:/Games/WTOB"), "1.0.0").unwrap();
        let state = read_at(&dir.join("state.json")).expect("state");
        assert_eq!(state.version, "1.0.0");
        assert_eq!(state.game_path, "C:/Games/WTOB");
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn matches_game_path_case_insensitively() {
        let dir = temp_dir("match");
        write_at(&dir, Path::new("C:/Games/WTOB"), "1.0.0").unwrap();
        assert_eq!(
            version_for(&dir.join("state.json"), Path::new("c:/games/wtob")).as_deref(),
            Some("1.0.0")
        );
        assert!(version_for(&dir.join("state.json"), Path::new("D:/Other")).is_none());
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn rejects_corrupt_state() {
        let dir = temp_dir("corrupt");
        std::fs::write(dir.join("state.json"), b"not json").unwrap();
        assert!(read_at(&dir.join("state.json")).is_none());
        std::fs::remove_dir_all(dir).ok();
    }

    #[test]
    fn result_is_ok() {
        let result: AppResult<()> = Ok(());
        assert!(result.is_ok());
        let error = AppError::msg("x");
        assert_eq!(error.to_string(), "x");
    }
}
