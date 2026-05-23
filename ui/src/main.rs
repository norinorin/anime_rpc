#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod api;
mod app;
mod components;
mod constants;
mod history;
mod sse;
mod styles;
mod types;
mod utils;
mod views;

use app::AnimeRpc;
use iced::{Size, window};

pub fn main() -> iced::Result {
    iced::application::timed(
        AnimeRpc::init,
        AnimeRpc::update,
        AnimeRpc::subscription,
        AnimeRpc::view,
    )
    .antialiasing(true)
    .title("Anime RPC")
    .font(include_bytes!(
        "../assets/MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf"
    ))
    .window(window::Settings {
        size: Size::new(constants::WINDOW_WIDTH, constants::WINDOW_HEIGHT),
        resizable: false,
        visible: true,
        ..Default::default()
    })
    .theme(|_state: &AnimeRpc| iced::Theme::Dark)
    .run()
}
