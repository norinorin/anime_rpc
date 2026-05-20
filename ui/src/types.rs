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
    View(ViewMessage),
    Rpc(RpcMessage),
    Search(SearchMessage),
    Io(IoMessage),
}

#[derive(Debug, Clone)]
pub enum ViewMessage {
    ToggleWindow,
    Switch(View),
    TabPressed { shift: bool },
    Tick,
    TogglePollerDropdown,
}

#[derive(Debug, Clone)]
pub enum RpcMessage {
    TitleChanged(String),
    UrlChanged(String),
    ImageUrlChanged(String),
    ToggleRewatching(bool),
    OpenUrlClicked,
}

#[derive(Debug, Clone)]
pub enum SearchMessage {
    QueryChanged(String),
    Perform,
    Finished(Result<Vec<SearchResult>, String>),
    ResultSelected(SearchResult),
}

#[derive(Debug, Clone)]
pub enum IoMessage {
    PollersFetched(Result<HashMap<String, Poller>, String>),
    PollerSelected(String),
    RpcLoaded(Result<String, String>),
    RefreshClicked,
    SaveClicked,
    SaveCompleted(Result<(), String>),
    ResetSaveStatus,
    ImageLoaded(String, Option<Handle>),
}

#[derive(Default, Clone, Copy, Debug, PartialEq, Eq)]
pub enum SaveStatus {
    #[default]
    Idle,
    Saved,
    Failed,
}

#[derive(Default, Clone, Copy, Debug, PartialEq, Eq)]
pub enum DaemonStatus {
    #[default]
    Checking,
    Disconnected,
    Connected,
}
