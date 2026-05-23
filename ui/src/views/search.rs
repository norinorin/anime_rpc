use crate::app::AnimeRpc;
use crate::components::{icon, toggler};
use crate::constants::{colours, layout, typography};
use crate::styles::{self, ColorExt, TogglerStyle};
use crate::types::{Message, SearchMessage, SearchProvider, SearchResult, View, ViewMessage};
use iced::border::Radius;
use iced::widget::{Id, Space, button, column, container, row, scrollable, text, text_input};
use iced::{Alignment, Background, Center, Color, Element, Font, Length, Padding};

pub fn result_card<'a, Message: Clone + 'a>(
    result: &'a SearchResult,
    img_widget: Element<'a, Message>,
    is_hovered: bool,
) -> Element<'a, Message> {
    let title_text = text(&result.title)
        .size(typography::BODY_SIZE)
        .font(Font {
            weight: iced::font::Weight::Bold,
            ..Default::default()
        })
        .color(Color::WHITE)
        .width(Length::Fill);

    let score_el = if let Some(score) = result.score {
        let normalised = score as f32 / 100.0;
        let score_color = if is_hovered {
            Color::WHITE
        } else {
            Color::interpolate(colours::RED, colours::GREEN, normalised / 10.)
        };

        text(format!("{:.2} ★", normalised))
            .size(typography::BODY_SIZE)
            .font(Font {
                weight: iced::font::Weight::Bold,
                ..Default::default()
            })
            .color(score_color)
    } else {
        text("N/A")
            .size(typography::BODY_SIZE)
            .color(if is_hovered {
                Color::WHITE
            } else {
                colours::TEXT_DARK_MUTED
            })
    };

    let top_row = row![title_text, score_el]
        .spacing(layout::SPACING)
        .align_y(Alignment::Start);

    let default_text_color = if is_hovered {
        Color::WHITE
    } else {
        colours::TEXT_MUTED
    };

    let mut metadata_items: Vec<Element<'a, Message>> = vec![];
    if let Some(f) = &result.media_format {
        metadata_items.push(
            text(f.as_str())
                .size(typography::CAPTION_SIZE)
                .color(default_text_color)
                .into(),
        );
    }
    if let Some(y) = result.year {
        metadata_items.push(
            text(y.to_string())
                .size(typography::CAPTION_SIZE)
                .color(default_text_color)
                .into(),
        );
    }
    if let Some(s) = &result.status {
        metadata_items.push(
            text(s.as_str())
                .size(typography::CAPTION_SIZE)
                .color(if is_hovered {
                    Color::WHITE
                } else {
                    s.accent_colour()
                })
                .into(),
        );
    }

    let metadata_row = row(metadata_items)
        .spacing(layout::S_SPACING)
        .width(Length::Fill);

    let provider_text = text(SearchProvider::from_url(&result.url).display_name())
        .size(typography::STATUS_SIZE)
        .font(Font {
            weight: iced::font::Weight::Bold,
            ..Default::default()
        })
        .color(default_text_color);

    let bottom_row = row![metadata_row, provider_text].align_y(Alignment::End);

    container(
        row![
            container(img_widget)
                .width(Length::Fixed(48.0))
                .height(Length::Fixed(72.0))
                .style(|_| container::Style {
                    background: Some(Background::Color(colours::SOFT_DARK)),
                    ..Default::default()
                }),
            column![top_row, Space::new().height(Length::Fill), bottom_row]
                .height(Length::Fixed(72.0))
                .width(Length::Fill)
        ]
        .spacing(layout::L_SPACING)
        .align_y(Alignment::Center),
    )
    .padding(layout::S_SPACING)
    .into()
}

