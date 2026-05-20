use crate::api::{fetch_img, fetch_pollers, perform_search};
use crate::constants::image_cache_size;
use crate::types::{Message, Poller, SaveStatus, SearchResult, View};
use crate::utils::{clean_dir_name, load_rpc, save_rpc};
use crate::views;
use iced::widget::container;
use iced::widget::image::Handle;
use iced::{Element, Length, Task, window};
use lru::LruCache;
use std::collections::HashMap;
use std::time::Instant;

pub struct AnimeRpc {
    pub view: ViewState,
    pub rpc: RpcState,
    pub search: SearchState,
}

pub struct ViewState {
    pub current: View,
    pub window_visible: bool,
    pub elapsed_time: f32,
    pub start_time: Instant,
    pub save_status: SaveStatus,
}

pub struct RpcState {
    pub pollers: HashMap<String, Poller>,
    pub active_id: Option<String>,
    pub active_filedir: Option<String>,
    pub title: String,
    pub title_placeholder: String,
    pub url: String,
    pub image_url: String,
    pub rewatching: bool,
    pub raw_content: String,
    pub image_cache: LruCache<String, Handle>,
}

pub struct SearchState {
    pub query: String,
    pub results: Vec<SearchResult>,
}

impl AnimeRpc {
    pub fn init() -> (Self, Task<Message>) {
        (
            Self {
                view: ViewState {
                    current: View::Config,
                    window_visible: true,
                    elapsed_time: 0.0,
                    start_time: Instant::now(),
                    save_status: SaveStatus::Idle,
                },
                rpc: RpcState {
                    pollers: HashMap::new(),
                    active_id: None,
                    active_filedir: None,
                    title: String::new(),
                    title_placeholder: "Title...".to_string(),
                    url: String::new(),
                    image_url: String::new(),
                    rewatching: false,
                    raw_content: String::new(),
                    image_cache: LruCache::new(image_cache_size()),
                },
                search: SearchState {
                    query: String::new(),
                    results: Vec::new(),
                },
            },
            Task::perform(fetch_pollers(), Message::PollersFetched),
        )
    }

    pub fn subscription(&self) -> iced::Subscription<Message> {
        let tick = iced::window::frames().map(|_| Message::Tick);

        let keyboard_sub = iced::keyboard::listen().filter_map(|event| match event {
            iced::keyboard::Event::KeyPressed {
                key: iced::keyboard::Key::Named(iced::keyboard::key::Named::Escape),
                ..
            } => Some(Message::ToggleWindow),
            iced::keyboard::Event::KeyPressed {
                key: iced::keyboard::Key::Named(iced::keyboard::key::Named::Tab),
                modifiers,
                ..
            } => Some(Message::TabPressed {
                shift: modifiers.shift(),
            }),
            _ => None,
        });

        iced::Subscription::batch([tick, keyboard_sub])
    }

