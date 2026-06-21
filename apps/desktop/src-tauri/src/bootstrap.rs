use serde::Serialize;
use std::sync::Arc;

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ApiBootstrap {
    pub base_url: String,
    pub token: String,
}

#[derive(Clone, Debug)]
pub struct ApiBootstrapState {
    value: Arc<ApiBootstrap>,
}

impl ApiBootstrapState {
    pub fn new(base_url: String, token: String) -> Self {
        Self {
            value: Arc::new(ApiBootstrap { base_url, token }),
        }
    }

    pub fn get(&self) -> ApiBootstrap {
        (*self.value).clone()
    }
}

#[tauri::command]
pub fn get_api_bootstrap(state: tauri::State<'_, ApiBootstrapState>) -> ApiBootstrap {
    state.get()
}