pub fn view<'a>(state: &'a AnimeRpc) -> Element<'a, Message> {
    let results = state
        .search
        .results
        .get(&state.search.form.selected_provider)
        .map(|v| v.as_slice())
        .unwrap_or(&[]);
    let results_len = results.len();
    let results_content: Element<'_, Message> = if results.is_empty() {
        container(text("No results").color(colours::TEXT_DARK_MUTED))
            .width(Length::Fill)
            .height(Length::Fixed(100.0))
            .align_x(Center)
            .align_y(Center)
            .into()
    } else {
        column(
            results
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
                        styles::get_ghost_button_style(Color::WHITE, colours::TEXT_MUTED);

                    let radius: iced::border::Radius = if results_len == 1 {
                        layout::XL_SPACING.into()
                    } else if i == 0 {
                        Radius {
                            top_left: layout::XL_SPACING,
                            top_right: layout::XL_SPACING,
                            ..Default::default()
                        }
                    } else if i == results_len - 1 {
                        Radius {
                            bottom_right: layout::XL_SPACING,
                            bottom_left: layout::XL_SPACING,
                            ..Default::default()
                        }
                    } else {
                        0.0.into()
                    };

                    button(result_card(res, img_widget, is_hovered))
                        .width(Length::Fill)
                        .padding([layout::SPACING, layout::XL_SPACING])
                        .style(move |theme, status| {
                            let mut style = if is_hovered {
                                styles::primary_button_style(theme, status)
                            } else {
                                ghost_style(theme, status)
                            };
                            style.border.radius = radius;
                            style
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
        .padding(0.)
        .width(Length::Fill)
        .height(Length::Fill);

    let next_provider = match state.search.form.selected_provider {
        SearchProvider::MyAnimeList => SearchProvider::AniList,
        SearchProvider::AniList => SearchProvider::MyAnimeList,
    };

    let progress = state.view.provider_anim.interpolate(0., 1., state.now);
    let mal_color = Color::interpolate(colours::TEXT_MUTED, colours::TEXT_DARK_MUTED, progress);
    let anilist_color = Color::interpolate(colours::TEXT_DARK_MUTED, colours::TEXT_MUTED, progress);

    let root = column![
        row![
            button(icon('\u{e5e0}').size(28))
                .style(styles::get_ghost_button_style(
                    Color::WHITE,
                    colours::TEXT_MUTED
                ))
                .on_press(Message::View(ViewMessage::Switch(View::Config))),
            text("Search").size(34).font(Font {
                weight: iced::font::Weight::Bold,
                ..Default::default()
            }),
            Space::new().width(Length::Fill),
            row![
                text("MAL").size(typography::CAPTION_SIZE).color(mal_color),
                toggler(
                    state.view.provider_anim.interpolate(0., 1., state.now),
                    Message::Search(SearchMessage::ProviderSelected(next_provider)),
                    TogglerStyle {
                        bg_off: SearchProvider::MyAnimeList.accent_colour(),
                        bg_on: SearchProvider::AniList.accent_colour(),
                        ..Default::default()
                    }
                ),
                text("AniList")
                    .size(typography::CAPTION_SIZE)
                    .color(anilist_color),
            ]
            .spacing(layout::S_SPACING)
            .align_y(Center)
        ]
        .spacing(layout::L_SPACING)
        .align_y(Center)
        .padding([0., layout::L_SPACING + layout::S_SPACING]),
        column![
            row![
                text_input("Search title...", &state.search.form.query)
                    .id(Id::new("search_bar"))
                    .on_input(|res| Message::Search(SearchMessage::QueryChanged(res)))
                    .on_submit(Message::Search(SearchMessage::Perform))
                    .style(styles::search_input_style)
                    .padding([layout::L_SPACING, layout::L_SPACING + layout::S_SPACING]),
                button(icon('\u{e8b6}').size(layout::XL_SPACING))
                    .on_press(Message::Search(SearchMessage::Perform))
                    .style(styles::get_ghost_button_style(
                        Color::WHITE,
                        colours::TEXT_MUTED
                    ))
                    .padding({
                        Padding {
                            left: layout::L_SPACING,
                            right: 0.,
                            bottom: layout::L_SPACING,
                            top: layout::L_SPACING,
                        }
                    })
            ]
            .spacing(layout::S_SPACING)
            .align_y(Center)
        ]
        .spacing(layout::S_SPACING)
        .padding([0., layout::L_SPACING + layout::S_SPACING]),
        scrollable(column![card, Space::new().height(Length::Fill)].padding([0., layout::SPACING]))
            .id(Id::new("search_scroll"))
            .direction(styles::slim_scrollbar())
            .height(Length::Fill),
    ]
    .spacing(layout::XL_SPACING)
    .padding(Padding::new(0.).top(40).bottom(20));

    container(root)
        .style(styles::black_container_style)
        .width(Length::Fill)
        .height(Length::Fill)
        .into()
}
