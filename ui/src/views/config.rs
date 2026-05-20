use crate::app::AnimeRpc;
use crate::components::{divider, underlined_input};
use crate::styles::{self, hex, secondary_button_style};
use crate::types::{IoMessage, Message, RpcMessage, SaveStatus, View, ViewMessage};
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
                .size(12)
                .align_x(Center)
                .color(hex(0x888888)),
            container(image(handle).width(Length::Fixed(200.0)))
                .width(Length::Fill)
                .align_x(Center),
        ]
        .spacing(10)
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
        row![text("Poller").width(Length::Fill).size(16), poller_select].align_y(Center),
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
                    text("Media URL").size(13).color(hex(0x888888)),
                    text_input("URL...", &state.rpc.url)
                        .on_input(|res| Message::Rpc(RpcMessage::UrlChanged(res)))
                        .on_submit(Message::Rpc(RpcMessage::OpenUrlClicked))
                        .style(styles::transparent_text_input_style)
                        .padding([8, 0]),
                ],
                row![open_btn, search_btn].spacing(8)
            ]
            .spacing(10),
            divider(),
        ]
        .spacing(4),
        underlined_input("Image URL", "URL...", &state.rpc.image_url, |res| {
            Message::Rpc(RpcMessage::ImageUrlChanged(res))
        }),
        row![
            text("Rewatching").width(Length::Fill).size(16),
            toggler(state.rpc.rewatching)
                .on_toggle(|res| Message::Rpc(RpcMessage::ToggleRewatching(res)))
        ]
        .align_y(Center),
        image_preview
    ]
    .spacing(10);

    let card = container(card_content)
        .style(styles::card_container_style)
        .padding(24)
        .width(Length::Fill);

    let root = column![
        container(text("Anime RPC").size(34).font(Font {
            weight: iced::font::Weight::Bold,
            ..Default::default()
        }))
        .padding([0., 24.]),
        Space::new().height(10),
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
        .spacing(10)
        .padding([0, 24])
    ]
    .padding([40., 0.]);

    container(root)
        .style(styles::black_container_style)
        .width(Length::Fill)
        .height(Length::Fill)
        .into()
}
