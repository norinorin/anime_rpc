use std::num::NonZeroUsize;

use iced::{
    Font,
    font::{Family, Stretch, Style, Weight},
};

pub const API_BASE_URL: &str = "http://127.0.0.1:56727";
pub const WINDOW_WIDTH: f32 = 400.0;
pub const WINDOW_HEIGHT: f32 = 800.0;

pub fn image_cache_size() -> NonZeroUsize {
    NonZeroUsize::new(100).unwrap()
}

pub mod layout {
    pub const ROOT_PADDING_TOP: u16 = 40;
    pub const VERTICAL_SPACING: f32 = 10.;
    pub const IMAGE_PREVIEW_WIDTH: f32 = 200.;
    pub const INNER_COLUMN_SPACING: f32 = 6.;
    pub const XL_SPACING: f32 = 24.;
    pub const L_SPACING: f32 = 12.;
    pub const SPACING: f32 = 8.;
    pub const S_SPACING: f32 = 4.;
    pub const XS_SPACING: f32 = 2.;
}

pub mod typography {
    pub const TITLE_SIZE: u32 = 34;
    pub const BODY_SIZE: u32 = 16;
    pub const CAPTION_SIZE: u32 = 13;
    pub const STATUS_SIZE: u32 = 12;
    pub const INDICATOR_DOT_SIZE: u32 = 10;
}

pub mod colours {
    use iced::{Color, color};

    pub const TEXT_MUTED: Color = color!(0x888888);
    pub const TEXT_DARK_MUTED: Color = color!(0x666666);
    pub const GREEN: Color = color!(0x10B981);
    pub const RED: Color = color!(0xEF4444);
    pub const DIVIDER: Color = color!(0x2A2A2C);
    pub const SOFT_DARK: Color = color!(0x151515);
    pub const SELECTION: Color = color!(0x3E91FF);
    pub const SURFACE_WARNING: Color = color!(0x47381C);
}

pub const ICON_FONT: Font = Font {
    family: Family::Name("Material Symbols Rounded"),
    weight: Weight::Normal,
    stretch: Stretch::Normal,
    style: Style::Normal,
};
