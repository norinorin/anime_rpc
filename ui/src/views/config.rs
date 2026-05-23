use crate::app::{AnimeRpc, SseState};
use crate::components::{divider, dropdown, icon, toggler, underlined_input};
use crate::constants::{colours, layout, typography};
use crate::styles::{self, TogglerStyle};
use crate::types::{IoMessage, Message, RpcMessage, SaveStatus, View, ViewMessage};
use crate::utils::clean_dir_name;
use iced::widget::text::LineHeight;
use iced::widget::{Space, button, column, container, row, scrollable, text, text_input};
use iced::{Center, Color, Element, Font, Length, Padding};

pub fn view(state: &AnimeRpc) -> Element<'_, Message> {
    let is_active = state
        .rpc
        .active_id
        .as_ref()
        .and_then(|id| state.rpc.pollers.get(id))
        .is_some_and(|p| p.active);

    let active_poller = state
        .rpc
        .active_id
        .as_ref()
        .and_then(|id| state.rpc.pollers.get(id));

    let mut sorted_pollers: Vec<_> = state.rpc.pollers.iter().collect();
    sorted_pollers.sort_by_key(|&(id, _)| state.rpc.active_id.as_ref() != Some(id));
    let dropdown_options = sorted_pollers.into_iter().map(|(id, p)| {
        let is_current = state.rpc.active_id.as_ref() == Some(id);
        let base_colour = if p.active {
            Color::WHITE
        } else {
            colours::TEXT_MUTED
        };

        let mut btn = button(
            row![
                container(
                    text("●")
                        .size(typography::INDICATOR_DOT_SIZE)
                        .color(if is_current {
                            colours::GREEN
                        } else {
                            colours::TEXT_DARK_MUTED
                        })
                        .line_height(LineHeight::Relative(1.0))
                        .center()
                )
                // nudge this down so it aligns with the row
                // with this we probably don't even need line_height() and center()?
                .padding(Padding::new(0.).top(3.)),
                text(&p.display_name)
                    .size(typography::BODY_SIZE)
                    .line_height(LineHeight::Relative(1.0))
                    .center(),
                Space::new().width(Length::Fill),
                container(
                    text(if let Some(dir) = &p.filedir {
                        format!("Playing {}", clean_dir_name(dir))
                    } else {
                        "Waiting".into()
                    })
                    .size(typography::STATUS_SIZE)
                    .color(colours::TEXT_MUTED)
                    .line_height(LineHeight::Relative(1.0))
                    .center()
                )
                .padding(Padding::new(0.).top(2.)),
            ]
            .spacing(layout::SPACING)
            .align_y(Center),
        )
        .width(Length::Fill)
        .height(35.)
        .style(styles::get_ghost_button_style(
            base_colour,
            colours::SELECTION,
        ))
        .padding([layout::SPACING, layout::L_SPACING]);

        if p.active {
            btn = btn.on_press(Message::Io(IoMessage::PollerSelected(id.clone())));
        }

        btn.into()
    });

    let poller_section = dropdown(
        "Poller",
        active_poller.map_or("Select...", |p| &p.display_name),
        state.view.poller_dropdown_open,
        state
            .view
            .poller_dropdown_anim
            .interpolate(0.0, 1.0, state.now),
        Message::View(ViewMessage::TogglePollerDropdown),
        dropdown_options,
        35.,
    );

    let mut media_label_row = row![
        text("Media URL")
            .size(typography::CAPTION_SIZE)
            .color(colours::TEXT_MUTED),
    ]
    .align_y(Center)
    .spacing(layout::SPACING);

    if !state.rpc.form.url.is_empty() {
        let open_btn = button(icon('\u{e89e}').size(typography::STATUS_SIZE))
            .style(styles::get_ghost_button_style(
                colours::TEXT_MUTED,
                colours::SELECTION,
            ))
            .padding(0.)
            .on_press(Message::OpenUrlClicked(state.rpc.form.url.clone()));
        media_label_row = media_label_row.push(open_btn);
    }

    let search_btn = button(icon('\u{e8b6}').size(24))
        .style(styles::get_ghost_button_style(
            colours::TEXT_MUTED,
            colours::SELECTION,
        ))
        .padding([0., layout::SPACING]);

    let search_btn = if is_active {
        search_btn.on_press(Message::View(ViewMessage::Switch(View::Search)))
    } else {
        search_btn
    };

    let image_preview: Element<'_, Message> = if !state.rpc.form.image_url.is_empty()
        && let Some(img) = state.rpc.image_cache.peek(&state.rpc.form.image_url)
    {
        column![
            divider(),
            text("Image preview")
                .width(Length::Fill)
                .size(typography::CAPTION_SIZE)
                .align_x(Center)
                .color(colours::TEXT_MUTED),
            container(img.view(layout::IMAGE_PREVIEW_WIDTH, state.now))
                .width(Length::Fill)
                .align_x(Center)
        ]
        .spacing(layout::INNER_COLUMN_SPACING)
        .into()
    } else {
        Space::new().height(0).width(0).into()
    };

    let (save_text, save_style): (
        &str,
        fn(&iced::Theme, iced::widget::button::Status) -> iced::widget::button::Style,
    ) = match state.view.save_status {
        SaveStatus::Idle => ("Save Changes", styles::primary_button_style),
        SaveStatus::Saved => ("✔ Saved", styles::success_button_style),
        SaveStatus::Failed => ("Failed to Save", styles::danger_button_style),
    };

    let card_content = column![
        poller_section,
        divider(),
        underlined_input(
            "Media title",
            if state.rpc.title_placeholder.is_empty() {
                "Title..."
            } else {
                &state.rpc.title_placeholder
            },
            &state.rpc.form.title,
            |res| Message::Rpc(RpcMessage::TitleChanged(res))
        ),
        column![
            media_label_row,
            row![
                text_input("URL...", &state.rpc.form.url)
                    .on_input(|res| Message::Rpc(RpcMessage::UrlChanged(res)))
                    .on_submit(Message::OpenUrlClicked(state.rpc.form.url.clone()))
                    .style(styles::transparent_text_input_style)
                    .padding([layout::SPACING, 0.]),
                search_btn
            ]
            .align_y(Center),
            divider(),
        ]
        .spacing(layout::S_SPACING),
        underlined_input("Image URL", "URL...", &state.rpc.form.image_url, |res| {
            Message::Rpc(RpcMessage::ImageUrlChanged(res))
        }),
        row![
            text("Rewatching")
                .width(Length::Fill)
                .size(typography::BODY_SIZE),
            toggler(
                state.view.rewatching_anim.interpolate(0.0, 1.0, state.now),
                Message::Rpc(RpcMessage::ToggleRewatching(!state.rpc.form.rewatching)),
                TogglerStyle::default()
            )
        ]
        .align_y(Center),
        image_preview
    ]
    .spacing(layout::VERTICAL_SPACING)
    .padding(layout::XL_SPACING)
    .height(Length::Fill);

    let card = container(card_content)
        .style(styles::card_container_style)
        .width(Length::Fill)
        .height(Length::Fill);

    let status_indicator: Element<'_, Message> = match state.sse {
        SseState::Connecting { .. } => row![
            text("●")
                .size(typography::INDICATOR_DOT_SIZE)
                .color(colours::TEXT_DARK_MUTED),
            text(" Connecting to daemon...")
                .size(typography::STATUS_SIZE)
                .color(colours::TEXT_MUTED)
        ],
        SseState::Connected => row![
            text("●")
                .size(typography::INDICATOR_DOT_SIZE)
                .color(colours::GREEN),
            text(" Daemon active")
                .size(typography::STATUS_SIZE)
                .color(colours::TEXT_MUTED)
        ],
        SseState::WaitingToReconnect { seconds_left, .. } => row![
            text("●")
                .size(typography::INDICATOR_DOT_SIZE)
                .color(colours::RED),
            text(format!(
                " Daemon offline. Reconnecting in {}...",
                seconds_left
            ))
            .size(typography::STATUS_SIZE)
            .color(colours::RED),
            button(
                text("Connect now")
                    .size(typography::INDICATOR_DOT_SIZE)
                    .font(Font {
                        weight: iced::font::Weight::Bold,
                        ..Default::default()
                    })
            )
            .on_press(Message::Io(IoMessage::ReconnectClicked))
            .padding(0)
            .style(styles::get_ghost_button_style(
                colours::TEXT_MUTED,
                Color::WHITE
            ))
        ],
    }
    .align_y(iced::alignment::Vertical::Center)
    .spacing(layout::SPACING)
    .padding([layout::S_SPACING, layout::XL_SPACING])
    .into();

    let root = column![
        status_indicator,
        container(text("Anime RPC").size(typography::TITLE_SIZE).font(Font {
            weight: iced::font::Weight::Bold,
            ..Default::default()
        }))
        .padding([0., layout::XL_SPACING]),
        Space::new().height(layout::VERTICAL_SPACING),
        scrollable(
            column![card, Space::new().height(Length::Fill),].padding([0., layout::SPACING])
        )
        .direction(styles::slim_scrollbar())
        .height(Length::Fill),
        row![
            button(text(save_text).align_x(iced::alignment::Horizontal::Center))
                .on_press(Message::Io(IoMessage::SaveClicked))
                .style(save_style)
                .width(Length::Fill),
        ]
        .spacing(layout::VERTICAL_SPACING)
        .padding([layout::VERTICAL_SPACING, layout::XL_SPACING])
    ]
    .padding([layout::ROOT_PADDING_TOP, 0])
    .height(Length::Fill);

    container(root)
        .style(styles::black_container_style)
        .width(Length::Fill)
        .height(Length::Fill)
        .into()
}
