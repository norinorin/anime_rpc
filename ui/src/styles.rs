use iced::widget::button::{self, Status};
use iced::widget::{container, scrollable, text_input};
use iced::{Background, Border, Color, Shadow, Theme, color};

use crate::constants::{colours, layout};

pub fn primary_button_style(_theme: &Theme, status: Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(colours::SELECTION)),
        text_color: Color::WHITE,
        border: Border {
            radius: layout::INNER_COLUMN_SPACING.into(),
            width: 0.,
            color: Color::TRANSPARENT,
        },
        shadow: Shadow::default(),
        ..Default::default()
    };

    match status {
        Status::Active => base,
        Status::Hovered => button::Style {
            background: Some(Background::Color(color!(96, 165, 250))),
            ..base
        },
        Status::Pressed => button::Style {
            background: Some(Background::Color(color!(37, 99, 235))),
            ..base
        },
        Status::Disabled => button::Style {
            background: Some(Background::Color(color!(75, 85, 99))),
            text_color: color!(156, 163, 175),
            ..base
        },
    }
}

pub fn success_button_style(_theme: &Theme, status: Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(colours::GREEN)),
        text_color: Color::WHITE,
        border: Border {
            radius: layout::INNER_COLUMN_SPACING.into(),
            width: 0.,
            color: Color::TRANSPARENT,
        },
        shadow: Shadow::default(),
        ..Default::default()
    };

    match status {
        Status::Active => base,
        Status::Hovered => button::Style {
            background: Some(Background::Color(color!(52, 211, 153))),
            ..base
        },
        Status::Pressed => button::Style {
            background: Some(Background::Color(color!(5, 150, 105))),
            ..base
        },
        Status::Disabled => base,
    }
}

pub fn danger_button_style(_theme: &Theme, status: Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(colours::RED)),
        text_color: Color::WHITE,
        border: Border {
            radius: layout::INNER_COLUMN_SPACING.into(),
            width: 0.,
            color: Color::TRANSPARENT,
        },
        shadow: Shadow::default(),
        ..Default::default()
    };

    match status {
        Status::Active => base,
        Status::Hovered => button::Style {
            background: Some(Background::Color(color!(248, 113, 113))),
            ..base
        },
        Status::Pressed => button::Style {
            background: Some(Background::Color(color!(220, 38, 38))),
            ..base
        },
        Status::Disabled => base,
    }
}

pub fn secondary_button_style(_theme: &Theme, status: Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(Color::TRANSPARENT)),
        text_color: colours::TEXT_MUTED,
        border: Border {
            radius: layout::INNER_COLUMN_SPACING.into(),
            width: 1.,
            color: colours::TEXT_DARK_MUTED,
        },
        shadow: Shadow::default(),
        ..Default::default()
    };

    match status {
        Status::Active => base,
        Status::Hovered => button::Style {
            background: Some(Background::Color(color!(55, 65, 81))),
            text_color: Color::WHITE,
            ..base
        },
        Status::Pressed => button::Style {
            background: Some(Background::Color(color!(31, 41, 55))),
            ..base
        },
        Status::Disabled => base,
    }
}

pub fn card_container_style(_theme: &Theme) -> container::Style {
    container::Style {
        background: Some(Background::Color(colours::SOFT_DARK)),
        text_color: Some(Color::WHITE),
        border: Border {
            radius: layout::XL_SPACING.into(),
            width: 0.,
            color: Color::TRANSPARENT,
        },
        shadow: Default::default(),
        ..Default::default()
    }
}

pub fn black_container_style(_theme: &Theme) -> container::Style {
    container::Style {
        background: Some(Background::Color(Color::BLACK)),
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
        placeholder: colours::TEXT_DARK_MUTED,
        selection: colours::SELECTION,
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
        background: Background::Color(colours::SOFT_DARK),
        border: Border {
            radius: (layout::XL_SPACING - layout::S_SPACING).into(),
            width: 0.,
            color: Color::TRANSPARENT,
        },
        icon: Color::WHITE,
        value: Color::WHITE,
        placeholder: colours::TEXT_DARK_MUTED,
        selection: colours::SELECTION,
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

pub trait ColorExt {
    fn interpolate(from: Self, to: Self, progress: f32) -> Self;
}

impl ColorExt for Color {
    fn interpolate(from: Self, to: Self, progress: f32) -> Self {
        Self {
            r: from.r + (to.r - from.r) * progress,
            g: from.g + (to.g - from.g) * progress,
            b: from.b + (to.b - from.b) * progress,
            a: from.a + (to.a - from.a) * progress,
        }
    }
}
// Hmm, maybe we should make this a function that takes
// in theme and toggle status for when we need to integrate theme.
// For now let's keep it stupid simple.
pub struct TogglerStyle {
    pub bg_off: Color,
    pub bg_on: Color,
    pub knob_off: Color,
    pub knob_on: Color,
}

impl Default for TogglerStyle {
    fn default() -> Self {
        Self {
            bg_off: colours::TEXT_DARK_MUTED,
            bg_on: colours::SELECTION,
            knob_off: colours::SOFT_DARK,
            knob_on: Color::WHITE,
        }
    }
}
