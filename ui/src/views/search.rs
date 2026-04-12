use crate::animations::LoadingSpinner;
use crate::app::AnimeRpc;
use crate::types::{Message, View};
use iced::widget::{button, column, container, image, row, scrollable, text, text_input};
use iced::{Alignment, Center, Element, Length};

pub fn view(state: &AnimeRpc) -> Element<'_, Message> {
    let results = scrollable(
        column(
            state
                .search_results
                .iter()
                .map(|res| {
                    let img_widget: Element<'_, Message> =
                        if let Some(handle) = state.image_cache.peek(&res.image_url) {
                            container(image(handle.clone()).width(Length::Fixed(60.0)))
                                .width(Length::Fixed(60.0))
                                .align_x(Center)
                                .into()
                        } else {
                            container(LoadingSpinner::view(state.elapsed_time, 2., 15., 60., 3.))
                                .width(Length::Fixed(60.))
                                .height(Length::Fixed(60.))
                                .align_x(Center)
                                .align_y(Center)
                                .into()
                        };

                    button(
                        row![
                            img_widget,
                            column![
                                text(&res.title).size(16).font(iced::Font {
                                    weight: iced::font::Weight::Bold,
                                    ..Default::default()
                                }),
                                text("MyAnimeList").size(12).color([0.5, 0.5, 0.5]),
                            ]
                            .spacing(5)
                        ]
                        .spacing(15)
                        .align_y(Alignment::Center)
                        .padding(5),
                    )
                    .width(Length::Fill)
                    .on_press(Message::ResultSelected(res.clone()))
                    .into()
                })
                .collect::<Vec<Element<Message>>>(),
        )
        .spacing(10),
    );

    column![
        button("<- Back").on_press(Message::SwitchView(View::Config)),
        row![
            text_input("Search anime...", &state.search_query)
                .on_input(Message::SearchQueryChanged)
                .on_submit(Message::PerformSearch),
            button("Go").on_press(Message::PerformSearch)
        ]
        .spacing(10),
        results,
    ]
    .spacing(15)
    .padding(20)
    .into()
}
