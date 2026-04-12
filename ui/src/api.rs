use crate::constants::API_BASE_URL;
use crate::types::{Poller, SearchResult};
use iced::widget::image::Handle;
use std::collections::HashMap;

pub async fn fetch_pollers() -> Result<HashMap<String, Poller>, String> {
    reqwest::get(&format!("{}/pollers", API_BASE_URL))
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())
}

pub async fn fetch_img(url: String) -> Option<Handle> {
    reqwest::get(&url)
        .await
        .ok()?
        .bytes()
        .await
        .ok()
        .map(Handle::from_bytes)
}

// FIXME: allow choosing providers
pub async fn perform_search(query: String) -> Result<Vec<SearchResult>, String> {
    let url = format!("{}/search?q={}&provider=myanimelist", API_BASE_URL, query);
    reqwest::get(&url)
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())
}
