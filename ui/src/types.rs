use iced::widget::image::Handle;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Poller {
    pub display_name: String,
    pub active: bool,
    pub filedir: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: String,
    pub title: String,
    pub url: String,
    pub image_url: String,
}

#[derive(Default, Clone, Copy, Debug, PartialEq, Eq)]
pub enum View {
    #[default]
    Config,
    Search,
}

#[derive(Debug, Clone)]
pub enum Message {
    TitleChanged(String),
    UrlChanged(String),
    ImageUrlChanged(String),
    ToggleRewatching(bool),
    SwitchView(View),
    SearchQueryChanged(String),
    PollerSelected(String),
    PollersFetched(Result<HashMap<String, Poller>, String>),
    RpcLoaded(Result<String, String>),
    SearchFinished(Result<Vec<SearchResult>, String>),
    ResultSelected(SearchResult),
    SaveClicked,
    PerformSearch,
    ImageLoaded(String, Option<Handle>),
    ToggleWindow,
    RefreshClicked,
    Tick,
    Quit,
}
