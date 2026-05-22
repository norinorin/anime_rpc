use crate::constants::API_BASE_URL;
use crate::types::{SearchProvider, SearchResult};
use iced::widget::image::Handle;

pub async fn fetch_img(url: String) -> Option<Handle> {
    let bytes = reqwest::get(&url)
        .await
        .ok()?
        .error_for_status()
        .ok()?
        .bytes()
        .await
        .ok()?;
    image::load_from_memory(&bytes).ok()?;
    Some(Handle::from_bytes(bytes))
}

// FIXME: allow choosing providers
pub async fn perform_search(
    query: String,
    provider: SearchProvider,
) -> Result<Vec<SearchResult>, String> {
    let url = format!("{}/search?q={}&provider={}", API_BASE_URL, query, provider);
    reqwest::get(&url)
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())
}
