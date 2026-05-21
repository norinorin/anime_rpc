use iced::widget::canvas::{self, Canvas, Frame, Geometry, Path, Program, Stroke, Style};
use iced::widget::image::Handle;
use iced::widget::{Space, button, column, container, image, row, text, text_input};
use iced::{Alignment, Animation, Background, Color, Element, Length, Radians, Theme};
use std::f32::consts::{PI, TAU};
use std::time::Instant;

use crate::constants::{colours, layout, typography};
use crate::styles::{self, hex};
use crate::types::Message;

pub struct LoadingSpinner {
    radius: f32,
    stroke_width: f32,
    progress: f32,
}

impl LoadingSpinner {
    pub fn view(
        progress: f32,
        radius: f32,
        size: f32,
        stroke_width: f32,
    ) -> Element<'static, crate::types::Message> {
        Canvas::new(LoadingSpinner {
            radius,
            stroke_width,
            progress,
        })
        .width(Length::Fixed(size))
        .height(Length::Fixed(size))
        .into()
    }
}

impl<Message> Program<Message> for LoadingSpinner {
    type State = ();

    fn draw(
        &self,
        _state: &Self::State,
        renderer: &iced::Renderer,
        _theme: &Theme,
        bounds: iced::Rectangle,
        _cursor: iced::mouse::Cursor,
    ) -> Vec<Geometry> {
        let mut frame = Frame::new(renderer, bounds.size());

        // bypass damage tracking
        let bg_bounds = Path::rectangle(iced::Point::ORIGIN, bounds.size());
        frame.fill(&bg_bounds, Color::TRANSPARENT);

        let base_angle = self.progress * TAU * 1.25;
        let t = self.progress * 2.0;
        let (start_offset, end_offset) = if t < 1.0 {
            (0.0, t * 0.75 * TAU)
        } else {
            ((t - 1.0) * 0.75 * TAU, 0.75 * TAU)
        };
        let min_length = PI * 0.1;
        let start_angle = base_angle + start_offset;
        let end_angle = base_angle + end_offset + min_length;

        let center = frame.center();
        let arc = Path::new(|b| {
            b.arc(canvas::path::Arc {
                center,
                radius: self.radius,
                start_angle: Radians(start_angle),
                end_angle: Radians(end_angle),
            });
        });

        // FIXME: is there a way to improve AA?
        // feathering pass
        frame.stroke(
            &arc,
            Stroke {
                // FIXME: make colour customisable
                style: Style::Solid(Color::from_rgba(1., 1., 1., 0.3)),
                width: self.stroke_width + 1.5,
                line_cap: canvas::LineCap::Round,
                ..Stroke::default()
            },
        );
        // actual stroke
        frame.stroke(
            &arc,
            Stroke {
                style: Style::Solid(Color::from_rgb(1., 1., 1.)),
                width: self.stroke_width,
                line_cap: canvas::LineCap::Round,
                ..Stroke::default()
            },
        );
        vec![frame.into_geometry()]
    }
}

pub fn divider() -> Element<'static, Message> {
    container(Space::new().width(Length::Fill).height(Length::Fixed(1.0)))
        .style(|_theme| container::Style {
            background: Some(Background::Color(hex(colours::DIVIDER))),
            ..Default::default()
        })
        .into()
}

pub fn underlined_input<'a>(
    label: &'a str,
    placeholder: &'a str,
    value: &'a str,
    on_change: impl Fn(String) -> Message + 'a,
) -> Element<'a, Message> {
    column![
        text(label).size(13).color(hex(colours::TEXT_MUTED)),
        text_input(placeholder, value)
            .on_input(on_change)
            .style(styles::transparent_text_input_style)
            .padding([layout::SPACING, 0.]),
        divider(),
    ]
    .spacing(4)
    .into()
}

pub fn dropdown<'a, Message: Clone + 'a>(
    title: &'a str,
    active_text: &'a str,
    is_open: bool,
    on_toggle: Message,
    options: impl IntoIterator<Item = Element<'a, Message>>,
) -> Element<'a, Message> {
    let selector_btn = button(
        row![
            text(active_text).width(Length::Fill),
            text(if is_open { "▲" } else { "▼" })
                .size(layout::SPACING)
                .color(hex(colours::TEXT_MUTED))
        ]
        .align_y(Alignment::Center),
    )
    .on_press(on_toggle)
    .style(styles::secondary_button_style)
    .padding([layout::SPACING, layout::L_SPACING])
    .width(Length::Fill);

    let mut section = column![
        row![
            text(title).width(Length::Fill).size(typography::BODY_SIZE),
            selector_btn
        ]
        .align_y(Alignment::Center)
    ]
    .spacing(layout::SPACING);

    if is_open {
        let opts_column =
            column(options.into_iter().collect::<Vec<_>>()).spacing(layout::XS_SPACING);
        section = section.push(
            container(opts_column)
                .width(Length::Fill)
                .padding([layout::S_SPACING, 0.]),
        );
    }

    section.into()
}

#[derive(Debug, Clone)]
pub enum CachedImage {
    Pending(Animation<bool>),
    Failed,
    Ready(Handle),
}

impl CachedImage {
    pub fn new_pending(now: Instant) -> Self {
        Self::Pending(
            Animation::new(false)
                .duration(std::time::Duration::from_millis(2000))
                .easing(iced::animation::Easing::EaseInOutCubic)
                .repeat_forever()
                .go(true, now),
        )
    }

    pub fn is_animating(&self) -> bool {
        matches!(self, Self::Pending(_))
    }

    pub fn view(&self, size: f32, now: Instant) -> Element<'_, Message> {
        match self {
            Self::Ready(handle) => image(handle).width(Length::Fixed(size)).into(),
            Self::Pending(anim) => {
                LoadingSpinner::view(anim.interpolate(0.0, 1.0, now), 10., 50., 3.)
            }
            Self::Failed => text("Failed to load")
                .size(typography::STATUS_SIZE)
                .color(hex(colours::TEXT_DARK_MUTED))
                .into(),
        }
    }
}
