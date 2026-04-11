use iced::futures::SinkExt;
use iced::futures::channel::mpsc::Sender;
use iced::widget::image::Handle;
use iced::widget::{
    Space, button, checkbox, column, container, image as image_widget, pick_list, row, scrollable,
    text, text_input,
};
use iced::{Center, Element, Length, Size, Task, window};
use lru::LruCache;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::num::NonZeroUsize;
use tray_icon::{
    TrayIconBuilder,
    menu::{Menu, MenuItem},
};

pub fn main() -> iced::Result {
    iced::application(AnimeRpc::init, AnimeRpc::update, AnimeRpc::view)
        .subscription(AnimeRpc::subscription)
        .title("Anime RPC")
        .window(window::Settings {
            size: Size::new(400.0, 550.0),
            resizable: false,
            visible: false,

            ..Default::default()
        })
        .theme(|_state: &AnimeRpc| iced::Theme::Dark)
        .run()
}

fn load_icon(path: &str) -> tray_icon::Icon {
    let (icon_rgba, icon_width, icon_height) = {
        let image = ::image::open(path)
            .expect("Failed to open icon path")
            .into_rgba8();
        let (width, height) = image.dimensions();
        let rgba = image.into_raw();
        (rgba, width, height)
    };
    tray_icon::Icon::from_rgba(icon_rgba, icon_width, icon_height).expect("Failed to open icon")
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Poller {
    display_name: String,
    active: bool,
    filedir: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SearchResult {
    id: String,
    title: String,
    url: String,
    image_url: String,
}

struct AnimeRpc {
    current_view: View,
    pollers: HashMap<String, Poller>,
    active_id: Option<String>,
    active_filedir: Option<String>,
    title: String,
    url: String,
    image_url: String,
    rewatching: bool,
    raw_content: String,
    search_query: String,
    search_results: Vec<SearchResult>,
    image_cache: LruCache<String, Handle>,
    window_visible: bool,
    #[allow(dead_code)]
    tray_icon: tray_icon::TrayIcon,
}

#[derive(Default, Clone, Copy, Debug, PartialEq, Eq)]
enum View {
    #[default]
    Config,
    Search,
}

#[derive(Debug, Clone)]
enum Message {
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
    ImageLoaded(String, Option<iced::widget::image::Handle>),
    ToggleWindow,
    RefreshClicked,
    PumpGtk,
    Quit,
}

impl AnimeRpc {
    fn init() -> (Self, Task<Message>) {
        let _ = gtk::init();
        let tray_menu = Menu::new();
        let quit_i = MenuItem::with_id("quit", "Quit", true, None);
        let show_i = MenuItem::with_id("show", "Show/Hide", true, None);
        tray_menu.append_items(&[&show_i, &quit_i]).unwrap();

        let tray_icon = TrayIconBuilder::new()
            .with_menu(Box::new(tray_menu))
            .with_menu_on_left_click(false)
            .with_tooltip("Anime RPC")
            .with_icon(load_icon("assets/icon.png"))
            .build()
            .unwrap();

        (
            Self {
                current_view: View::Config,
                pollers: HashMap::new(),
                active_id: None,
                active_filedir: None,
                title: String::new(),
                url: String::new(),
                image_url: String::new(),
                rewatching: false,
                raw_content: String::new(),
                search_query: String::new(),
                search_results: Vec::new(),
                image_cache: LruCache::new(NonZeroUsize::new(100).unwrap()),
                window_visible: false,
                tray_icon,
            },
            Task::perform(fetch_pollers(), Message::PollersFetched),
        )
    }

    fn subscription(&self) -> iced::Subscription<Message> {
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
                        if event.id.as_ref() == "show" {
                            let _ = output.send(Message::ToggleWindow).await;
                        } else if event.id.as_ref() == "quit" {
                            let _ = output.send(Message::Quit).await;
                        }
                    }
                    tokio::time::sleep(std::time::Duration::from_millis(50)).await;
                }
            })
        });

        let gtk_pump =
            iced::time::every(std::time::Duration::from_millis(50)).map(|_| Message::PumpGtk);

        let keyboard_sub = iced::keyboard::listen().filter_map(|event| match event {
            iced::keyboard::Event::KeyPressed {
                key: iced::keyboard::Key::Named(iced::keyboard::key::Named::Escape),
                ..
            } => Some(Message::ToggleWindow),
            _ => None,
        });

        iced::Subscription::batch([tray_sub, gtk_pump, keyboard_sub])
    }
    fn update(&mut self, message: Message) -> Task<Message> {
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
                    && let Some((id, _p)) = self.pollers.iter().find(|(_, p)| p.active)
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
                        self.raw_content = String::new();
                        self.rewatching = false;
                        self.title = String::new();
                        self.url = String::new();
                        self.image_url = String::new();
                        self.active_filedir = p.filedir.clone();
                    }

                    if p.active {
                        self.active_id = Some(id);
                        if let Some(dir) = &p.filedir {
                            return Task::perform(load_rpc(dir.clone()), Message::RpcLoaded);
                        }
                    } else {
                        return Task::none();
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
                }
            }
            Message::ImageLoaded(url, Some(handle)) => {
                self.image_cache.put(url, handle);
            }
            Message::PumpGtk => {
                while gtk::events_pending() {
                    gtk::main_iteration_do(false);
                }
            }
            Message::Quit => {
                return iced::exit();
            }
            _ => {}
        }
        Task::none()
    }

    fn view(&self) -> Element<'_, Message> {
        let content = match self.current_view {
            View::Config => self.config_view(),
            View::Search => self.search_view(),
        };

        container(content)
            .width(Length::Fill)
            .height(Length::Fill)
            .into()
    }

    fn config_view(&self) -> Element<'_, Message> {
        let poller_list: Vec<String> = self
            .pollers
            .values()
            .map(|p| {
                format!(
                    "{} {} | {}",
                    if p.active { "●" } else { "○" },
                    p.display_name,
                    if p.active { "Active" } else { "Waiting" }
                )
            })
            .collect();

        let poller_select = pick_list(poller_list, self.active_id.clone(), Message::PollerSelected)
            .placeholder("Select Poller...")
            .width(Length::Fill);

        let is_active = self
            .active_id
            .as_ref()
            .and_then(|id| self.pollers.get(id))
            .is_some_and(|p| p.active);

        let search_btn = button("🔍");
        let search_btn = if is_active {
            search_btn.on_press(Message::SwitchView(View::Search))
        } else {
            search_btn
        };

        let title_placeholder = if let Some(filedir) = &self.active_filedir {
            clean_dir_name(filedir)
        } else {
            "Title...".to_string()
        };

        column![
            text("Available Pollers").size(18),
            poller_select,
            text("Media Title").size(14),
            text_input(&title_placeholder, &self.title).on_input(Message::TitleChanged),
            text("Media URL").size(14),
            row![
                text_input("URL...", &self.url).on_input(Message::UrlChanged),
                search_btn
            ]
            .spacing(10),
            text("Image URL").size(14),
            text_input("Image URL...", &self.image_url).on_input(Message::ImageUrlChanged),
            checkbox(self.rewatching)
                .label("Rewatching")
                .on_toggle(Message::ToggleRewatching),
            if !self.image_url.is_empty()
                && let Some(handle) = self.image_cache.peek(&self.image_url)
            {
                container(image_widget(handle).width(Length::Fixed(200.0)))
                    .width(Length::Fill)
                    .align_x(Center)
            } else {
                container(Space::new().height(Length::Fill).width(Length::Fill))
            },
            Space::new().height(Length::Fill),
            row![
                button("Save Changes")
                    .on_press(Message::SaveClicked)
                    .style(button::success)
                    .width(Length::Fill),
                button("Refresh")
                    .on_press(Message::RefreshClicked)
                    .style(button::primary)
                    .width(Length::Shrink)
            ]
            .spacing(10)
        ]
        .spacing(12)
        .padding(20)
        .into()
    }

    fn search_view(&self) -> Element<'_, Message> {
        let results = scrollable(
            column(
                self.search_results
                    .iter()
                    .map(|res| {
                        let img_widget: Element<'_, Message> =
                            if let Some(handle) = self.image_cache.peek(&res.image_url) {
                                container(image_widget(handle.clone()).width(Length::Fixed(60.0)))
                                    .width(Length::Fixed(60.0))
                                    .align_x(iced::Center)
                                    .into()
                            } else {
                                container(text("Loading...").size(10))
                                    .width(Length::Fixed(60.0))
                                    .into()
                            };

                        button(
                            row![
                                img_widget,
                                column![
                                    text(&res.title).size(16).font(iced::Font {
                                        weight: iced::font::Weight::Bold,
                                        ..Default::default()
                                    }),
                                    text("MyAnimeList").size(12).color([0.5, 0.5, 0.5]),
                                ]
                                .spacing(5)
                            ]
                            .spacing(15)
                            .align_y(iced::Alignment::Center)
                            .padding(5),
                        )
                        .width(Length::Fill)
                        .on_press(Message::ResultSelected(res.clone()))
                        .into()
                    })
                    .collect::<Vec<Element<Message>>>(),
            )
            .spacing(10),
        );

        column![
            button("<- Back").on_press(Message::SwitchView(View::Config)),
            row![
                text_input("Search anime...", &self.search_query)
                    .on_input(Message::SearchQueryChanged)
                    .on_submit(Message::PerformSearch),
                button("Go").on_press(Message::PerformSearch)
            ]
            .spacing(10),
            results,
        ]
        .spacing(15)
        .padding(20)
        .into()
    }
}

