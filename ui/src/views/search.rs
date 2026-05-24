use crate::app::AnimeRpc;
use crate::components::{icon, rounded_scrollable_card, space_between_column, toggler};
use crate::constants::{colours, layout, typography};
use crate::styles::{self, ColorExt, TogglerStyle};
use crate::types::{Message, SearchMessage, SearchProvider, SearchResult, View, ViewMessage};
use iced::border::Radius;
use iced::widget::{Id, Space, button, column, container, row, stack, svg, text, text_input};
use iced::{Alignment, Background, Center, Color, Element, Font, Length, Padding};

pub fn result_card<'a>(
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
        .padding(0.)
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

    let provider = SearchProvider::from_url(&result.url);
    let provider_logo_size = 20.0;

    let provider_display = button(
        row![
            container(svg(provider.logo()))
                .width(provider_logo_size)
                .height(provider_logo_size)
                .center(provider_logo_size),
            container(icon('\u{e89e}').size(typography::BODY_SIZE))
                .padding(Padding::new(0.).top(2.))
        ]
        .align_y(Center)
        .spacing(layout::SPACING),
    )
    .style(styles::get_ghost_button_style(
        colours::TEXT_MUTED,
        colours::SELECTION,
    ))
    .padding(0.)
    .width(Length::Shrink)
    .height(Length::Shrink)
    .on_press(Message::OpenUrlClicked(result.url.clone()));

    let image_width = 48.0;
    let image_height = 72.0;
    let bottom_row = row![metadata_row, provider_display].align_y(Center);

    container(
        row![
            container(img_widget)
                .width(image_width)
                .height(image_height)
                .style(|_| container::Style {
                    background: Some(Background::Color(colours::SOFT_DARK)),
                    ..Default::default()
                }),
            space_between_column(top_row, bottom_row)
                .spacing(layout::INNER_COLUMN_SPACING)
                .min_height(image_height),
        ]
        .spacing(layout::L_SPACING)
        .align_y(Alignment::Start),
    )
    .height(Length::Shrink)
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

    let is_connected = state.sse.is_connected();

    // TODO: move this to components.rs
    // Also TODO: use Option instead of an empty Space everywhere else
    let stale_banner: Option<Element<'_, Message>> =
        (!is_connected && !results.is_empty()).then(|| {
            container(
                row![
                    icon('\u{e002}').size(16),
                    text(format!(
                        "Offline — showing cached {} results",
                        state.search.form.selected_provider.display_name()
                    ))
                ]
                .spacing(layout::S_SPACING)
                .align_y(Center),
            )
            .width(Length::Fill)
            .style(|_theme| container::Style {
                background: Some(colours::SURFACE_WARNING.scale_alpha(0.8).into()),
                ..Default::default()
            })
            .align_x(Center)
            .padding(layout::S_SPACING)
            .into()
        });

    let results_content: Element<'_, Message> = if results.is_empty() {
        container(
            text(if is_connected {
                format!(
                    "No results on {}",
                    state.search.form.selected_provider.display_name()
                )
            } else {
                "Daemon is offline".into()
            })
            .color(colours::TEXT_DARK_MUTED),
        )
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

    let next_provider = match state.search.form.selected_provider {
        SearchProvider::MyAnimeList => SearchProvider::AniList,
        SearchProvider::AniList => SearchProvider::MyAnimeList,
    };

    let progress = state.view.provider_anim.interpolate(0., 1., state.now);
    let mal_color = Color::interpolate(colours::TEXT_MUTED, colours::TEXT_DARK_MUTED, progress);
    let anilist_color = Color::interpolate(colours::TEXT_DARK_MUTED, colours::TEXT_MUTED, progress);

    let search_bar = text_input("Search title...", &state.search.form.query)
        .id(Id::new("search_bar"))
        .on_input(|res| Message::Search(SearchMessage::QueryChanged(res)))
        .style(styles::search_input_style)
        .padding([layout::L_SPACING, layout::L_SPACING + layout::S_SPACING]);

    let search_btn = button(icon('\u{e8b6}').size(layout::XL_SPACING))
        .style(styles::get_ghost_button_style(
            if is_connected {
                Color::WHITE
            } else {
                colours::TEXT_MUTED
            },
            colours::TEXT_MUTED,
        ))
        .padding({
            Padding {
                left: layout::L_SPACING,
                right: 0.,
                bottom: layout::L_SPACING,
                top: layout::L_SPACING,
            }
        });

    let (search_bar, search_btn) = if is_connected {
        (
            search_bar.on_submit(Message::Search(SearchMessage::Perform)),
            search_btn.on_press(Message::Search(SearchMessage::Perform)),
        )
    } else {
        (search_bar, search_btn)
    };

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
            row![search_bar, search_btn]
                .spacing(layout::S_SPACING)
                .align_y(Center)
        ]
        .spacing(layout::S_SPACING)
        .padding([0., layout::L_SPACING + layout::S_SPACING]),
        rounded_scrollable_card(results_content, |s| s.id(Id::new("search_scroll"))),
    ]
    .spacing(layout::XL_SPACING)
    .padding(Padding::new(0.).top(40).bottom(20));

    stack![
        container(root)
            .style(styles::black_container_style)
            .width(Length::Fill)
            .height(Length::Fill),
        stale_banner,
    ]
    .into()
}
