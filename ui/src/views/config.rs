use crate::app::AnimeRpc;
use crate::components::{divider, underlined_input};
use crate::styles::{self, hex, secondary_button_style};
use crate::types::{Message, View};
use iced::widget::{
    Space, button, column, container, image, pick_list, row, text, text_input, toggler,
};
use iced::{Center, Element, Font, Length};

pub fn view(state: &AnimeRpc) -> Element<'_, Message> {
    let poller_list: Vec<String> = state
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

    let poller_select = pick_list(
        poller_list,
        state.active_id.clone(),
        Message::PollerSelected,
    )
    .placeholder("Select...")
    .width(Length::Fill);

    let is_active = state
        .active_id
        .as_ref()
        .and_then(|id| state.pollers.get(id))
        .is_some_and(|p| p.active);

    let search_btn = button("🔍").style(secondary_button_style);
    let search_btn = if is_active {
        search_btn.on_press(Message::SwitchView(View::Search))
    } else {
        search_btn
    };

    let image_preview: Element<'_, Message> = if !state.image_url.is_empty()
        && let Some(handle) = state.image_cache.peek(&state.image_url)
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

    let card_content = column![
        row![text("Poller").width(Length::Fill).size(16), poller_select].align_y(Center),
        divider(),
        underlined_input(
            "Media title",
            &state.title_placeholder,
            &state.title,
            Message::TitleChanged
        ),
        column![
            row![
                column![
                    text("Media URL").size(13).color(hex(0x888888)),
                    text_input("URL...", &state.url)
                        .on_input(Message::UrlChanged)
                        .style(styles::transparent_text_input_style)
                        .padding([8, 0]),
                ],
                search_btn
            ]
            .spacing(10),
            divider(),
        ]
        .spacing(4),
        underlined_input(
            "Image URL",
            "URL...",
            &state.image_url,
            Message::ImageUrlChanged
        ),
        row![
            text("Rewatching").width(Length::Fill).size(16),
            toggler(state.rewatching).on_toggle(Message::ToggleRewatching)
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
            button(text("Save Changes").align_x(iced::alignment::Horizontal::Center))
                .on_press(Message::SaveClicked)
                .style(styles::success_button_style)
                .width(Length::Fill),
            button(text("Refresh").align_x(iced::alignment::Horizontal::Center))
                .on_press(Message::RefreshClicked)
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
