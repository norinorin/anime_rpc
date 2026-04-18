use crate::api::{fetch_img, fetch_pollers, perform_search};
use crate::constants::{TICK_RATE_MS, image_cache_size};
use crate::types::{Message, Poller, SaveStatus, SearchResult, View};
use crate::utils::{clean_dir_name, load_icon, load_rpc, save_rpc};
use crate::views;
use iced::futures::SinkExt;
use iced::futures::channel::mpsc::Sender;
use iced::widget::container;
use iced::widget::image::Handle;
use iced::{Element, Length, Task, window};
use lru::LruCache;
use std::collections::HashMap;
use std::time::{Duration, Instant};
use tray_icon::TrayIconBuilder;
use tray_icon::menu::{Menu, MenuItem};

pub struct AnimeRpc {
    pub current_view: View,
    pub pollers: HashMap<String, Poller>,
    pub active_id: Option<String>,
    pub active_filedir: Option<String>,
    pub title: String,
    pub title_placeholder: String,
    pub url: String,
    pub image_url: String,
    pub rewatching: bool,
    pub raw_content: String,
    pub search_query: String,
    pub search_results: Vec<SearchResult>,
    pub image_cache: LruCache<String, Handle>,
    pub window_visible: bool,
    #[allow(dead_code)]
    pub tray_icon: tray_icon::TrayIcon,
    pub save_status: SaveStatus,

    // animation
    start_time: Instant,
    pub elapsed_time: f32,
}

impl AnimeRpc {
    pub fn init() -> (Self, Task<Message>) {
        let _ = gtk::init();
        let tray_menu = Menu::new();
        tray_menu
            .append_items(&[
                &MenuItem::with_id("show", "Show/Hide", true, None),
                &MenuItem::with_id("quit", "Quit", true, None),
            ])
            .unwrap();

        let tray_icon = TrayIconBuilder::new()
            .with_menu(Box::new(tray_menu))
            .with_menu_on_left_click(false)
            .with_tooltip("Anime RPC")
            .with_icon(load_icon())
            .build()
            .unwrap();

        (
            Self {
                current_view: View::Config,
                pollers: HashMap::new(),
                active_id: None,
                active_filedir: None,
                title: String::new(),
                title_placeholder: "Title...".to_string(),
                url: String::new(),
                image_url: String::new(),
                rewatching: false,
                raw_content: String::new(),
                search_query: String::new(),
                search_results: Vec::new(),
                image_cache: LruCache::new(image_cache_size()),
                window_visible: false,
                save_status: SaveStatus::Idle,
                elapsed_time: 0.0,
                start_time: Instant::now(),
                tray_icon,
            },
            Task::perform(fetch_pollers(), Message::PollersFetched),
        )
    }

    pub fn subscription(&self) -> iced::Subscription<Message> {
        let tray_sub = iced::Subscription::run(|| {
            iced::stream::channel(10, |mut output: Sender<Message>| async move {
                let tray_receiver = tray_icon::TrayIconEvent::receiver();
                let menu_receiver = tray_icon::menu::MenuEvent::receiver();
                loop {
                    if let Ok(tray_icon::TrayIconEvent::Click { button, .. }) =
                        tray_receiver.try_recv()
                        && button == tray_icon::MouseButton::Left
                    {
                        let _ = output.send(Message::ToggleWindow).await;
                    }
                    if let Ok(event) = menu_receiver.try_recv() {
                        match event.id.as_ref() {
                            "show" => {
                                let _ = output.send(Message::ToggleWindow).await;
                            }
                            "quit" => {
                                let _ = output.send(Message::Quit).await;
                            }
                            _ => {}
                        }
                    }
                    tokio::time::sleep(Duration::from_millis(TICK_RATE_MS)).await;
                }
            })
        });

        let tick = iced::window::frames().map(|_| Message::Tick);

        let keyboard_sub = iced::keyboard::listen().filter_map(|event| match event {
            iced::keyboard::Event::KeyPressed {
                key: iced::keyboard::Key::Named(iced::keyboard::key::Named::Escape),
                ..
            } => Some(Message::ToggleWindow),
            _ => None,
        });

        iced::Subscription::batch([tray_sub, tick, keyboard_sub])
    }

