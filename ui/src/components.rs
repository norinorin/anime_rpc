use iced::advanced::layout::{Limits, Node};
use iced::advanced::mouse::Cursor;
use iced::advanced::renderer;
use iced::advanced::widget::{Tree, Widget};
use iced::advanced::{Clipboard, Layout, Shell};
use iced::event::Event;
use iced::widget::canvas::{self, Canvas, Frame, Geometry, Path, Program, Stroke, Style};
use iced::widget::image::Handle;
use iced::widget::{
    Space, button, column, container, image, mouse_area, row, scrollable, space, stack, text,
    text_input,
};
use iced::{
    Alignment, Animation, Background, Color, Element, Length, Padding, Radians, Theme, mouse,
};
use iced::{Point, Rectangle, Size};
use std::f32::consts::{PI, TAU};
use std::time::Instant;

use crate::constants::{ICON_FONT, colours, layout, typography};
use crate::styles::{self, ColorExt, TogglerStyle};
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
            background: Some(Background::Color(colours::DIVIDER)),
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
        text(label)
            .size(typography::CAPTION_SIZE)
            .color(colours::TEXT_MUTED),
        text_input(placeholder, value)
            .on_input(on_change)
            .style(styles::transparent_text_input_style)
            .padding([layout::SPACING, 0.]),
        divider(),
    ]
    .spacing(layout::S_SPACING)
    .into()
}

pub fn dropdown<'a, Message: Clone + 'a>(
    title: &'a str,
    active_text: &'a str,
    is_open: bool,
    progress: f32,
    on_toggle: Message,
    options: impl IntoIterator<Item = Element<'a, Message>>,
    row_height: f32,
) -> Element<'a, Message> {
    let selector_btn = button(
        row![
            text(active_text).width(Length::Fill),
            text(if is_open { "▲" } else { "▼" })
                .size(layout::SPACING)
                .color(colours::TEXT_MUTED)
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
    ];

    if progress > 0.0 {
        let options_vec: Vec<_> = options.into_iter().collect();
        let target_height = options_vec.len() as f32 * row_height + layout::SPACING;
        let opts_column = column(options_vec).spacing(layout::XS_SPACING);
        let opts_container = container(opts_column).width(Length::Fill).padding(Padding {
            top: layout::SPACING,
            bottom: 0.,
            right: 0.,
            left: 0.,
        });
        let viewport = scrollable(opts_container)
            .direction(scrollable::Direction::Vertical(
                scrollable::Scrollbar::new()
                    .width(0)
                    .scroller_width(0)
                    .margin(0),
            ))
            .height(Length::Fixed(target_height * progress));
        section = section.push(viewport);
    }

    section.into()
}

pub fn toggler<'a, Message: Clone + 'a>(
    progress: f32,
    on_toggle: Message,
    style: TogglerStyle,
) -> Element<'a, Message> {
    let width = 34.0;
    let height = 18.0;
    let circle_size = 12.0;
    let padding = 3.0;
    let current_bg_colour = Color::interpolate(style.bg_off, style.bg_on, progress);
    let current_knob_colour = Color::interpolate(style.knob_off, style.knob_on, progress);

    let bg = container(space())
        .width(Length::Fixed(width))
        .height(Length::Fixed(height))
        .style(move |_theme| container::Style {
            background: Some(Background::Color(current_bg_colour)),
            border: iced::Border {
                radius: (height / 2.0).into(),
                ..Default::default()
            },
            ..Default::default()
        });

    let circle_x = padding + (width - circle_size - padding * 2.0) * progress;

    let knob = container(space())
        .width(Length::Fixed(circle_size))
        .height(Length::Fixed(circle_size))
        .style(move |_theme| container::Style {
            background: Some(Background::Color(current_knob_colour)),
            border: iced::Border {
                radius: (circle_size / 2.0).into(),
                ..Default::default()
            },
            ..Default::default()
        });

    let knob_positioned = container(knob)
        .width(Length::Fixed(width))
        .height(Length::Fixed(height))
        .padding(Padding {
            top: padding,
            bottom: 0.0,
            left: circle_x,
            right: 0.0,
        });

    mouse_area(stack![bg, knob_positioned])
        .interaction(mouse::Interaction::Pointer)
        .on_press(on_toggle)
        .into()
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
                .color(colours::TEXT_DARK_MUTED)
                .into(),
        }
    }
}

