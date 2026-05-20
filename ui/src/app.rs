use crate::api::{fetch_img, fetch_pollers, perform_search};
use crate::constants::image_cache_size;
use crate::types::{
    DaemonStatus, IoMessage, Message, Poller, RpcMessage, SaveStatus, SearchMessage, SearchResult,
    View, ViewMessage,
};
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
    pub poller_dropdown_open: bool,
    pub elapsed_time: f32,
    pub start_time: Instant,
    pub save_status: SaveStatus,
    pub daemon_status: DaemonStatus,
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
                    poller_dropdown_open: false,
                    elapsed_time: 0.0,
                    start_time: Instant::now(),
                    save_status: SaveStatus::default(),
                    daemon_status: DaemonStatus::default(),
                },
                rpc: RpcState {
                    pollers: HashMap::new(),
                    active_id: None,
                    active_filedir: None,
                    title: String::new(),
                    title_placeholder: String::new(),
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
            Task::perform(fetch_pollers(), |res| {
                Message::Io(IoMessage::PollersFetched(res))
            }),
        )
    }

    pub fn subscription(&self) -> iced::Subscription<Message> {
        let tick = iced::window::frames().map(|_| Message::View(ViewMessage::Tick));

        let keyboard_sub = iced::keyboard::listen().filter_map(|event| match event {
            iced::keyboard::Event::KeyPressed {
                key: iced::keyboard::Key::Named(iced::keyboard::key::Named::Escape),
                ..
            } => Some(Message::View(ViewMessage::ToggleWindow)),
            iced::keyboard::Event::KeyPressed {
                key: iced::keyboard::Key::Named(iced::keyboard::key::Named::Tab),
                modifiers,
                ..
            } => Some(Message::View(ViewMessage::TabPressed {
                shift: modifiers.shift(),
            })),
            _ => None,
        });

        iced::Subscription::batch([tick, keyboard_sub])
    }

    pub fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::View(msg) => self.handle_view(msg),
            Message::Rpc(msg) => self.handle_rpc(msg),
            Message::Search(msg) => self.handle_search(msg),
            Message::Io(msg) => self.handle_io(msg),
        }
    }

    fn handle_view(&mut self, message: ViewMessage) -> Task<Message> {
        match message {
            ViewMessage::ToggleWindow => {
                self.view.window_visible = !self.view.window_visible;
                let mode = if self.view.window_visible {
                    window::Mode::Windowed
                } else {
                    window::Mode::Hidden
                };
                window::latest().and_then(move |id| window::set_mode(id, mode))
            }
            ViewMessage::Switch(v) => {
                if v == View::Search
                    && let Some(id) = &self.rpc.active_id
                    && let Some(p) = self.rpc.pollers.get(id)
                    && let Some(dir) = &p.filedir
                {
                    self.search.query = clean_dir_name(dir);
                }
                self.view.current = v;
                Task::none()
            }
            ViewMessage::Tick => {
                self.view.elapsed_time = self.view.start_time.elapsed().as_secs_f32();
                Task::none()
            }
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

    fn handle_rpc(&mut self, message: RpcMessage) -> Task<Message> {
        match message {
            RpcMessage::TitleChanged(val) => {
                self.rpc.title = val;
                Task::none()
            }
            RpcMessage::UrlChanged(val) => {
                self.rpc.url = val;
                Task::none()
            }
            RpcMessage::ImageUrlChanged(val) => {
                self.rpc.image_url = val.clone();
                if !val.is_empty() && !self.rpc.image_cache.contains(&val) {
                    return Task::perform(fetch_img(val.clone()), move |handle| {
                        Message::Io(IoMessage::ImageLoaded(val, handle))
                    });
                }
                Task::none()
            }
            RpcMessage::ToggleRewatching(b) => {
                self.rpc.rewatching = b;
                Task::none()
            }
            RpcMessage::OpenUrlClicked => {
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
                        |_| Message::View(ViewMessage::Tick),
                    );
                }

                Task::none()
            }
        }
    }

    fn handle_search(&mut self, message: SearchMessage) -> Task<Message> {
        match message {
            SearchMessage::QueryChanged(q) => {
                self.search.query = q;
                Task::none()
            }
            SearchMessage::Perform => {
                Task::perform(perform_search(self.search.query.clone()), |res| {
                    Message::Search(SearchMessage::Finished(res))
                })
            }
            SearchMessage::Finished(Ok(results)) => {
                self.search.results = results.clone();
                let urls: Vec<String> = results.into_iter().map(|r| r.image_url).collect();
                Task::batch(urls.into_iter().map(|url| {
                    Task::perform(fetch_img(url.clone()), move |handle| {
                        Message::Io(IoMessage::ImageLoaded(url, handle))
                    })
                }))
            }
            SearchMessage::Finished(Err(_)) => Task::none(),
            SearchMessage::ResultSelected(res) => {
                self.rpc.title = res.title;
                self.rpc.url = res.url;
                self.rpc.image_url = res.image_url;
                self.view.current = View::Config;
                Task::none()
            }
        }
    }

    fn handle_io(&mut self, message: IoMessage) -> Task<Message> {
        match message {
            IoMessage::RefreshClicked => Task::perform(fetch_pollers(), |res| {
                Message::Io(IoMessage::PollersFetched(res))
            }),
            IoMessage::PollersFetched(res) => {
                if res.is_err() {
                    self.view.daemon_status = DaemonStatus::Disconnected;
                    return Task::none();
                }

                self.view.daemon_status = DaemonStatus::Connected;
                self.rpc.pollers = res.unwrap();
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
                    return Task::done(Message::Io(IoMessage::PollerSelected(id.clone())));
                }

                Task::none()
            }
            IoMessage::PollerSelected(id) => {
                self.view.poller_dropdown_open = false;
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
                    return Task::done(Message::Rpc(RpcMessage::ImageUrlChanged(
                        self.rpc.image_url.clone(),
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
                            self.rpc.title.clone(),
                            self.rpc.url.clone(),
                            self.rpc.image_url.clone(),
                            self.rpc.rewatching,
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
            IoMessage::ImageLoaded(url, Some(handle)) => {
                self.rpc.image_cache.put(url, handle);
                Task::none()
            }
            _ => Task::none(),
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