    pub fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::ToggleWindow => {
                self.window_visible = !self.window_visible;
                let mode = if self.window_visible {
                    window::Mode::Windowed
                } else {
                    window::Mode::Hidden
                };
                return window::latest().and_then(move |id| window::set_mode(id, mode));
            }
            Message::SwitchView(v) => {
                if v == View::Search
                    && let Some(id) = &self.active_id
                    && let Some(p) = self.pollers.get(id)
                    && let Some(dir) = &p.filedir
                {
                    self.search_query = clean_dir_name(dir);
                }
                self.current_view = v;
            }
            Message::TitleChanged(val) => self.title = val,
            Message::UrlChanged(val) => self.url = val,
            Message::ImageUrlChanged(val) => {
                self.image_url = val.clone();
                if !val.is_empty() && !self.image_cache.contains(&val) {
                    return Task::perform(fetch_img(val.clone()), move |handle| {
                        Message::ImageLoaded(val, handle)
                    });
                }
            }
            Message::ToggleRewatching(b) => self.rewatching = b,
            Message::SearchQueryChanged(q) => self.search_query = q,
            Message::RefreshClicked => {
                return Task::perform(fetch_pollers(), Message::PollersFetched);
            }
            Message::PollersFetched(Ok(data)) => {
                self.pollers = data;
                if let Some(id) = &self.active_id
                    && !self.pollers.contains_key(id)
                {
                    self.active_id = None;
                    self.active_filedir = None;
                }

                if self.active_id.is_none()
                    && let Some((id, _)) = self.pollers.iter().find(|(_, p)| p.active)
                {
                    self.active_id = Some(id.clone());
                }

                if let Some(id) = &self.active_id {
                    return Task::done(Message::PollerSelected(id.clone()));
                }
            }
            Message::PollerSelected(id) => {
                if let Some(p) = self.pollers.get(&id) {
                    if self.active_filedir != p.filedir {
                        self.raw_content.clear();
                        self.rewatching = false;
                        self.title.clear();
                        self.url.clear();
                        self.image_url.clear();
                        self.active_filedir = p.filedir.clone();
                        self.title_placeholder = if let Some(dir) = &self.active_filedir {
                            clean_dir_name(dir)
                        } else {
                            "Title...".to_string()
                        }
                    }

                    if p.active {
                        self.active_id = Some(id);
                        if let Some(dir) = &p.filedir {
                            return Task::perform(load_rpc(dir.clone()), Message::RpcLoaded);
                        }
                    }
                }
            }
            Message::RpcLoaded(Ok(content)) => {
                self.raw_content = content.clone();
                self.rewatching = false;
                for line in content.lines() {
                    let parts: Vec<&str> = line.splitn(2, '=').collect();
                    if parts.len() == 2 {
                        match parts[0] {
                            "title" => self.title = parts[1].to_string(),
                            "url" => self.url = parts[1].to_string(),
                            "image_url" => self.image_url = parts[1].to_string(),
                            "rewatching" => self.rewatching = parts[1] != "0",
                            _ => {}
                        }
                    }
                }

                if !self.image_url.is_empty() {
                    return Task::done(Message::ImageUrlChanged(self.image_url.clone()));
                }
            }
            Message::PerformSearch => {
                return Task::perform(
                    perform_search(self.search_query.clone()),
                    Message::SearchFinished,
                );
            }
            Message::SearchFinished(Ok(results)) => {
                self.search_results = results.clone();
                let urls: Vec<String> = results.into_iter().map(|r| r.image_url).collect();
                return Task::batch(urls.into_iter().map(|url| {
                    Task::perform(fetch_img(url.clone()), move |handle| {
                        Message::ImageLoaded(url, handle)
                    })
                }));
            }
            Message::ResultSelected(res) => {
                self.title = res.title;
                self.url = res.url;
                self.image_url = res.image_url;
                self.current_view = View::Config;
            }
            Message::SaveClicked => {
                if let Some(id) = &self.active_id
                    && let Some(p) = self.pollers.get(id)
                    && let Some(dir) = &p.filedir
                {
                    save_rpc(
                        dir.clone(),
                        &self.raw_content,
                        self.title.clone(),
                        self.url.clone(),
                        self.image_url.clone(),
                        self.rewatching,
                    );

                    self.save_status = SaveStatus::Saved;

                    return Task::perform(
                        async {
                            tokio::time::sleep(std::time::Duration::from_secs(2)).await;
                        },
                        |_| Message::ResetSaveStatus,
                    );
                }
            }
            Message::OpenUrlClicked => {
                if !self.url.is_empty() {
                    let cloned_url = self.url.clone();
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

                                    if !opened_via_portal {
                                        println!("Falling back");
                                        let _ = std::process::Command::new("xdg-open")
                                            .arg(&cloned_url)
                                            .spawn();
                                    } else {
                                        println!("XDG success");
                                    }
                                }
                            }
                        },
                        |_| Message::Tick,
                    );
                }
            }
            Message::ResetSaveStatus => {
                self.save_status = SaveStatus::Idle;
            }
            Message::ImageLoaded(url, Some(handle)) => {
                self.image_cache.put(url, handle);
            }
            Message::Tick => {
                while gtk::events_pending() {
                    gtk::main_iteration_do(false);
                }

                self.elapsed_time = self.start_time.elapsed().as_secs_f32();
            }
            Message::Quit => {
                return iced::exit();
            }
            _ => {}
        }
        Task::none()
    }

    pub fn view(&self) -> Element<'_, Message> {
        let content = match self.current_view {
            View::Config => views::config::view(self),
            View::Search => views::search::view(self),
        };

        container(content)
            .width(Length::Fill)
            .height(Length::Fill)
            .into()
    }
}
