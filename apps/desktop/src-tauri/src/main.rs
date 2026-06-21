mod bootstrap;

use bootstrap::{get_api_bootstrap, ApiBootstrapState};

fn main() {
    let base_url = std::env::var("MIB_API_BASE_URL").unwrap_or_else(|_| "http://127.0.0.1:8910".to_string());
    let token = std::env::var("MIB_API_TOKEN").unwrap_or_else(|_| "test-token".to_string());

    tauri::Builder::default()
        .manage(ApiBootstrapState::new(base_url, token))
        .invoke_handler(tauri::generate_handler![get_api_bootstrap])
        .run(tauri::generate_context!())
        .expect("failed to run MIB Studio desktop shell");
}
