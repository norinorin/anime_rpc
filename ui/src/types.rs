use iced::{
    Color, color,
    widget::{image::Handle, svg},
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::constants::colours;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PollerStatus {
    pub display_name: String,
    pub active: bool,
    pub filedir: Option<String>,
}

pub type PollerStatePayload = HashMap<String, PollerStatus>;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum MediaFormat {
    Tv,
    Movie,
    Ova,
    Ona,
    Special,
}

impl MediaFormat {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Tv => "TV",
            Self::Movie => "Movie",
            Self::Ova => "OVA",
            Self::Ona => "ONA",
            Self::Special => "Special",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AiringStatus {
    Finished,
    Releasing,
    Tba,
}

impl AiringStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Finished => "Finished",
            Self::Releasing => "Airing",
            Self::Tba => "TBA",
        }
    }

    pub fn accent_colour(&self) -> Color {
        match self {
            AiringStatus::Finished => colours::GREEN,
            AiringStatus::Releasing => colours::SELECTION,
            AiringStatus::Tba => colours::RED,
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct SearchResult {
    #[allow(unused)]
    pub id: String,
    pub title: String,
    pub url: String,
    pub image_url: String,
    pub year: Option<i32>,
    pub media_format: Option<MediaFormat>,
    pub status: Option<AiringStatus>,
    pub score: Option<u16>,
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
    Undo,
    Redo,
    GotoSearchBar,
    EscPressed,
    TabPressed { shift: bool },
    OpenUrlClicked(String),
}

#[derive(Debug, Clone)]
pub enum ViewMessage {
    Switch(View),
    Animate,
    TogglePollerDropdown,
}

#[derive(Debug, Clone)]
pub enum RpcMessage {
    TitleChanged(String),
    UrlChanged(String),
    ImageUrlChanged(String),
    ToggleRewatching(bool),
    Undo,
    Redo,
}

#[derive(Debug, Clone)]
pub enum SearchMessage {
    QueryChanged(String),
    Perform,
    Finished(SearchProvider, Result<Vec<SearchResult>, String>),
    ResultSelected(SearchResult),
    ProviderSelected(SearchProvider),
    MoveSelection(isize),
    SelectHovered,
    FocusInput,
    Undo,
    Redo,
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
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

    pub fn logo(&self) -> svg::Handle {
        match self {
            Self::MyAnimeList => {
                svg::Handle::from_memory(include_bytes!("../assets/myanimelist.svg"))
            }
            Self::AniList => svg::Handle::from_memory(include_bytes!("../assets/anilist.svg")),
        }
    }

    #[allow(unused)]
    pub fn display_name(&self) -> &'static str {
        match self {
            Self::MyAnimeList => "MyAnimeList",
            Self::AniList => "AniList",
        }
    }

    pub fn accent_colour(&self) -> Color {
        match self {
            Self::MyAnimeList => color!(0x2E51A2),
            Self::AniList => color!(0x0B1622),
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
