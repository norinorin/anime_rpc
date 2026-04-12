use crate::app::AnimeRpc;
use crate::components::LoadingSpinner;
use crate::styles::{self, hex};
use crate::types::{Message, View};
use iced::widget::{Space, button, column, container, image, row, scrollable, text, text_input};
use iced::{Alignment, Center, Element, Font, Length, Padding};

pub fn view(state: &AnimeRpc) -> Element<'_, Message> {
    let results_content: Element<'_, Message> = if state.search_results.is_empty() {
        container(text("No results").color(hex(0x666666)))
            .width(Length::Fill)
            .height(Length::Fixed(100.0))
            .align_x(Center)
            .align_y(Center)
            .into()
    } else {
        column(
            state
                .search_results
                .iter()
                .map(|res| {
                    let img_widget: Element<'_, Message> =
                        if let Some(handle) = state.image_cache.peek(&res.image_url) {
                            container(image(handle.clone()).width(Length::Fixed(50.0)))
                                .width(Length::Fixed(50.0))
                                .height(Length::Fixed(50.0))
                                .align_x(Center)
                                .align_y(Center)
                                .into()
                        } else {
                            LoadingSpinner::view(state.elapsed_time, 1.5, 10., 50.0, 3.)
                        };

                    button(
                        row![
                            img_widget,
                            column![
                                text(&res.title).size(15).font(Font {
                                    weight: iced::font::Weight::Bold,
                                    ..Default::default()
                                }),
                                text("MyAnimeList").size(12).color(hex(0x888888)),
                            ]
                            .spacing(2)
                        ]
                        .spacing(12)
                        .align_y(Alignment::Center),
                    )
                    .width(Length::Fill)
                    .padding([8, 12])
                    .style(styles::ghost_button_style)
                    .on_press(Message::ResultSelected(res.clone()))
                    .into()
                })
                .collect::<Vec<Element<Message>>>(),
        )
        .spacing(4)
        .into()
    };
    let results_scroll = scrollable(results_content);
    let card = container(results_scroll)
        .style(styles::card_container_style)
        .padding(0)
        .width(Length::Fill)
        .height(Length::Fill);
    let root = column![
        row![
            button(text("<").size(28).font(Font {
                weight: iced::font::Weight::Light,
                ..Default::default()
            }))
            .style(styles::ghost_button_style)
            .on_press(Message::SwitchView(View::Config)),
            text("Search").size(34).font(Font {
                weight: iced::font::Weight::Bold,
                ..Default::default()
            })
        ]
        .spacing(12)
        .align_y(Center)
        .padding([0, 12]),
        row![
            text_input("Search title...", &state.search_query)
                .on_input(Message::SearchQueryChanged)
                .on_submit(Message::PerformSearch)
                .style(styles::search_input_style)
                .padding([12, 16]),
            button("Go")
                .on_press(Message::PerformSearch)
                .style(styles::ghost_button_style)
                .padding([12, 16])
        ]
        .spacing(8)
        .padding([0, 24]),
        Space::new().height(10),
        card
    ]
    .spacing(16)
    .padding(Padding::new(0.).top(40).right(0).bottom(20).left(0));
    container(root)
        .style(styles::black_container_style)
        .width(Length::Fill)
        .height(Length::Fill)
        .into()
}
