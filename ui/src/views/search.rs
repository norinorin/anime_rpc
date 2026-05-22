use crate::app::AnimeRpc;
use crate::components::icon;
use crate::constants::{colours, layout, typography};
use crate::styles::{self, hex};
use crate::types::{Message, SearchMessage, SearchProvider, View, ViewMessage};
use iced::widget::{Id, Space, button, column, container, row, scrollable, text, text_input};
use iced::{Alignment, Center, Color, Element, Font, Length, Padding};

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
                .enumerate()
                .map(|(i, res)| {
                    let img_widget: Element<'_, Message> = state
                        .rpc
                        .image_cache
                        .peek(&res.image_url)
                        .map(|img| img.view(50.0, state.now))
                        .unwrap_or_else(|| Space::new().into());
                    let is_hovered = state.search.hovered_index == Some(i);
                    let ghost_style =
                        styles::get_ghost_button_style(Color::WHITE, hex(colours::TEXT_MUTED));
                    button(
                        row![
                            img_widget,
                            column![
                                text(&res.title).size(15).font(Font {
                                    weight: iced::font::Weight::Bold,
                                    ..Default::default()
                                }),
                                text(SearchProvider::from_url(&res.url).display_name())
                                    .size(typography::STATUS_SIZE)
                                    .color(if is_hovered {
                                        Color::WHITE
                                    } else {
                                        hex(colours::TEXT_MUTED)
                                    }),
                            ]
                            .spacing(layout::XS_SPACING)
                        ]
                        .spacing(layout::L_SPACING)
                        .align_y(Alignment::Center),
                    )
                    .width(Length::Fill)
                    .padding([layout::SPACING, layout::L_SPACING])
                    .style(move |theme, status| {
                        if is_hovered {
                            styles::primary_button_style(theme, status)
                        } else {
                            ghost_style(theme, status)
                        }
                    })
                    .on_press(Message::Search(SearchMessage::ResultSelected(res.clone())))
                    .into()
                })
                .collect::<Vec<Element<Message>>>(),
        )
        .spacing(layout::S_SPACING)
        .into()
    };

    let card = container(results_content)
        .style(styles::card_container_style)
        .padding(0)
        .width(Length::Fill)
        .height(Length::Fill);

    let provider_toggles = container(
        row(SearchProvider::ALL.iter().map(|&provider| {
            let is_active = state.search.selected_provider == provider;
            let ghost_style =
                styles::get_ghost_button_style(Color::WHITE, hex(colours::TEXT_MUTED));

            button(
                text(provider.display_name())
                    .size(typography::CAPTION_SIZE)
                    .width(Length::Fill)
                    .align_x(iced::alignment::Horizontal::Center),
            )
            .width(Length::Fill)
            .padding([layout::S_SPACING, 0.])
            .style(move |theme, status| {
                if is_active {
                    styles::primary_button_style(theme, status)
                } else {
                    ghost_style(theme, status)
                }
            })
            .on_press(Message::Search(SearchMessage::ProviderSelected(provider)))
            .into()
        }))
        .spacing(layout::S_SPACING),
    )
    .width(Length::Fill)
    .padding([layout::L_SPACING, layout::L_SPACING + layout::S_SPACING]);

    let root = column![
        row![
            button(icon('\u{e5e0}').size(28))
                .style(styles::get_ghost_button_style(
                    Color::WHITE,
                    hex(colours::TEXT_MUTED)
                ))
                .on_press(Message::View(ViewMessage::Switch(View::Config))),
            text("Search").size(34).font(Font {
                weight: iced::font::Weight::Bold,
                ..Default::default()
            })
        ]
        .spacing(layout::L_SPACING)
        .align_y(Center)
        .padding([0., layout::L_SPACING]),
        column![
            provider_toggles,
            row![
                text_input("Search title...", &state.search.query)
                    .id(Id::new("search_bar"))
                    .on_input(|res| Message::Search(SearchMessage::QueryChanged(res)))
                    .on_submit(Message::Search(SearchMessage::Perform))
                    .style(styles::search_input_style)
                    .padding([layout::L_SPACING, layout::L_SPACING + layout::S_SPACING]),
                button(icon('\u{e8b6}').size(layout::XL_SPACING))
                    .on_press(Message::Search(SearchMessage::Perform))
                    .style(styles::get_ghost_button_style(
                        Color::WHITE,
                        hex(colours::TEXT_MUTED)
                    ))
                    .padding([layout::L_SPACING, layout::L_SPACING + layout::S_SPACING])
            ]
            .spacing(layout::S_SPACING)
            .align_y(Center)
        ]
        .spacing(layout::S_SPACING)
        .padding([0., layout::L_SPACING + layout::S_SPACING]),
        scrollable(column![card, Space::new().height(Length::Fill)])
            .id(Id::new("search_scroll"))
            .direction(styles::slim_scrollbar())
            .height(Length::Fill),
    ]
    .spacing(layout::XL_SPACING)
    .padding(Padding::new(0.).top(40).right(0).bottom(20).left(0));

    container(root)
        .style(styles::black_container_style)
        .width(Length::Fill)
        .height(Length::Fill)
        .into()
}
