use crate::api::{fetch_img, perform_search};
use crate::components::CachedImage;
use crate::constants::image_cache_size;
use crate::history::History;
use crate::types::{
    IoMessage, Message, PollerStatePayload, RpcMessage, SaveStatus, SearchMessage, SearchProvider,
    SearchResult, SseMessage, View, ViewMessage,
};
use crate::utils::{clean_dir_name, load_rpc, save_rpc};
use crate::{sse, views};
use iced::Animation;
use iced::widget::container;
use iced::{Element, Length, Task};
use lru::LruCache;
use std::collections::HashMap;
use std::time::Instant;

pub struct AnimeRpc {
    pub view: ViewState,
    pub rpc: RpcState,
    pub search: SearchState,
    pub sse: SseState,
    pub now: Instant,
}

pub struct ViewState {
    pub current: View,
    pub poller_dropdown_open: bool,
    pub poller_dropdown_anim: Animation<bool>,
    pub rewatching_anim: Animation<bool>,
    pub provider_anim: Animation<bool>,
    pub save_status: SaveStatus,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct RpcFormData {
    pub title: String,
    pub url: String,
    pub image_url: String,
    pub rewatching: bool,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct SearchFormData {
    pub query: String,
    pub selected_provider: SearchProvider,
}

pub struct RpcState {
    pub form: History<RpcFormData>,
    pub pollers: PollerStatePayload,
    pub active_id: Option<String>,
    pub active_filedir: Option<String>,
    pub title_placeholder: String,
    pub raw_content: String,
    pub image_cache: LruCache<String, CachedImage>,
}

pub struct SearchState {
    pub form: History<SearchFormData>,
    pub results: HashMap<SearchProvider, Vec<SearchResult>>,
    pub hovered_index: Option<usize>,
}

pub enum SseState {
    Connecting { attempt: u32 },
    Connected,
    WaitingToReconnect { seconds_left: u64, attempt: u32 },
}

impl AnimeRpc {
    pub fn init() -> (Self, Task<Message>) {
        (
            Self {
                view: ViewState {
                    current: View::Config,
                    poller_dropdown_open: false,
                    poller_dropdown_anim: Animation::new(false)
                        .duration(std::time::Duration::from_millis(200))
                        .easing(iced::animation::Easing::EaseInOutCubic),
                    rewatching_anim: Animation::new(false)
                        .duration(std::time::Duration::from_millis(150))
                        .easing(iced::animation::Easing::EaseInOutCubic),
                    provider_anim: Animation::new(false)
                        .duration(std::time::Duration::from_millis(150))
                        .easing(iced::animation::Easing::EaseInOutCubic),
                    save_status: SaveStatus::default(),
                },
                rpc: RpcState {
                    pollers: HashMap::new(),
                    active_id: None,
                    active_filedir: None,
                    title_placeholder: String::new(),
                    raw_content: String::new(),
                    image_cache: LruCache::new(image_cache_size()),
                    form: History::new(RpcFormData::default()),
                },
                search: SearchState {
                    results: HashMap::new(),
                    hovered_index: None,
                    form: History::new(SearchFormData::default()),
                },
                sse: SseState::Connecting { attempt: 1 },
                now: Instant::now(),
            },
            Task::none(),
        )
    }

    fn clear_config_form(&mut self) {
        self.rpc.form.modify(|form| *form = RpcFormData::default());
        self.rpc.active_id = None;
        self.rpc.active_filedir = None;
        self.rpc.title_placeholder.clear();
    }

    fn is_animating(&self) -> bool {
        let mut is_animating = self
            .rpc
            .image_cache
            .iter()
            .any(|(_, img)| img.is_animating());

        is_animating |= self.view.poller_dropdown_anim.is_animating(self.now);
        is_animating |= self.view.rewatching_anim.is_animating(self.now);
        is_animating |= self.view.provider_anim.is_animating(self.now);

        is_animating
    }

    pub fn subscription(&self) -> iced::Subscription<Message> {
        let animation = if self.is_animating() {
            iced::window::frames().map(|_| Message::View(ViewMessage::Animate))
        } else {
            iced::Subscription::none()
        };

        let keyboard_sub = iced::keyboard::listen().filter_map(move |event| match event {
            iced::keyboard::Event::KeyPressed { key, modifiers, .. } => {
                use iced::keyboard::key::{Key, Named};

                match key.as_ref() {
                    Key::Named(Named::Tab) => Some(Message::View(ViewMessage::TabPressed {
                        shift: modifiers.shift(),
                    })),
                    Key::Character(c) if c.eq_ignore_ascii_case("z") && modifiers.command() => {
                        if modifiers.shift() {
                            Some(Message::Redo)
                        } else {
                            Some(Message::Undo)
                        }
                    }
                    Key::Character(c) if c.eq_ignore_ascii_case("s") && modifiers.command() => {
                        Some(Message::Io(IoMessage::SaveClicked))
                    }
                    Key::Character(c) if c.eq_ignore_ascii_case("l") && modifiers.command() => {
                        Some(Message::GotoSearchBar)
                    }
                    Key::Character("/") => Some(Message::Search(SearchMessage::FocusInput)),
                    Key::Named(Named::ArrowDown) => {
                        Some(Message::Search(SearchMessage::MoveSelection(1)))
                    }
                    Key::Named(Named::ArrowUp) => {
                        Some(Message::Search(SearchMessage::MoveSelection(-1)))
                    }
                    Key::Named(Named::Enter) => Some(Message::Search(SearchMessage::SelectHovered)),
                    Key::Named(Named::Escape) => Some(Message::EscPressed),
                    _ => None,
                }
            }
            _ => None,
        });

        let sse = match self.sse {
            SseState::Connecting { .. } | SseState::Connected => sse::listen().map(Message::Sse),
            SseState::WaitingToReconnect { .. } => {
                iced::time::every(std::time::Duration::from_secs(1))
                    .map(|_| Message::Sse(SseMessage::Tick))
            }
        };

        iced::Subscription::batch([animation, keyboard_sub, sse])
    }

    pub fn update(&mut self, message: Message, now: Instant) -> Task<Message> {
        self.now = now;

        let task = match (message, &self.view.current) {
            (Message::View(msg), _) => self.handle_view(msg, now),
            (Message::Rpc(msg), _) => self.handle_rpc(msg, now),
            (Message::Search(msg), _) => self.handle_search(msg, now),
            (Message::Io(msg), _) => self.handle_io(msg, now),
            (Message::Sse(msg), _) => self.handle_sse(msg, now),
            (Message::Undo, _) => match self.view.current {
                View::Search => self.handle_search(SearchMessage::Undo, now),
                View::Config => self.handle_rpc(RpcMessage::Undo, now),
            },
            (Message::Redo, View::Config) => self.handle_rpc(RpcMessage::Redo, now),
            (Message::Redo, View::Search) => self.handle_search(SearchMessage::Redo, now),
            (Message::GotoSearchBar, View::Config) => {
                self.handle_view(ViewMessage::Switch(View::Search), now)
            }
            (Message::GotoSearchBar, View::Search) => {
                self.handle_search(SearchMessage::FocusInput, now)
            }
            (Message::EscPressed, View::Search) => {
                if self.search.hovered_index.is_some() {
                    self.search.hovered_index = None;
                    Task::none()
                } else {
                    self.handle_view(ViewMessage::Switch(View::Config), now)
                }
            }
            (Message::EscPressed, View::Config) => Task::none(),
        };

        // animation sync
        self.view
            .provider_anim
            .go_mut(self.search.form.selected_provider as u8 != 0, now);
        self.view
            .rewatching_anim
            .go_mut(self.rpc.form.rewatching, now);
        self.view
            .poller_dropdown_anim
            .go_mut(self.view.poller_dropdown_open, now);

        task
    }

    fn handle_view(&mut self, message: ViewMessage, _now: Instant) -> Task<Message> {
        match message {
            ViewMessage::Switch(v) => {
                if v == View::Search
                    && let Some(id) = &self.rpc.active_id
                    && let Some(p) = self.rpc.pollers.get(id)
                    && let Some(dir) = &p.filedir
                {
                    self.search
                        .form
                        .modify(|form| form.query = clean_dir_name(dir));
                }
                self.view.current = v;
                Task::none()
            }
            ViewMessage::Animate => Task::none(),
            ViewMessage::TabPressed { shift } => {
                if shift {
                    iced::widget::operation::focus_previous()
                } else {
                    iced::widget::operation::focus_next()
                }
            }
            ViewMessage::TogglePollerDropdown => {
                self.view.poller_dropdown_open = !self.view.poller_dropdown_open;
                Task::none()
            }
        }
    }

    fn handle_rpc(&mut self, message: RpcMessage, now: Instant) -> Task<Message> {
        if self.view.current != View::Config
            && let RpcMessage::Undo | RpcMessage::Redo = message
        {
            return Task::none();
        }

        match message {
            RpcMessage::TitleChanged(val) => {
                self.rpc.form.modify(|form| form.title = val);
                Task::none()
            }
            RpcMessage::UrlChanged(val) => {
                self.rpc.form.modify(|form| form.url = val);
                Task::none()
            }
            RpcMessage::ImageUrlChanged(val) => {
                self.rpc.form.modify(|form| form.image_url = val.clone());
                if val.is_empty() || self.rpc.image_cache.contains(&val) {
                    return Task::none();
                }
                self.rpc
                    .image_cache
                    .put(val.clone(), CachedImage::new_pending(now));
                Task::perform(fetch_img(val.clone()), move |handle| {
                    Message::Io(IoMessage::ImageLoaded(val, handle))
                })
            }
            RpcMessage::ToggleRewatching(b) => {
                self.rpc.form.modify(|form| form.rewatching = b);
                Task::none()
            }
            RpcMessage::Undo => {
                self.rpc.form.undo();
                Task::none()
            }
            RpcMessage::Redo => {
                self.rpc.form.redo();
                Task::none()
            }
            RpcMessage::OpenUrlClicked => {
                if !self.rpc.form.url.is_empty() {
                    let cloned_url = self.rpc.form.url.clone();
                    return Task::perform(
                        async move {
                            #[cfg(target_os = "windows")]
                            let _ = std::process::Command::new("cmd")
                                .args(["/C", "start", &cloned_url])
                                .spawn();

                            #[cfg(target_os = "macos")]
                            let _ = std::process::Command::new("open").arg(&cloned_url).spawn();

                            #[cfg(target_os = "linux")]
                            {
                                {
                                    // This will not activate the uri handler
                                    // But I'll keep it here for when iced supports xdg-activation-v1
                                    let opened_via_portal = async {
                                        if let Ok(parsed_url) = ashpd::Uri::parse(&cloned_url)
                                            && let Ok(proxy) =
                                                ashpd::desktop::open_uri::OpenURIProxy::new().await
                                            && let Ok(request) = proxy.open_uri(
                                                None,
                                                &parsed_url,
                                                ashpd::desktop::open_uri::OpenFileOptions::default()
                                            ).await {
                                                    return request.response().is_ok();
                                        }
                                        false
                                    }
                                    .await;

                                    // Fallback
                                    if !opened_via_portal {
                                        let _ = std::process::Command::new("xdg-open")
                                            .arg(&cloned_url)
                                            .spawn();
                                    }
                                }
                            }
                        },
                        |_| Message::View(ViewMessage::Animate),
                    );
                }

                Task::none()
            }
        }
    }

    fn handle_search(&mut self, message: SearchMessage, now: Instant) -> Task<Message> {
        if self.view.current != View::Search
            && let SearchMessage::MoveSelection(_)
            | SearchMessage::SelectHovered
            | SearchMessage::FocusInput = message
        {
            return Task::none();
        }

        match message {
            SearchMessage::QueryChanged(q) => {
                self.search.form.modify(|form| form.query = q);
                self.search.hovered_index = None;
                Task::none()
            }
            SearchMessage::Perform => {
                let provider = self.search.form.selected_provider;

                Task::perform(
                    perform_search(self.search.form.query.clone(), provider),
                    move |res| Message::Search(SearchMessage::Finished(provider, res)),
                )
            }
            SearchMessage::Finished(provider, Ok(results)) => {
                self.search.results.insert(provider, results.clone());
                let urls: Vec<String> = results.into_iter().map(|r| r.image_url).collect();
                Task::batch(urls.into_iter().map(|url| {
                    self.rpc
                        .image_cache
                        .put(url.clone(), CachedImage::new_pending(now));
                    Task::perform(fetch_img(url.clone()), move |handle| {
                        Message::Io(IoMessage::ImageLoaded(url, handle))
                    })
                }))
            }
            SearchMessage::Finished(_, Err(_)) => Task::none(),
            SearchMessage::ResultSelected(res) => {
                self.rpc.form.modify(|form| {
                    form.title = res.title;
                    form.url = res.url;
                    form.image_url = res.image_url;
                });
                self.view.current = View::Config;
                self.search.hovered_index = None;
                Task::none()
            }
            SearchMessage::ProviderSelected(provider) => {
                self.search
                    .form
                    .modify(|form| form.selected_provider = provider);
                self.search.hovered_index = None;
                Task::none()
            }
            SearchMessage::MoveSelection(delta) => {
                let results = self
                    .search
                    .results
                    .get(&self.search.form.selected_provider)
                    .map(|v| v.as_slice())
                    .unwrap_or(&[]);

                if results.is_empty() {
                    return Task::none();
                }

                let max_idx = results.len().saturating_sub(1);
                let new_idx = match self.search.hovered_index {
                    Some(curr) => {
                        let next = curr as isize + delta;
                        next.clamp(0, max_idx as isize) as usize
                    }
                    None => {
                        if delta > 0 {
                            0
                        } else {
                            max_idx
                        }
                    }
                };

                self.search.hovered_index = Some(new_idx);

                // FIXME: is there a way to properly calculate this?
                let offset_y = new_idx as f32 * 70.0;
                iced::widget::operation::scroll_to(
                    iced::widget::Id::new("search_scroll"),
                    iced::widget::scrollable::AbsoluteOffset {
                        x: 0.0,
                        y: offset_y,
                    },
                )
            }
            SearchMessage::SelectHovered => {
                let results = self
                    .search
                    .results
                    .get(&self.search.form.selected_provider)
                    .map(|v| v.as_slice())
                    .unwrap_or(&[]);

                if let Some(idx) = self.search.hovered_index
                    && let Some(res) = results.get(idx).cloned()
                {
                    return self.update(Message::Search(SearchMessage::ResultSelected(res)), now);
                }
                Task::none()
            }
            SearchMessage::FocusInput => {
                iced::widget::operation::focus(iced::widget::Id::new("search_bar"))
            }
            SearchMessage::Undo => {
                self.search.form.undo();
                Task::none()
            }
            SearchMessage::Redo => {
                self.search.form.redo();
                Task::none()
            }
        }
    }

    fn handle_io(&mut self, message: IoMessage, _now: Instant) -> Task<Message> {
        match message {
            IoMessage::ReconnectClicked => {
                self.sse = SseState::Connecting { attempt: 1 };
                Task::none()
            }
            IoMessage::PollerSelected(id) => {
                self.view.poller_dropdown_open = false;
                if let Some(p) = self.rpc.pollers.get(&id) {
                    if self.rpc.active_filedir != p.filedir {
                        self.rpc.form.modify(|form| {
                            form.rewatching = false;
                            form.title.clear();
                            form.url.clear();
                            form.image_url.clear();
                        });
                        self.rpc.raw_content.clear();
                        self.rpc.active_filedir = p.filedir.clone();
                        self.rpc.title_placeholder = self
                            .rpc
                            .active_filedir
                            .as_ref()
                            .map(|dir| clean_dir_name(dir))
                            .unwrap_or_default();
                    }

                    if p.active {
                        self.rpc.active_id = Some(id);
                        if let Some(dir) = &p.filedir {
                            return Task::perform(load_rpc(dir.clone()), |res| {
                                Message::Io(IoMessage::RpcLoaded(res))
                            });
                        }
                    }
                }

                Task::none()
            }
            IoMessage::RpcLoaded(Ok(content)) => {
                self.rpc.raw_content = content.clone();

                self.rpc.form.modify(|form| {
                    form.rewatching = false;
                    for line in content.lines() {
                        let parts: Vec<&str> = line.splitn(2, '=').collect();
                        if parts.len() == 2 {
                            match parts[0] {
                                "title" => form.title = parts[1].to_string(),
                                "url" => form.url = parts[1].to_string(),
                                "image_url" => form.image_url = parts[1].to_string(),
                                "rewatching" => {
                                    form.rewatching = parts[1] != "0";
                                }
                                _ => {}
                            }
                        }
                    }
                });

                if !self.rpc.form.image_url.is_empty() {
                    return Task::done(Message::Rpc(RpcMessage::ImageUrlChanged(
                        self.rpc.form.image_url.clone(),
                    )));
                }

                Task::none()
            }
            IoMessage::SaveClicked => {
                if let Some(id) = &self.rpc.active_id
                    && let Some(p) = self.rpc.pollers.get(id)
                    && let Some(dir) = &p.filedir
                {
                    return Task::perform(
                        save_rpc(
                            dir.clone(),
                            self.rpc.raw_content.clone(),
                            self.rpc.form.title.clone(),
                            self.rpc.form.url.clone(),
                            self.rpc.form.image_url.clone(),
                            self.rpc.form.rewatching,
                        ),
                        |res| Message::Io(IoMessage::SaveCompleted(res)),
                    );
                };

                Task::none()
            }
            IoMessage::SaveCompleted(res) => {
                self.view.save_status = if res.is_ok() {
                    SaveStatus::Saved
                } else {
                    SaveStatus::Failed
                };

                Task::perform(
                    async {
                        tokio::time::sleep(std::time::Duration::from_secs(2)).await;
                    },
                    |_| Message::Io(IoMessage::ResetSaveStatus),
                )
            }
            IoMessage::ResetSaveStatus => {
                self.view.save_status = SaveStatus::Idle;
                Task::none()
            }
            IoMessage::ImageLoaded(url, handle_opt) => {
                self.rpc.image_cache.put(
                    url,
                    match handle_opt {
                        Some(handle) => CachedImage::Ready(handle),
                        None => CachedImage::Failed,
                    },
                );
                Task::none()
            }
            _ => Task::none(),
        }
    }

    fn handle_sse(&mut self, message: SseMessage, _now: Instant) -> Task<Message> {
        match message {
            SseMessage::Connected => {
                self.sse = SseState::Connected;
                Task::none()
            }
            SseMessage::Data(json_str) => {
                match serde_json::from_str::<PollerStatePayload>(&json_str) {
                    Ok(payload) => {
                        self.rpc.pollers = payload;

                        if let Some(id) = &self.rpc.active_id
                            && !self.rpc.pollers.get(id).is_some_and(|p| p.active)
                        {
                            self.clear_config_form();
                        }

                        if self.rpc.active_id.is_none()
                            && let Some((id, _)) = self.rpc.pollers.iter().find(|(_, p)| p.active)
                        {
                            self.rpc.active_id = Some(id.clone());
                        }

                        if let Some(id) = &self.rpc.active_id {
                            return Task::done(Message::Io(IoMessage::PollerSelected(id.clone())));
                        }
                    }
                    Err(err) => eprintln!("Failed to parse poller payload: {:?}", err),
                }

                Task::none()
            }
            SseMessage::Disconnected => {
                self.rpc.pollers.clear();
                self.clear_config_form();
                let attempt = match self.sse {
                    SseState::Connecting { attempt: a } => a,
                    SseState::WaitingToReconnect { attempt: a, .. } => a,
                    _ => 1,
                };
                let backoff = (2u64.pow(attempt)).min(60);
                self.sse = SseState::WaitingToReconnect {
                    seconds_left: backoff,
                    attempt: attempt + 1,
                };
                Task::none()
            }
            SseMessage::Tick => {
                if let SseState::WaitingToReconnect {
                    seconds_left,
                    attempt,
                } = &mut self.sse
                {
                    if *seconds_left > 0 {
                        *seconds_left -= 1;
                    } else {
                        self.sse = SseState::Connecting { attempt: *attempt };
                    }
                }

                Task::none()
            }
        }
    }

    pub fn view(&self) -> Element<'_, Message> {
        let content = match self.view.current {
            View::Config => views::config::view(self),
            View::Search => views::search::view(self),
        };

        container(content)
            .width(Length::Fill)
            .height(Length::Fill)
            .into()
    }
}
