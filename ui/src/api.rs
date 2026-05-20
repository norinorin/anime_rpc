use crate::constants::API_BASE_URL;
use crate::types::SearchResult;
use iced::widget::image::Handle;

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
