use iced::widget::canvas::{self, Canvas, Frame, Geometry, Path, Program, Stroke};
use iced::{Color, Element, Length, Theme};
use std::f32::consts::{PI, TAU};

pub struct LoadingSpinner {
    radius: f32,
    progress: f32,
}

impl LoadingSpinner {
    pub fn view(radius: f32, progress: f32) -> Element<'static, crate::types::Message> {
        Canvas::new(LoadingSpinner { radius, progress })
            .width(Length::Fixed(60.0))
            .height(Length::Fixed(60.0))
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
        let center = frame.center();
        let eased_progress = ease_in_out_cubic(self.progress);
        let start_angle = iced::Radians(eased_progress * TAU);
        let end_angle = iced::Radians(start_angle.0 + PI * 1.5);
        let arc = Path::new(|b| {
            b.arc(canvas::path::Arc {
                center,
                radius: self.radius,
                start_angle,
                end_angle,
            });
        });
        frame.stroke(
            &arc,
            Stroke::default()
                .with_color(Color::from_rgb(1.0, 1.0, 1.0))
                .with_width(3.0),
        );
        vec![frame.into_geometry()]
    }
}
