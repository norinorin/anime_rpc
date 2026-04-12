use crate::app::AnimeRpc;
use crate::types::{Message, View};
use crate::utils::clean_dir_name;
use iced::widget::{
    Space, button, checkbox, column, container, image, pick_list, row, text, text_input,
};
use iced::{Center, Element, Length};

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
    .placeholder("Select Poller...")
    .width(Length::Fill);

    let is_active = state
        .active_id
        .as_ref()
        .and_then(|id| state.pollers.get(id))
        .is_some_and(|p| p.active);

    let search_btn = button("🔍");
    let search_btn = if is_active {
        search_btn.on_press(Message::SwitchView(View::Search))
    } else {
        search_btn
    };

    let title_placeholder = if let Some(filedir) = &state.active_filedir {
        clean_dir_name(filedir)
    } else {
        "Title...".to_string()
    };

    column![
        text("Available Pollers").size(18),
        poller_select,
        text("Media Title").size(14),
        text_input(&title_placeholder, &state.title).on_input(Message::TitleChanged),
        text("Media URL").size(14),
        row![
            text_input("URL...", &state.url).on_input(Message::UrlChanged),
            search_btn
        ]
        .spacing(10),
        text("Image URL").size(14),
        text_input("Image URL...", &state.image_url).on_input(Message::ImageUrlChanged),
        checkbox(state.rewatching)
            .label("Rewatching")
            .on_toggle(Message::ToggleRewatching),
        Space::new().height(Length::Fill),
        if !state.image_url.is_empty()
            && let Some(handle) = state.image_cache.peek(&state.image_url)
        {
            container(image(handle).width(Length::Fixed(200.0)))
                .width(Length::Fill)
                .align_x(Center)
        } else {
            container(Space::new().height(Length::Fill).width(Length::Fill))
        },
        Space::new().height(Length::Fill),
        row![
            button("Save Changes")
                .on_press(Message::SaveClicked)
                .style(button::success)
                .width(Length::Fill),
            button("Refresh")
                .on_press(Message::RefreshClicked)
                .style(button::primary)
                .width(Length::Shrink)
        ]
        .spacing(10)
    ]
    .spacing(12)
    .padding(20)
    .into()
}