pub fn icon<'a>(unicode: char) -> iced::widget::Text<'a> {
    text(unicode.to_string())
        .font(ICON_FONT)
        .align_x(iced::alignment::Horizontal::Center)
        .align_y(iced::alignment::Vertical::Center)
}

pub struct SpaceBetweenColumn<'a, Message, Theme, Renderer> {
    top: Element<'a, Message, Theme, Renderer>,
    bottom: Element<'a, Message, Theme, Renderer>,
    min_height: f32,
    spacing: f32,
}

// I'm missing the .min_height() feature, which I need for the
// result cards used in View::Search.
//
// Basically what I'm trying to do is set a minimum height while
// letting the container/column grow as needed.
//
// I've tried different combinations to no avail:
// 1. Tried Length::Fill on both spacer in between the 2 widgets
//    and the container that wraps the 3. While this maintains
//    the min_height, it clips the bottom widget when the top widget
//    grows/expands downward.
// 2. Tried Length::Shrink on the container and set a fixed spacer.
//    This obviously still looks nice and doesn't clip the bottom widget,
//    yet it doesn't do what I want since now the spacer is static
//    instead of growing/shrinking on demand.
// 3. Tried guesstimating the font height and width, but it relies on
//    assuming the average char width. Somehow that works out but it's
//    ugly as fuck and is likely to break sooner or later when I implement
//    the --preferred-lang which lets the user pick native titles (CJK).
//
// This implementation is way cleaner than my last attempt, but still not
// sure if this is optimal. I'd be so happy if there's a higher level
// interface for what I'm trying to achieve here.
//
// TL;DR I want a flex column with a vertical `justify-content: space-between`
// with a min-height and also height set to `fit-content`.
// Keeping it really simple since I only need it for exactly 2 widgets.
// Maybe I can just keep nesting with a macro or something, but that's for later.
impl<'a, Message, Theme, Renderer> Widget<Message, Theme, Renderer>
    for SpaceBetweenColumn<'a, Message, Theme, Renderer>
