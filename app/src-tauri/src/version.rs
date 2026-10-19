use semver::Version;

use crate::error::AppError;

pub fn parse(value: &str) -> Result<Version, AppError> {
    Version::parse(value.trim_start_matches('v'))
        .map_err(|error| AppError::msg(format!("invalid version '{value}': {error}")))
}

pub fn is_newer(candidate: &str, current: &str) -> Result<bool, AppError> {
    Ok(parse(candidate)? > parse(current)?)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn compares_versions() {
        assert!(is_newer("1.0.0", "0.9.0").unwrap());
        assert!(!is_newer("1.0.0", "1.0.0").unwrap());
        assert!(is_newer("1.0.1", "1.0.0").unwrap());
        assert!(is_newer("v2.0.0", "1.9.9").unwrap());
    }

    #[test]
    fn rejects_garbage() {
        assert!(parse("latest").is_err());
        assert!(parse("1.0").is_err());
    }

}