async fn fetch_pollers() -> Result<HashMap<String, Poller>, String> {
    reqwest::get("http://127.0.0.1:56727/pollers")
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())
}

async fn load_rpc(dir: String) -> Result<String, String> {
    let path = format!("{}/.rpc", dir);
    fs::read_to_string(path).map_err(|e| e.to_string())
}

async fn fetch_img(url: String) -> Option<Handle> {
    match reqwest::get(&url).await {
        Ok(res) => match res.bytes().await {
            Ok(bytes) => Some(Handle::from_bytes(bytes)),
            Err(_) => None,
        },
        Err(_) => None,
    }
}

async fn perform_search(query: String) -> Result<Vec<SearchResult>, String> {
    let url = format!(
        "http://127.0.0.1:56727/search?q={}&provider=myanimelist",
        query
    );
    reqwest::get(url)
        .await
        .map_err(|e| e.to_string())?
        .json()
        .await
        .map_err(|e| e.to_string())
}

fn save_rpc(dir: String, raw: &str, title: String, url: String, img: String, rew: bool) {
    let mut lines: Vec<String> = raw.lines().map(|s| s.to_string()).collect();
    let updates = vec![
        ("title", title),
        ("url", url),
        ("image_url", img),
        ("rewatching", if rew { "1" } else { "0" }.to_string()),
    ];

    for (key, val) in updates {
        let prefix = format!("{}=", key);
        if let Some(idx) = lines.iter().position(|l| l.starts_with(&prefix)) {
            lines[idx] = format!("{}{}", prefix, val);
        } else {
            lines.push(format!("{}{}", prefix, val));
        }
    }

    let _ = fs::write(format!("{}/.rpc", dir), lines.join("\n"));
}

fn clean_dir_name(path: &str) -> String {
    let base = std::path::Path::new(path)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("");

    let mut result = String::new();
    let mut in_bracket = 0;
    let mut in_paren = 0;

    for c in base.chars() {
        match c {
            '[' => in_bracket += 1,
            ']' => in_bracket -= 1,
            '(' => in_paren += 1,
            ')' => in_paren -= 1,
            _ => {
                if in_bracket <= 0 && in_paren <= 0 {
                    result.push(c);
                }
            }
        }
        in_bracket = in_bracket.max(0);
        in_paren = in_paren.max(0);
    }

    result.split_whitespace().collect::<Vec<_>>().join(" ")
}
