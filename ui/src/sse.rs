use crate::{constants::API_BASE_URL, types::SseMessage};
use futures_util::SinkExt;
use iced::{Subscription, stream};

pub fn listen() -> Subscription<SseMessage> {
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
    struct SseId;

    Subscription::run_with(SseId, |_id| {
        stream::channel(
            100,
            |mut output: iced::futures::channel::mpsc::Sender<SseMessage>| async move {
                let client = reqwest::Client::new();
                let url = format!("{}/pollers/events", API_BASE_URL);

                let connection = async {
                    let res = client
                        .get(&url)
                        .header("Accept", "text/event-stream")
                        .send()
                        .await
                        .ok()?;

                    if !res.status().is_success() {
                        return None;
                    }

                    Some(res)
                }
                .await;

                match connection {
                    Some(mut response) => {
                        let _ = output.send(SseMessage::Connected).await;

                        let mut buffer = String::new();

                        while let Ok(Some(chunk)) = response.chunk().await {
                            let Ok(chunk_str) = std::str::from_utf8(&chunk) else {
                                continue;
                            };

                            buffer.push_str(chunk_str);

                            while let Some(idx) = buffer.find("\n\n") {
                                let event_block = buffer[..idx].to_owned();

                                buffer.drain(..idx + 2);

                                for json_data in event_block
                                    .lines()
                                    .filter_map(|line| line.strip_prefix("data: "))
                                {
                                    let _ =
                                        output.send(SseMessage::Data(json_data.to_owned())).await;
                                }
                            }
                        }

                        let _ = output.send(SseMessage::Disconnected).await;
                    }
                    None => {
                        // Sleep for a bit so it doesn't flicker since the connection
                        // fails instantly
                        tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                        let _ = output.send(SseMessage::Disconnected).await;
                    }
                }

                // Wait indefinitely 'til iced drops us
                iced::futures::future::pending().await
            },
        )
    })
}
