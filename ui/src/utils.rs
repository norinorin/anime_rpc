use std::fs;
use tray_icon::Icon;

pub fn load_icon() -> Icon {
    let (icon_rgba, icon_width, icon_height) = {
        let image_bytes = include_bytes!("../assets/icon.png");
        let image = ::image::load_from_memory(image_bytes)
            .expect("Failed to parse embedded icon")
            .into_rgba8();

        let (width, height) = image.dimensions();
        (image.into_raw(), width, height)
    };

    Icon::from_rgba(icon_rgba, icon_width, icon_height).expect("Failed to create icon")
}
pub async fn load_rpc(dir: String) -> Result<String, String> {
    let path = format!("{}/.rpc", dir);
    fs::read_to_string(path).map_err(|e| e.to_string())
}

pub fn save_rpc(dir: String, raw: &str, title: String, url: String, img: String, rew: bool) {
    let mut lines: Vec<String> = raw.lines().map(|s| s.to_string()).collect();
    let updates = vec![
        ("title", title),
        ("url", url),
        ("image_url", img),
        ("rewatching", if rew { "1" } else { "0" }.to_string()),
    ];

    for (key, val) in updates {
        let prefix = format!("{}=", key);
        if let Some(idx) = lines.iter().position(|l| l.starts_with(&prefix)) {
            lines[idx] = format!("{}{}", prefix, val);
        } else {
            lines.push(format!("{}{}", prefix, val));
        }
    }

    let _ = fs::write(format!("{}/.rpc", dir), lines.join("\n"));
}

pub fn clean_dir_name(path: &str) -> String {
    let base = std::path::Path::new(path)
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("");

    let mut result = String::new();
    let (mut in_bracket, mut in_paren) = (0, 0);

    for c in base.chars() {
        match c {
            '[' => in_bracket += 1,
            ']' => in_bracket -= 1,
            '(' => in_paren += 1,
            ')' => in_paren -= 1,
            _ if in_bracket <= 0 && in_paren <= 0 => result.push(c),
            _ => {}
        }
        in_bracket = in_bracket.max(0);
        in_paren = in_paren.max(0);
    }

    result.split_whitespace().collect::<Vec<_>>().join(" ")
}
