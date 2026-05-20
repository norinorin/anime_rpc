use crate::app::AnimeRpc;
use crate::components::LoadingSpinner;
use crate::constants::{colours, layout, typography};
use crate::styles::{self, hex};
use crate::types::{Message, SearchMessage, View, ViewMessage};
use iced::widget::{button, column, container, image, row, scrollable, text, text_input};
use iced::{Alignment, Center, Element, Font, Length, Padding};

pub fn view(state: &AnimeRpc) -> Element<'_, Message> {
    let results_content: Element<'_, Message> = if state.search.results.is_empty() {
        container(text("No results").color(hex(colours::TEXT_DARK_MUTED)))
            .width(Length::Fill)
            .height(Length::Fixed(100.0))
            .align_x(Center)
            .align_y(Center)
            .into()
    } else {
        column(
            state
                .search
                .results
                .iter()
                .map(|res| {
                    let img_widget: Element<'_, Message> =
                        if let Some(handle) = state.rpc.image_cache.peek(&res.image_url) {
                            container(image(handle.clone()).width(Length::Fixed(50.0)))
                                .width(Length::Fixed(50.0))
                                .height(Length::Fixed(50.0))
                                .align_x(Center)
                                .align_y(Center)
                                .into()
                        } else {
                            LoadingSpinner::view(state.view.elapsed_time, 1.5, 10., 50.0, 3.)
                        };

                    button(
                        row![
                            img_widget,
                            column![
                                text(&res.title).size(15).font(Font {
                                    weight: iced::font::Weight::Bold,
                                    ..Default::default()
                                }),
                                text("MyAnimeList")
                                    .size(typography::STATUS_SIZE)
                                    .color(hex(colours::TEXT_MUTED)),
                            ]
                            .spacing(layout::XS_SPACING)
                        ]
                        .spacing(layout::L_SPACING)
                        .align_y(Alignment::Center),
                    )
                    .width(Length::Fill)
                    .padding([layout::SPACING, layout::L_SPACING])
                    .style(styles::ghost_button_style)
                    .on_press(Message::Search(SearchMessage::ResultSelected(res.clone())))
                    .into()
                })
                .collect::<Vec<Element<Message>>>(),
        )
        .spacing(layout::S_SPACING)
        .into()
    };
    let results_scroll = scrollable(results_content).direction(styles::slim_scrollbar());
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
            .on_press(Message::View(ViewMessage::Switch(View::Config))),
            text("Search").size(34).font(Font {
                weight: iced::font::Weight::Bold,
                ..Default::default()
            })
        ]
        .spacing(layout::L_SPACING)
        .align_y(Center)
        .padding([0., layout::L_SPACING]),
        row![
            text_input("Search title...", &state.search.query)
                .on_input(|res| Message::Search(SearchMessage::QueryChanged(res)))
                .on_submit(Message::Search(SearchMessage::Perform))
                .style(styles::search_input_style)
                .padding([layout::L_SPACING, layout::L_SPACING + layout::S_SPACING]),
            button("Go")
                .on_press(Message::Search(SearchMessage::Perform))
                .style(styles::ghost_button_style)
                .padding([layout::L_SPACING, layout::L_SPACING + layout::S_SPACING])
        ]
        .spacing(layout::S_SPACING)
        .padding([0., layout::S_SPACING]),
        card
    ]
    .spacing(layout::L_SPACING)
    .padding(Padding::new(0.).top(40).right(0).bottom(20).left(0));
    container(root)
        .style(styles::black_container_style)
        .width(Length::Fill)
        .height(Length::Fill)
        .into()
}
