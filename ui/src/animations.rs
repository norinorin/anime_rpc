use iced::widget::canvas::{self, Canvas, Frame, Geometry, Path, Program, Stroke, Style};
use iced::{Color, Element, Length, Radians, Theme};
use std::f32::consts::{PI, TAU};

pub struct LoadingSpinner {
    radius: f32,
    stroke_width: f32,
    elapsed_time: f32,
    cycle_duration: f32,
}

impl LoadingSpinner {
    pub fn view(
        elapsed_time: f32,
        cycle_duration: f32,
        radius: f32,
        size: f32,
        stroke_width: f32,
    ) -> Element<'static, crate::types::Message> {
        Canvas::new(LoadingSpinner {
            radius,
            stroke_width,
            elapsed_time,
            cycle_duration,
        })
        .width(Length::Fixed(size))
        .height(Length::Fixed(size))
        .into()
    }
}

fn ease_in_out_cubic(t: f32) -> f32 {
    let t = t % 1.0;
    if t < 0.5 {
        4.0 * t * t * t
    } else {
        1.0 - (-2.0 * t + 2.0).powi(3) / 2.0
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

        let progress = (self.elapsed_time % self.cycle_duration) / self.cycle_duration;
        let base_angle = progress * TAU * 1.25;
        let t = (progress * 2.0) % 1.0;
        let ease = ease_in_out_cubic(t);
        let (start_offset, end_offset) = if progress < 0.5 {
            (0.0, ease * 0.75 * TAU)
        } else {
            (ease * 0.75 * TAU, 0.75 * TAU)
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