    pub fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::ToggleWindow => {
                self.view.window_visible = !self.view.window_visible;
                let mode = if self.view.window_visible {
                    window::Mode::Windowed
                } else {
                    window::Mode::Hidden
                };
                return window::latest().and_then(move |id| window::set_mode(id, mode));
            }
            Message::SwitchView(v) => {
                if v == View::Search
                    && let Some(id) = &self.rpc.active_id
                    && let Some(p) = self.rpc.pollers.get(id)
                    && let Some(dir) = &p.filedir
                {
                    self.search.query = clean_dir_name(dir);
                }
                self.view.current = v;
            }
            Message::TitleChanged(val) => self.rpc.title = val,
            Message::UrlChanged(val) => self.rpc.url = val,
            Message::ImageUrlChanged(val) => {
                self.rpc.image_url = val.clone();
                if !val.is_empty() && !self.view.image_cache.contains(&val) {
                    return Task::perform(fetch_img(val.clone()), move |handle| {
                        Message::ImageLoaded(val, handle)
                    });
                }
            }
            Message::ToggleRewatching(b) => self.rpc.rewatching = b,
            Message::SearchQueryChanged(q) => self.search.query = q,
            Message::RefreshClicked => {
                return Task::perform(fetch_pollers(), Message::PollersFetched);
            }
            Message::PollersFetched(Ok(data)) => {
                self.rpc.pollers = data;
                if let Some(id) = &self.rpc.active_id
                    && !self.rpc.pollers.contains_key(id)
                {
                    self.rpc.active_id = None;
                    self.rpc.active_filedir = None;
                }

                if self.rpc.active_id.is_none()
                    && let Some((id, _)) = self.rpc.pollers.iter().find(|(_, p)| p.active)
                {
                    self.rpc.active_id = Some(id.clone());
                }

                if let Some(id) = &self.rpc.active_id {
                    return Task::done(Message::PollerSelected(id.clone()));
                }
            }
            Message::PollerSelected(id) => {
                if let Some(p) = self.rpc.pollers.get(&id) {
                    if self.rpc.active_filedir != p.filedir {
                        self.rpc.raw_content.clear();
                        self.rpc.rewatching = false;
                        self.rpc.title.clear();
                        self.rpc.url.clear();
                        self.rpc.image_url.clear();
                        self.rpc.active_filedir = p.filedir.clone();
                        self.rpc.title_placeholder = if let Some(dir) = &self.rpc.active_filedir {
                            clean_dir_name(dir)
                        } else {
                            "Title...".to_string()
                        }
                    }

                    if p.active {
                        self.rpc.active_id = Some(id);
                        if let Some(dir) = &p.filedir {
                            return Task::perform(load_rpc(dir.clone()), Message::RpcLoaded);
                        }
                    }
                }
            }
            Message::RpcLoaded(Ok(content)) => {
                self.rpc.raw_content = content.clone();
                self.rpc.rewatching = false;
                for line in content.lines() {
                    let parts: Vec<&str> = line.splitn(2, '=').collect();
                    if parts.len() == 2 {
                        match parts[0] {
                            "title" => self.rpc.title = parts[1].to_string(),
                            "url" => self.rpc.url = parts[1].to_string(),
                            "image_url" => self.rpc.image_url = parts[1].to_string(),
                            "rewatching" => self.rpc.rewatching = parts[1] != "0",
                            _ => {}
                        }
                    }
                }

                if !self.rpc.image_url.is_empty() {
                    return Task::done(Message::ImageUrlChanged(self.rpc.image_url.clone()));
                }
            }
            Message::PerformSearch => {
                return Task::perform(
                    perform_search(self.search.query.clone()),
                    Message::SearchFinished,
                );
            }
            Message::SearchFinished(Ok(results)) => {
                self.search.results = results.clone();
                let urls: Vec<String> = results.into_iter().map(|r| r.image_url).collect();
                return Task::batch(urls.into_iter().map(|url| {
                    Task::perform(fetch_img(url.clone()), move |handle| {
                        Message::ImageLoaded(url, handle)
                    })
                }));
            }
            Message::ResultSelected(res) => {
                self.rpc.title = res.title;
                self.rpc.url = res.url;
                self.rpc.image_url = res.image_url;
                self.view.current = View::Config;
            }
            Message::SaveClicked => {
                if let Some(id) = &self.rpc.active_id
                    && let Some(p) = self.rpc.pollers.get(id)
                    && let Some(dir) = &p.filedir
                {
                    return Task::perform(
                        save_rpc(
                            dir.clone(),
                            self.rpc.raw_content.clone(),
                            self.rpc.title.clone(),
                            self.rpc.url.clone(),
                            self.rpc.image_url.clone(),
                            self.rpc.rewatching,
                        ),
                        Message::SaveCompleted,
                    );
                };
            }
            Message::SaveCompleted(res) => {
                self.rpc.save_status = if res.is_ok() {
                    SaveStatus::Saved
                } else {
                    SaveStatus::Failed
                };

                return Task::perform(
                    async {
                        tokio::time::sleep(std::time::Duration::from_secs(2)).await;
                    },
                    |_| Message::ResetSaveStatus,
                );
            }
            Message::OpenUrlClicked => {
                if !self.rpc.url.is_empty() {
                    let cloned_url = self.rpc.url.clone();
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
                        |_| Message::Tick,
                    );
                }
            }
            Message::ResetSaveStatus => {
                self.rpc.save_status = SaveStatus::Idle;
            }
            Message::ImageLoaded(url, Some(handle)) => {
                self.view.image_cache.put(url, handle);
            }
            Message::Tick => {
                self.view.elapsed_time = self.view.start_time.elapsed().as_secs_f32();
            }
            Message::TabPressed { shift } => {
                if shift {
                    return iced::widget::operation::focus_previous();
                } else {
                    return iced::widget::operation::focus_next();
                }
            }
            _ => {}
        }
        Task::none()
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