where
    Renderer: renderer::Renderer,
{
    fn size(&self) -> Size<Length> {
        Size {
            width: Length::Fill,
            height: Length::Shrink,
        }
    }

    fn layout(&mut self, tree: &mut Tree, renderer: &Renderer, limits: &Limits) -> Node {
        let max_width = limits.max().width;
        let child_limits = limits.loose().max_width(max_width);

        let top_node =
            self.top
                .as_widget_mut()
                .layout(&mut tree.children[0], renderer, &child_limits);

        let mut bottom_node =
            self.bottom
                .as_widget_mut()
                .layout(&mut tree.children[1], renderer, &child_limits);

        let top_size = top_node.size();
        let bottom_size = bottom_node.size();

        let intrinsic_height = top_size.height + bottom_size.height + self.spacing;
        let final_height = intrinsic_height.max(self.min_height);

        bottom_node.move_to_mut(Point::new(0.0, final_height - bottom_size.height));
        // Should I actually pass max_width or whichever is bigger between top and bottom?
        Node::with_children(
            Size::new(max_width, final_height),
            vec![top_node, bottom_node],
        )
    }

    fn children(&self) -> Vec<Tree> {
        vec![Tree::new(&self.top), Tree::new(&self.bottom)]
    }

    fn diff(&self, tree: &mut Tree) {
        tree.diff_children(&[&self.top, &self.bottom]);
    }

    fn draw(
        &self,
        tree: &Tree,
        renderer: &mut Renderer,
        theme: &Theme,
        style: &renderer::Style,
        layout: Layout<'_>,
        cursor: Cursor,
        viewport: &Rectangle,
    ) {
        let mut children = layout.children();
        self.top.as_widget().draw(
            &tree.children[0],
            renderer,
            theme,
            style,
            children.next().unwrap(),
            cursor,
            viewport,
        );
        self.bottom.as_widget().draw(
            &tree.children[1],
            renderer,
            theme,
            style,
            children.next().unwrap(),
            cursor,
            viewport,
        );
    }

    fn operate(
        &mut self,
        state: &mut Tree,
        layout: Layout<'_>,
        renderer: &Renderer,
        operation: &mut dyn iced::advanced::widget::Operation,
    ) {
        let mut children = layout.children();
        self.top.as_widget_mut().operate(
            &mut state.children[0],
            children.next().unwrap(),
            renderer,
            operation,
        );
        self.bottom.as_widget_mut().operate(
            &mut state.children[1],
            children.next().unwrap(),
            renderer,
            operation,
        );
    }

    fn update(
        &mut self,
        state: &mut Tree,
        event: &Event,
        layout: Layout<'_>,
        cursor: Cursor,
        renderer: &Renderer,
        clipboard: &mut dyn Clipboard,
        shell: &mut Shell<'_, Message>,
        viewport: &Rectangle,
    ) {
        let mut children = layout.children();
        self.top.as_widget_mut().update(
            &mut state.children[0],
            event,
            children.next().unwrap(),
            cursor,
            renderer,
            clipboard,
            shell,
            viewport,
        );
        self.bottom.as_widget_mut().update(
            &mut state.children[1],
            event,
            children.next().unwrap(),
            cursor,
            renderer,
            clipboard,
            shell,
            viewport,
        );
    }

    fn mouse_interaction(
        &self,
        state: &Tree,
        layout: Layout<'_>,
        cursor: Cursor,
        viewport: &Rectangle,
        renderer: &Renderer,
    ) -> iced::advanced::mouse::Interaction {
        let mut children = layout.children();
        let top_interaction = self.top.as_widget().mouse_interaction(
            &state.children[0],
            children.next().unwrap(),
            cursor,
            viewport,
            renderer,
        );
        let bottom_interaction = self.bottom.as_widget().mouse_interaction(
            &state.children[1],
            children.next().unwrap(),
            cursor,
            viewport,
            renderer,
        );
        top_interaction.max(bottom_interaction)
    }
}

impl<'a, Message, Theme, Renderer> From<SpaceBetweenColumn<'a, Message, Theme, Renderer>>
    for Element<'a, Message, Theme, Renderer>
where
    Message: 'a,
    Theme: 'a,
    Renderer: renderer::Renderer + 'a,
{
    fn from(content: SpaceBetweenColumn<'a, Message, Theme, Renderer>) -> Self {
        Element::new(content)
    }
}

impl<'a, Message, Theme, Renderer> SpaceBetweenColumn<'a, Message, Theme, Renderer> {
    pub fn new(
        top: impl Into<Element<'a, Message, Theme, Renderer>>,
        bottom: impl Into<Element<'a, Message, Theme, Renderer>>,
    ) -> Self {
        Self {
            top: top.into(),
            bottom: bottom.into(),
            min_height: 0.0,
            spacing: 0.0,
        }
    }

    pub fn min_height(mut self, height: f32) -> Self {
        self.min_height = height;
        self
    }

    pub fn spacing(mut self, spacing: f32) -> Self {
        self.spacing = spacing;
        self
    }
}

pub fn space_between_column<'a, Message, Theme, Renderer>(
    top: impl Into<Element<'a, Message, Theme, Renderer>>,
    bottom: impl Into<Element<'a, Message, Theme, Renderer>>,
) -> SpaceBetweenColumn<'a, Message, Theme, Renderer> {
    SpaceBetweenColumn::new(top, bottom)
}
