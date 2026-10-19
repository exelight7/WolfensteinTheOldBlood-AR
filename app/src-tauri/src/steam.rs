use std::path::{Path, PathBuf};

pub const INSTALL_DIR_NAME: &str = "Wolfenstein The Old Blood";

pub fn detect_game(app_id: u32, executable: &str, install_dir: &str) -> Option<PathBuf> {
    for root in steam_roots() {
        for library in libraries(&root) {
            if let Some(game) = game_in_library(&library, app_id, executable) {
                return Some(game);
            }
            let fallback = library.join("steamapps").join("common").join(install_dir);
            if fallback.join(executable).is_file() {
                return Some(fallback);
            }
        }
    }
    None
}

fn game_in_library(library: &Path, app_id: u32, executable: &str) -> Option<PathBuf> {
    let acf = library
        .join("steamapps")
        .join(format!("appmanifest_{app_id}.acf"));
    let text = std::fs::read_to_string(&acf).ok()?;
    let install_dir = parse_installdir(&text)?;
    let candidate = library.join("steamapps").join("common").join(install_dir);
    candidate.join(executable).is_file().then_some(candidate)
}

fn libraries(root: &Path) -> Vec<PathBuf> {
    let mut result = vec![root.to_path_buf()];
    for candidate in [
        root.join("steamapps").join("libraryfolders.vdf"),
        root.join("config").join("libraryfolders.vdf"),
    ] {
        let Ok(text) = std::fs::read_to_string(&candidate) else {
            continue;
        };
        for path in parse_library_paths(&text) {
            let path = PathBuf::from(path);
            if path.is_dir() && !result.iter().any(|existing| same_path(existing, &path)) {
                result.push(path);
            }
        }
    }
    result
}

fn same_path(a: &Path, b: &Path) -> bool {
    a.to_string_lossy().eq_ignore_ascii_case(&b.to_string_lossy())
}

fn steam_roots() -> Vec<PathBuf> {
    let mut roots = Vec::new();

    if let Ok(value) = std::env::var("WTOB_STEAM_DIR") {
        if !value.trim().is_empty() {
            roots.push(PathBuf::from(value));
        }
    }

    #[cfg(windows)]
    {
        use winreg::enums::{HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE};
        use winreg::RegKey;

        let candidates = [
            (
                RegKey::predef(HKEY_CURRENT_USER),
                "Software\\Valve\\Steam",
                "SteamPath",
            ),
            (
                RegKey::predef(HKEY_LOCAL_MACHINE),
                "SOFTWARE\\WOW6432Node\\Valve\\Steam",
                "InstallPath",
            ),
            (
                RegKey::predef(HKEY_LOCAL_MACHINE),
                "SOFTWARE\\Valve\\Steam",
                "InstallPath",
            ),
        ];

        for (root, key_path, value_name) in candidates {
            if let Ok(key) = root.open_subkey(key_path) {
                if let Ok(value) = key.get_value::<String, _>(value_name) {
                    let path = PathBuf::from(value);
                    if path.is_dir() && !roots.iter().any(|existing| same_path(existing, &path)) {
                        roots.push(path);
                    }
                }
            }
        }
    }

    roots
}

pub fn parse_library_paths(text: &str) -> Vec<String> {
    let tokens = quoted_strings(text);
    let mut paths = Vec::new();
    for window in tokens.windows(2) {
        let key = &window[0];
        let value = &window[1];
        let is_path_key = key.eq_ignore_ascii_case("path");
        let is_numeric_key = !key.is_empty() && key.chars().all(|c| c.is_ascii_digit());
        if (is_path_key || is_numeric_key) && looks_like_path(value) {
            paths.push(value.clone());
        }
    }
    paths
}

pub fn parse_installdir(text: &str) -> Option<String> {
    let tokens = quoted_strings(text);
    tokens
        .windows(2)
        .find(|window| window[0].eq_ignore_ascii_case("installdir"))
        .map(|window| window[1].clone())
}

fn looks_like_path(value: &str) -> bool {
    value.contains(":\\") || value.starts_with('/') || value.contains(":/")
}

fn quoted_strings(text: &str) -> Vec<String> {
    let mut values = Vec::new();
    let mut chars = text.chars().peekable();
    while let Some(character) = chars.next() {
        if character != '"' {
            continue;
        }
        let mut value = String::new();
        while let Some(character) = chars.next() {
            match character {
                '"' => break,
                '\\' => {
                    if let Some(escaped) = chars.next() {
                        match escaped {
                            'n' => value.push('\n'),
                            't' => value.push('\t'),
                            other => value.push(other),
                        }
                    }
                }
                other => value.push(other),
            }
        }
        values.push(value);
    }
    values
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_modern_library_folders() {
        let text = r#"
        "libraryfolders"
        {
            "0"
            {
                "path"        "C:\\Program Files (x86)\\Steam"
                "label"       ""
                "contentid"   "123"
            }
            "1"
            {
                "path"        "D:\\SteamLibrary"
                "apps"
                {
                    "350080"  "12345"
                }
            }
        }
        "#;
        let paths = parse_library_paths(text);
        assert_eq!(paths.len(), 2);
        assert_eq!(paths[0], r"C:\Program Files (x86)\Steam");
        assert_eq!(paths[1], r"D:\SteamLibrary");
    }

    #[test]
    fn parses_legacy_numeric_entries() {
        let text = r#"
        "LibraryFolders"
        {
            "TimeNextStatsReport" "123"
            "1" "E:\\Games\\Steam"
            "2" "F:/SteamLibrary"
        }
        "#;
        let paths = parse_library_paths(text);
        assert_eq!(paths, vec![r"E:\Games\Steam", "F:/SteamLibrary"]);
    }

    #[test]
    fn parses_installdir() {
        let text = r#"
        "AppState"
        {
            "appid" "350080"
            "name" "Wolfenstein: The Old Blood"
            "installdir" "Wolfenstein The Old Blood"
        }
        "#;
        assert_eq!(
            parse_installdir(text).as_deref(),
            Some("Wolfenstein The Old Blood")
        );
    }

    #[test]
    fn ignores_non_path_values() {
        let text = r#""path" "not-a-path" "path" "G:\\Steam""#;
        assert_eq!(parse_library_paths(text), vec![r"G:\Steam"]);
    }
}
