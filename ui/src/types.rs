use iced::{Color, widget::image::Handle};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::styles::hex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PollerStatus {
    pub display_name: String,
    pub active: bool,
    pub filedir: Option<String>,
}

pub type PollerStatePayload = HashMap<String, PollerStatus>;

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
    Sse(SseMessage),
}

#[derive(Debug, Clone)]
pub enum ViewMessage {
    Switch(View),
    TabPressed { shift: bool },
    Animate,
    TogglePollerDropdown,
}

#[derive(Debug, Clone)]
pub enum RpcMessage {
    TitleChanged(String),
    UrlChanged(String),
    ImageUrlChanged(String),
    ToggleRewatching(bool),
    OpenUrlClicked,
    Undo,
    Redo,
}

#[derive(Debug, Clone)]
pub enum SearchMessage {
    QueryChanged(String),
    Perform,
    Finished(Result<Vec<SearchResult>, String>),
    ResultSelected(SearchResult),
    ProviderSelected(SearchProvider),
    MoveSelection(isize),
    SelectHovered,
    FocusInput,
}

#[derive(Debug, Clone)]
pub enum IoMessage {
    PollerSelected(String),
    RpcLoaded(Result<String, String>),
    ReconnectClicked,
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

#[derive(Debug, Clone)]
pub enum SseMessage {
    Connected,
    Data(String),
    Disconnected,
    Tick,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
#[repr(u8)]
pub enum SearchProvider {
    #[default]
    MyAnimeList = 0,
    AniList = 1,
}

impl SearchProvider {
    #[allow(unused)]
    pub const ALL: &'static [SearchProvider] =
        &[SearchProvider::MyAnimeList, SearchProvider::AniList];

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::MyAnimeList => "myanimelist",
            Self::AniList => "anilist",
        }
    }

    pub fn display_name(&self) -> &'static str {
        match self {
            Self::MyAnimeList => "MyAnimeList",
            Self::AniList => "AniList",
        }
    }

    pub fn accent_colour(&self) -> Color {
        match self {
            Self::MyAnimeList => hex(0x2E51A2),
            Self::AniList => hex(0x0B1622),
        }
    }

    pub fn from_url(url: &str) -> Self {
        if url.contains("anilist.co") {
            Self::AniList
        } else {
            Self::MyAnimeList
        }
    }
}

impl std::fmt::Display for SearchProvider {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}
