mod animations;
mod api;
mod app;
mod constants;
mod types;
mod utils;
mod views;

use app::AnimeRpc;
use iced::{Size, window};

pub fn main() -> iced::Result {
    iced::application(AnimeRpc::init, AnimeRpc::update, AnimeRpc::view)
        .subscription(AnimeRpc::subscription)
        .title("Anime RPC")
        .window(window::Settings {
            size: Size::new(constants::WINDOW_WIDTH, constants::WINDOW_HEIGHT),
            resizable: false,
            ..Default::default()
        })
        .theme(|_state: &AnimeRpc| iced::Theme::Dark)
        .run()
}
