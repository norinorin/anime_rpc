use std::num::NonZeroUsize;

pub const API_BASE_URL: &str = "http://127.0.0.1:56727";
pub const ICON_PATH: &str = "assets/icon.png";

pub const WINDOW_WIDTH: f32 = 400.0;
pub const WINDOW_HEIGHT: f32 = 800.0;

pub const TICK_RATE_MS: u64 = 50;

pub fn image_cache_size() -> NonZeroUsize {
    NonZeroUsize::new(100).unwrap()
}
