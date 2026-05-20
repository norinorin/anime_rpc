use crate::app::AnimeRpc;
use crate::components::{divider, underlined_input};
use crate::constants::{colours, layout, typography};
use crate::styles::{self, hex, secondary_button_style};
use crate::types::{DaemonStatus, IoMessage, Message, RpcMessage, SaveStatus, View, ViewMessage};
use iced::widget::{
    Space, button, column, container, image, pick_list, row, text, text_input, toggler,
};
use iced::{Center, Element, Font, Length};

pub fn view(state: &AnimeRpc) -> Element<'_, Message> {
    let poller_list: Vec<String> = state
        .rpc
        .pollers
        .values()
        .map(|p| {
            format!(
                "{} {} | {}",
                if p.active { "●" } else { "○" },
                p.display_name,
                if p.active { "Active" } else { "Waiting" }
            )
        })
        .collect();

    let poller_select = pick_list(poller_list, state.rpc.active_id.clone(), |res| {
        Message::Io(IoMessage::PollerSelected(res))
    })
    .placeholder("Select...")
    .width(Length::Fill);

    let is_active = state
        .rpc
        .active_id
        .as_ref()
        .and_then(|id| state.rpc.pollers.get(id))
        .is_some_and(|p| p.active);

    let search_btn = button("🔍").style(secondary_button_style);
    let search_btn = if is_active {
        search_btn.on_press(Message::View(ViewMessage::Switch(View::Search)))
    } else {
        search_btn
    };

    let open_btn = button("🌐").style(secondary_button_style);
    let open_btn = if !state.rpc.url.is_empty() {
        open_btn.on_press(Message::Rpc(RpcMessage::OpenUrlClicked))
    } else {
        open_btn
    };

    let image_preview: Element<'_, Message> = if !state.rpc.image_url.is_empty()
        && let Some(handle) = state.rpc.image_cache.peek(&state.rpc.image_url)
    {
        column![
            divider(),
            text("Image preview")
                .width(Length::Fill)
                .size(typography::CAPTION_SIZE)
                .align_x(Center)
                .color(hex(colours::TEXT_MUTED)),
            container(image(handle).width(Length::Fixed(layout::IMAGE_PREVIEW_WIDTH)))
                .width(Length::Fill)
                .align_x(Center),
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
        row![
            text("Poller")
                .width(Length::Fill)
                .size(typography::BODY_SIZE),
            poller_select
        ]
        .align_y(Center),
        divider(),
        underlined_input(
            "Media title",
            &state.rpc.title_placeholder,
            &state.rpc.title,
            |res| Message::Rpc(RpcMessage::TitleChanged(res))
        ),
        column![
            row![
                column![
                    text("Media URL")
                        .size(typography::CAPTION_SIZE)
                        .color(hex(colours::TEXT_MUTED)),
                    text_input("URL...", &state.rpc.url)
                        .on_input(|res| Message::Rpc(RpcMessage::UrlChanged(res)))
                        .on_submit(Message::Rpc(RpcMessage::OpenUrlClicked))
                        .style(styles::transparent_text_input_style)
                        .padding([layout::SPACING, 0.]),
                ],
                row![open_btn, search_btn].spacing(layout::SPACING)
            ]
            .spacing(layout::VERTICAL_SPACING),
            divider(),
        ]
        .spacing(layout::INNER_COLUMN_SPACING),
        underlined_input("Image URL", "URL...", &state.rpc.image_url, |res| {
            Message::Rpc(RpcMessage::ImageUrlChanged(res))
        }),
        row![
            text("Rewatching")
                .width(Length::Fill)
                .size(typography::BODY_SIZE),
            toggler(state.rpc.rewatching)
                .on_toggle(|res| Message::Rpc(RpcMessage::ToggleRewatching(res)))
        ]
        .align_y(Center),
        image_preview
    ]
    .spacing(layout::VERTICAL_SPACING);

    let card = container(card_content)
        .style(styles::card_container_style)
        .padding(layout::XL_SPACING)
        .width(Length::Fill);

    let status_indicator: Element<'_, Message> = match state.view.daemon_status {
        DaemonStatus::Checking => row![
            text("●")
                .size(typography::INDICATOR_DOT_SIZE)
                .color(hex(colours::TEXT_DARK_MUTED)),
            text(" Connecting to daemon...")
                .size(typography::STATUS_SIZE)
                .color(hex(colours::TEXT_MUTED))
        ],
        DaemonStatus::Connected => row![
            text("●")
                .size(typography::INDICATOR_DOT_SIZE)
                .color(hex(colours::GREEN)),
            text(" Daemon active")
                .size(typography::STATUS_SIZE)
                .color(hex(colours::TEXT_MUTED))
        ],
        DaemonStatus::Disconnected => row![
            text("●")
                .size(typography::INDICATOR_DOT_SIZE)
                .color(hex(colours::RED)),
            text(" Daemon offline")
                .size(typography::STATUS_SIZE)
                .color(hex(colours::RED))
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
        card,
        Space::new().height(Length::Fill),
        row![
            button(text(save_text).align_x(iced::alignment::Horizontal::Center))
                .on_press(Message::Io(IoMessage::SaveClicked))
                .style(save_style)
                .width(Length::Fill),
            button(text("Refresh").align_x(iced::alignment::Horizontal::Center))
                .on_press(Message::Io(IoMessage::RefreshClicked))
                .style(styles::primary_button_style)
                .width(Length::Shrink)
        ]
        .spacing(layout::VERTICAL_SPACING)
        .padding([0., layout::XL_SPACING])
    ]
    .padding([layout::ROOT_PADDING_TOP, 0]);

    container(root)
        .style(styles::black_container_style)
        .width(Length::Fill)
        .height(Length::Fill)
        .into()
}
