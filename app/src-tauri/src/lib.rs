mod backup;
mod commands;
mod config;
mod error;
mod game;
mod installer;
mod manifest;
mod payload;
mod state_store;
mod steam;
mod types;
mod version;

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            commands::detect_game,
            commands::validate_game,
            commands::get_status,
            commands::install,
            commands::repair,
            commands::restore,
            commands::verify_backup,
            commands::check_updates,
            commands::app_info,
            commands::open_url,
        ])
        .run(tauri::generate_context!())
        .expect("error while running the application");
}
