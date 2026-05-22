use iced::widget::button::{self, Status};
use iced::widget::{container, scrollable, text_input};
use iced::{Background, Border, Color, Shadow, Theme};

use crate::constants::{colours, layout};

pub fn hex(c: u32) -> Color {
    Color::from_rgba8(
        ((c >> 16) & 0xFF) as u8,
        ((c >> 8) & 0xFF) as u8,
        (c & 0xFF) as u8,
        1.0,
    )
}

fn rgb(r: f32, g: f32, b: f32) -> Color {
    Color::from_rgb(r / 255.0, g / 255.0, b / 255.0)
}

pub fn primary_button_style(_theme: &Theme, status: Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(hex(colours::SELECTION))),
        text_color: Color::WHITE,
        border: Border {
            radius: layout::INNER_COLUMN_SPACING.into(),
            width: 0.0,
            color: Color::TRANSPARENT,
        },
        shadow: Shadow::default(),
        ..Default::default()
    };

    match status {
        Status::Active => base,
        Status::Hovered => button::Style {
            background: Some(Background::Color(rgb(96.0, 165.0, 250.0))),
            ..base
        },
        Status::Pressed => button::Style {
            background: Some(Background::Color(rgb(37.0, 99.0, 235.0))),
            ..base
        },
        Status::Disabled => button::Style {
            background: Some(Background::Color(rgb(75.0, 85.0, 99.0))),
            text_color: rgb(156.0, 163.0, 175.0),
            ..base
        },
    }
}

pub fn success_button_style(_theme: &Theme, status: Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(hex(colours::GREEN))),
        text_color: Color::WHITE,
        border: Border {
            radius: layout::INNER_COLUMN_SPACING.into(),
            width: 0.0,
            color: Color::TRANSPARENT,
        },
        shadow: Shadow::default(),
        ..Default::default()
    };

    match status {
        Status::Active => base,
        Status::Hovered => button::Style {
            background: Some(Background::Color(rgb(52.0, 211.0, 153.0))),
            ..base
        },
        Status::Pressed => button::Style {
            background: Some(Background::Color(rgb(5.0, 150.0, 105.0))),
            ..base
        },
        Status::Disabled => base,
    }
}

pub fn danger_button_style(_theme: &Theme, status: Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(hex(colours::RED))),
        text_color: Color::WHITE,
        border: Border {
            radius: layout::INNER_COLUMN_SPACING.into(),
            width: 0.0,
            color: Color::TRANSPARENT,
        },
        shadow: Shadow::default(),
        ..Default::default()
    };

    match status {
        Status::Active => base,
        Status::Hovered => button::Style {
            background: Some(Background::Color(rgb(248.0, 113.0, 113.0))),
            ..base
        },
        Status::Pressed => button::Style {
            background: Some(Background::Color(rgb(220.0, 38.0, 38.0))),
            ..base
        },
        Status::Disabled => base,
    }
}

pub fn secondary_button_style(_theme: &Theme, status: Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(Color::TRANSPARENT)),
        text_color: hex(colours::TEXT_MUTED),
        border: Border {
            radius: layout::INNER_COLUMN_SPACING.into(),
            width: 1.0,
            color: hex(colours::TEXT_DARK_MUTED),
        },
        shadow: Shadow::default(),
        ..Default::default()
    };

    match status {
        Status::Active => base,
        Status::Hovered => button::Style {
            background: Some(Background::Color(rgb(55.0, 65.0, 81.0))),
            text_color: Color::WHITE,
            ..base
        },
        Status::Pressed => button::Style {
            background: Some(Background::Color(rgb(31.0, 41.0, 55.0))),
            ..base
        },
        Status::Disabled => base,
    }
}

pub fn card_container_style(_theme: &Theme) -> container::Style {
    container::Style {
        background: Some(Background::Color(hex(colours::SOFT_DARK))),
        text_color: Some(Color::WHITE),
        border: Border {
            radius: layout::XL_SPACING.into(),
            width: 0.0,
            color: Color::TRANSPARENT,
        },
        shadow: Default::default(),
        ..Default::default()
    }
}

pub fn black_container_style(_theme: &Theme) -> container::Style {
    container::Style {
        background: Some(Background::Color(hex(0x000000))),
        text_color: Some(Color::WHITE),
        ..Default::default()
    }
}

pub fn transparent_text_input_style(
    _theme: &Theme,
    _status: text_input::Status,
) -> text_input::Style {
    text_input::Style {
        background: Background::Color(Color::TRANSPARENT),
        border: Border::default(),
        icon: Color::WHITE,
        value: Color::WHITE,
        placeholder: hex(colours::TEXT_DARK_MUTED),
        selection: hex(colours::SELECTION),
    }
}

pub fn get_ghost_button_style(
    base_colour: Color,
    hover_colour: Color,
) -> impl Fn(&Theme, button::Status) -> button::Style {
    move |_theme, status| {
        let base = button::Style {
            background: Some(Background::Color(Color::TRANSPARENT)),
            border: iced::Border::default(),
            shadow: iced::Shadow::default(),
            text_color: base_colour,
            ..Default::default()
        };

        match status {
            button::Status::Hovered => button::Style {
                text_color: hover_colour,
                ..base
            },
            button::Status::Pressed => button::Style {
                text_color: Color::WHITE,
                ..base
            },
            button::Status::Disabled => button::Style {
                text_color: Color::from_rgba(base_colour.r, base_colour.g, base_colour.b, 0.5),
                ..base
            },
            _ => base,
        }
    }
}

pub fn search_input_style(_theme: &Theme, _status: text_input::Status) -> text_input::Style {
    text_input::Style {
        background: Background::Color(hex(colours::SOFT_DARK)),
        border: Border {
            radius: (layout::XL_SPACING - layout::S_SPACING).into(),
            width: 0.0,
            color: Color::TRANSPARENT,
        },
        icon: Color::WHITE,
        value: Color::WHITE,
        placeholder: hex(colours::TEXT_DARK_MUTED),
        selection: hex(colours::SELECTION),
    }
}

pub fn slim_scrollbar() -> scrollable::Direction {
    scrollable::Direction::Vertical(
        scrollable::Scrollbar::new()
            .width(layout::S_SPACING)
            .scroller_width(layout::S_SPACING)
            .margin(0),
    )
}
