use std::{
    collections::BTreeSet,
    env, fs,
    path::{Path, PathBuf},
    process::Command,
};

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=assets/MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf");

    let mut unicodes = BTreeSet::new();

    scan_dir(Path::new("src"), &mut unicodes);

    let unicode_arg = unicodes
        .into_iter()
        .map(|u| format!("U+{u}"))
        .collect::<Vec<_>>()
        .join(",");

    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());

    let output_font = out_dir.join("MaterialSymbolsSubset.ttf");

    let status = Command::new("pyftsubset")
        .arg("assets/MaterialSymbolsRounded[FILL,GRAD,opsz,wght].ttf")
        .arg(format!("--unicodes={unicode_arg}"))
        .arg(format!("--output-file={}", output_font.display()))
        .status()
        .expect("failed to run pyftsubset");

    if !status.success() {
        panic!("pyftsubset failed (exit code: {:?})", status.code())
    }
}

fn scan_dir(dir: &Path, unicodes: &mut BTreeSet<String>) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };

    for entry in entries.flatten() {
        let path = entry.path();

        if path.is_dir() {
            scan_dir(&path, unicodes);
            continue;
        }

        if path.extension().and_then(|s| s.to_str()) != Some("rs") {
            continue;
        }

        println!("cargo:rerun-if-changed={}", path.display());

        let content = fs::read_to_string(&path)
            .unwrap_or_else(|e| panic!("Failed to read {:?}: {}", path, e));

        extract_icons(&content, unicodes);
    }
}

/// This only matches `icon(\\u{...})`, maybe move icons to constants.rs
/// or just do an AST parse
fn extract_icons(content: &str, unicodes: &mut BTreeSet<String>) {
    let mut rest = content;

    while let Some(start) = rest.find("icon(") {
        rest = &rest[start + 5..];
        if !rest.starts_with(['\'', '"']) || !rest[1..].starts_with("\\u{") {
            if let Some(c) = rest.chars().next() {
                rest = &rest[c.len_utf8()..];
            }
            continue;
        }

        rest = &rest[4..];

        if let Some(end) = rest.find('}') {
            let hex = &rest[..end];

            if hex.chars().all(|c| c.is_ascii_hexdigit()) {
                unicodes.insert(hex.to_uppercase());
            }

            rest = &rest[end + 1..];
        }
    }
}
