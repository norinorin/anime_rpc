use iced::widget::button::{self, Status};
use iced::widget::{container, text_input};
use iced::{Background, Border, Color, Shadow, Theme};

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
        background: Some(Background::Color(rgb(59.0, 130.0, 246.0))),
        text_color: Color::WHITE,
        border: Border {
            radius: 8.0.into(),
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
        background: Some(Background::Color(rgb(16.0, 185.0, 129.0))),
        text_color: Color::WHITE,
        border: Border {
            radius: 8.0.into(),
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

pub fn secondary_button_style(_theme: &Theme, status: Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(Color::TRANSPARENT)),
        text_color: rgb(156.0, 163.0, 175.0),
        border: Border {
            radius: 8.0.into(),
            width: 1.0,
            color: rgb(75.0, 85.0, 99.0),
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
        background: Some(Background::Color(hex(0x151515))),
        text_color: Some(Color::WHITE),
        border: Border {
            radius: 24.0.into(),
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
        placeholder: hex(0x666666),
        selection: hex(0x3E91FF),
    }
}

pub fn ghost_button_style(_theme: &Theme, status: button::Status) -> button::Style {
    let base = button::Style {
        background: Some(Background::Color(Color::TRANSPARENT)),
        text_color: Color::WHITE,
        border: Border::default(),
        shadow: Shadow::default(),
        ..Default::default()
    };

    match status {
        button::Status::Hovered => button::Style {
            text_color: Color::from_rgba(1.0, 1.0, 1.0, 0.5),
            ..base
        },
        button::Status::Pressed => button::Style {
            text_color: Color::from_rgba(1.0, 1.0, 1.0, 0.9),
            ..base
        },
        _ => base,
    }
}

pub fn search_input_style(_theme: &Theme, _status: text_input::Status) -> text_input::Style {
    text_input::Style {
        background: Background::Color(hex(0x151515)),
        border: Border {
            radius: 20.0.into(),
            width: 0.0,
            color: Color::TRANSPARENT,
        },
        icon: Color::WHITE,
        value: Color::WHITE,
        placeholder: hex(0x666666),
        selection: hex(0x3E91FF),
    }
}
