#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("{0}")]
    Message(String),
    #[error("تعذر تنفيذ عملية على الملفات: {0}")]
    Io(#[from] std::io::Error),
    #[error("ملف JSON غير صالح: {0}")]
    Json(#[from] serde_json::Error),
}

impl AppError {
    pub fn msg(message: impl Into<String>) -> Self {
        Self::Message(message.into())
    }
}

pub type AppResult<T> = Result<T, AppError>;
