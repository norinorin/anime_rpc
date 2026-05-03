mod api;
mod app;
mod components;
mod constants;
mod curves;
mod styles;
mod types;
mod utils;
mod views;

use app::AnimeRpc;
use iced::{Size, window};

pub fn main() -> iced::Result {
    iced::application(AnimeRpc::init, AnimeRpc::update, AnimeRpc::view)
        .subscription(AnimeRpc::subscription)
        .antialiasing(true)
        .title("Anime RPC")
        .window(window::Settings {
            size: Size::new(constants::WINDOW_WIDTH, constants::WINDOW_HEIGHT),
            resizable: false,
            visible: true,
            ..Default::default()
        })
        .theme(|_state: &AnimeRpc| iced::Theme::Dark)
        .run()
}
