import re

import pytest

from anime_rpc.matcher import build_filename_pattern, exclude_non_media_files
from anime_rpc.pollers.base_poller import EP_TEMPLATE, EP_TITLE_TEMPLATE

# some random series to test against
ARIFURETA = [
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 01.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 02.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 03 V2.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 04 V2.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 05 V2.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 06 V2.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 07 V2.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 08 V2.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 09 V2.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 10 V2.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 11.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 12.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 13.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 14.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 15.mkv",
    "[EMBER] Arifureta Shokugyou de Sekai Saikyou S3 - 16.mkv",
]
DANDADAN = [
    "[EMBER] Dandadan - 01.mkv",
    "[EMBER] Dandadan - 02.mkv",
    "[EMBER] Dandadan - 03.mkv",
    "[EMBER] Dandadan - 04.mkv",
    "[EMBER] Dandadan - 05.mkv",
    "[EMBER] Dandadan - 06.mkv",
    "[EMBER] Dandadan - 07.mkv",
    "[EMBER] Dandadan - 08.mkv",
    "[EMBER] Dandadan - 09.mkv",
    "[EMBER] Dandadan - 10.mkv",
    "[EMBER] Dandadan - 11.mkv",
    "[EMBER] Dandadan - 12.mkv",
    ".rpc",
]
SALARYMAN = [
    "[Judas] Salaryman - S01E01v2.mkv",
    "[Judas] Salaryman - S01E02v2.mkv",
    "[Judas] Salaryman - S01E03v2.mkv",
    "[Judas] Salaryman - S01E04v2.mkv",
    "[Judas] Salaryman - S01E05v2.mkv",
    "[Judas] Salaryman - S01E06v2.mkv",
    "[Judas] Salaryman - S01E07v2.mkv",
    "[Judas] Salaryman - S01E08v2.mkv",
    "[Judas] Salaryman - S01E09v2.mkv",
    "[Judas] Salaryman - S01E10v2.mkv",
    "[Judas] Salaryman - S01E11v2.mkv",
    "[Judas] Salaryman - S01E12v2.mkv",
    ".rpc",
]
BREAKING_BAD = [
    "Breaking Bad s01e01 720p.BRrip.Sujaidr.mkv",
    "Breaking Bad s01e01 720p.BRrip.Sujaidr.srt",
    "Breaking Bad s01e02 720p.BRrip.Sujaidr.mkv",
    "Breaking Bad s01e02 720p.BRrip.Sujaidr.srt",
    "Breaking Bad s01e03 720p.BRrip.Sujaidr.mkv",
    "Breaking Bad s01e03 720p.BRrip.Sujaidr.srt",
    "Breaking Bad s01e04 720p.BRrip.Sujaidr.mkv",
    "Breaking Bad s01e04 720p.BRrip.Sujaidr.srt",
    "Breaking Bad s01e05 720p.BRrip.Sujaidr.mkv",
    "Breaking Bad s01e05 720p.BRrip.Sujaidr.srt",
    "Breaking Bad s01e06 720p.BRrip.Sujaidr.mkv",
    "Breaking Bad s01e06 720p.BRrip.Sujaidr.srt",
    "Breaking Bad s01e07 720p.BRrip.Sujaidr.mkv",
    "Breaking Bad s01e07 720p.BRrip.Sujaidr.srt",
    "sujaidr.txt",
    "Torrent downloaded from AhaShare.com.txt",
]
HOUSE_MD = [
    "House - [1x01] - Pilot.mkv",
    "House - [1x01] - Pilot.srt",
    "House - [1x02] - Paternity.mkv",
    "House - [1x02] - Paternity.srt",
    "House - [1x03] - Occam's Razor.mkv",
    "House - [1x03] - Occam's Razor.srt",
    "House - [1x04] - Maternity.mkv",
    "House - [1x04] - Maternity.srt",
    "House - [1x05] - Damned if you Do.mkv",
    "House - [1x05] - Damned if you Do.srt",
    "House - [1x06] - The Socratic Method.mkv",
    "House - [1x06] - The Socratic Method.srt",
    "House - [1x07] - Fidelity.mkv",
    "House - [1x07] - Fidelity.srt",
    "House - [1x08] - Poison.mkv",
    "House - [1x08] - Poison.srt",
    "House - [1x09] - DNR.mkv",
    "House - [1x09] - DNR.srt",
    "House - [1x10] - Histories.mkv",
    "House - [1x10] - Histories.srt",
    "House - [1x11] - Detox.mkv",
    "House - [1x11] - Detox.srt",
    "House - [1x12] - Sports Medicine.mkv",
    "House - [1x12] - Sports Medicine.srt",
    "House - [1x13] - Cursed.mkv",
    "House - [1x13] - Cursed.srt",
    "House - [1x14] - Control.mkv",
    "House - [1x14] - Control.srt",
    "House - [1x15] - Mob Rules.mkv",
    "House - [1x15] - Mob Rules.srt",
    "House - [1x16] - Heavy.mkv",
    "House - [1x16] - Heavy.srt",
    "House - [1x17] - Role Model.mkv",
    "House - [1x17] - Role Model.srt",
    "House - [1x18] - Babies & Bathwater.mkv",
    "House - [1x18] - Babies & Bathwater.srt",
    "House - [1x19] - Kids.mkv",
    "House - [1x19] - Kids.srt",
    "House - [1x20] - Love Hurts.mkv",
    "House - [1x20] - Love Hurts.srt",
    "House - [1x21] - Three Stories.mkv",
    "House - [1x21] - Three Stories.srt",
    "House - [1x22] - The Honeymoon.mkv",
    "House - [1x22] - The Honeymoon.srt",
    "Read Me.txt",
    "Torrent downloaded from AhaShare.com.txt",
    "Torrent_downloaded_from_Demonoid.com.txt",
]
THE_PUNISHER = [
    "Marvel's The Punisher S02E01 Roadhouse Blues.mkv",
    "Marvel's The Punisher S02E01 Roadhouse Blues.srt",
    "Marvel's The Punisher S02E02 Fight or Flight.mkv",
    "Marvel's The Punisher S02E02 Fight or Flight.srt",
    "Marvel's The Punisher S02E03 Trouble the Water.mkv",
    "Marvel's The Punisher S02E03 Trouble the Water.srt",
    "Marvel's The Punisher S02E04 Scar Tissue.mkv",
    "Marvel's The Punisher S02E04 Scar Tissue.srt",
    "Marvel's The Punisher S02E05 One-Eyed Jacks.mkv",
    "Marvel's The Punisher S02E05 One-Eyed Jacks.srt",
    "Marvel's The Punisher S02E06 Nakazat.mkv",
    "Marvel's The Punisher S02E06 Nakazat.srt",
    "Marvel's The Punisher S02E07 One Bad Day.mkv",
    "Marvel's The Punisher S02E07 One Bad Day.srt",
    "Marvel's The Punisher S02E08 My Brother's Keeper.mkv",
    "Marvel's The Punisher S02E08 My Brother's Keeper.srt",
    "Marvel's The Punisher S02E09 Flustercluck.mkv",
    "Marvel's The Punisher S02E09 Flustercluck.srt",
    "Marvel's The Punisher S02E10 The Dark Hearts of Men.mkv",
    "Marvel's The Punisher S02E10 The Dark Hearts of Men.srt",
    "Marvel's The Punisher S02E11 The Abyss.mkv",
    "Marvel's The Punisher S02E11 The Abyss.srt",
    "Marvel's The Punisher S02E12 Collision Course.mkv",
    "Marvel's The Punisher S02E12 Collision Course.srt",
    "Marvel's The Punisher S02E13 The Whirlwind.mkv",
    "Marvel's The Punisher S02E13 The Whirlwind.srt",
]
DUNGEON_MESHI = [
    "[MiniMTBB] Dungeon Meshi - 01 (BD 1080p) [37A7738A].mkv",
    "[MiniMTBB] Dungeon Meshi - 02 (BD 1080p) [FD85DB3B].mkv",
    "[MiniMTBB] Dungeon Meshi - 03 (BD 1080p) [DA3A7942].mkv",
    "[MiniMTBB] Dungeon Meshi - 04 (BD 1080p) [15C004DC].mkv",
    "[MiniMTBB] Dungeon Meshi - 05 (BD 1080p) [67F09F1E].mkv",
    "[MiniMTBB] Dungeon Meshi - 06 (BD 1080p) [31495666].mkv",
    "[MiniMTBB] Dungeon Meshi - 07 (BD 1080p) [CC62BE28].mkv",
    "[MiniMTBB] Dungeon Meshi - 08 (BD 1080p) [80D8938E].mkv",
    "[MiniMTBB] Dungeon Meshi - 09 (BD 1080p) [E13D3D71].mkv",
    "[MiniMTBB] Dungeon Meshi - 10 (BD 1080p) [7E21DEAC].mkv",
    "[MiniMTBB] Dungeon Meshi - 11 (BD 1080p) [3234B245].mkv",
    "[MiniMTBB] Dungeon Meshi - 12 (BD 1080p) [AA7A5258].mkv",
    "[MiniMTBB] Dungeon Meshi - 13 (BD 1080p) [8BA96863].mkv",
    "[MiniMTBB] Dungeon Meshi - 14 (BD 1080p) [D65FDE01].mkv",
    "[MiniMTBB] Dungeon Meshi - 15 (BD 1080p) [FB68E283].mkv",
    "[MiniMTBB] Dungeon Meshi - 16 (BD 1080p) [9C0F12FB].mkv",
    "[MiniMTBB] Dungeon Meshi - 17 (BD 1080p) [A43D8299].mkv",
    "[MiniMTBB] Dungeon Meshi - 18 (BD 1080p) [4D8326BF].mkv",
    "[MiniMTBB] Dungeon Meshi - 19 (BD 1080p) [D5611B67].mkv",
    "[MiniMTBB] Dungeon Meshi - 20 (BD 1080p) [4B3CBDD9].mkv",
    "[MiniMTBB] Dungeon Meshi - 21 (BD 1080p) [764EED02].mkv",
    "[MiniMTBB] Dungeon Meshi - 22 (BD 1080p) [DA2E0498].mkv",
    "[MiniMTBB] Dungeon Meshi - 23 (BD 1080p) [BF6EE038].mkv",
    "[MiniMTBB] Dungeon Meshi - 24 (BD 1080p) [0EA543A4].mkv",
]
BOKUYABA = [
    "S00E01-Bonus Dangers [8B61A9B8].mkv",
    "S02E01-We`re Searching [76B962E3].mkv",
    "S02E02-I`m Growing Up [538DD068].mkv",
    "S02E03-Yamada and Me [B8603C83].mkv",
    "S02E04-Yamada Likes... [9B9328E5].mkv",
    "S02E05-I Want to Know [449E880E].mkv",
    "S02E06-Yamada Likes Me [6545A1FC].mkv",
    "S02E07-We`re Overflowing [2948C996].mkv",
    "S02E08-We Stayed Up All Night [80762B1D].mkv",
    "S02E09-We Made a Promise [97A1860D].mkv",
    "S02E10-I Want to Be Closer to Yamada [F0A26B86].mkv",
    "S02E11-I Don`t Want to Lose [61F5526A].mkv",
    "S02E12-I Want to Tell Her [8C566F06].mkv",
    "S02E13-I, We, Fell in Love [82C41DDF].mkv",
]
SYNTHETIC_WITH_INCONSISTENT_PREFIXES_AND_SUFFIXES = [
    "Some random title - 1.mkv",
    "Some other random title - 2.mkv",
    "Title - 3v2.mkv",  # 3v2 is a noise
    "Long titleeeeeeee - 4.mkv",
]
MIZUZOKUSEI = [
    "The.Water.Magician.S01E01.The.Slow.But.Dangerous.Life..1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
    "The.Water.Magician.S01E02.Abel.the.Castaway.1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
    "The.Water.Magician.S01E03.The.Town.of.Lune.1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
    "The.Water.Magician.S01E04.Eclipses.and.Akuma.1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
    "The.Water.Magician.S01E05.The.Great.Tidal.Bore.1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
    "The.Water.Magician.S01E06.The.Sealed.Dungeon.1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
    "The.Water.Magician.S01E07.Beyond.the.Gate.1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
    "The.Water.Magician.S01E08.Unprecedented.1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
    "The.Water.Magician.S01E09.Nils.and.the.Mysterious.Town.1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
    "The.Water.Magician.S01E10.The.Open.Port.Festival.1080p.CR.WEB-DL.JPN.AAC2.0.H.264.MSubs-ToonsHub.mkv",
]
INITIAL_D_ARBITRARY_ORDER = [
    "[Judas] Initial D - Extra Stage 02 - Sentimental White.mkv",
    "[Judas] Initial D - Extra Stage 01 - Beyond The Impact Blue.mkv",
]
TOKYO_MAGNITUDE_8 = [
    "[Judas] Tokyo Magnitude 8.0 - S01E01.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E02.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E03.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E04.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E05.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E06.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E07.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E08.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E09.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E10.mkv",
    "[Judas] Tokyo Magnitude 8.0 - S01E11.mkv",
    # this is an outlier and should be ignored when
    # building the regex pattern
    "[Judas] Tokyo Magnitude 8.0 - S01S01 - Digest.mkv",
]


@pytest.mark.parametrize(
    ("name", "filenames", "pattern"),
    [
        ("arifureta", ARIFURETA, r"\- %ep%"),
        ("dandadan", DANDADAN, r"\- %ep%"),
        ("salaryman", SALARYMAN, "E%ep%"),
        ("breaking_bad", BREAKING_BAD, "e%ep%"),
        ("house_md", HOUSE_MD, r"x%ep%\] \- %title%\."),
        ("the_punisher", THE_PUNISHER, r"E%ep% %title%\."),
        ("dungeon_meshi", DUNGEON_MESHI, r"\- %ep%"),
        ("bokuyaba", BOKUYABA, r"E%ep%\-%title% \["),
        (
            "synthetic",
            SYNTHETIC_WITH_INCONSISTENT_PREFIXES_AND_SUFFIXES,
            r"%title% \- %ep%",
        ),
        ("mizuzokusei", MIZUZOKUSEI, r"E%ep%\.%title%\.1"),
        ("initial_d", INITIAL_D_ARBITRARY_ORDER, r"Stage %ep% \- %title%\."),
        ("tokyo_magnitude_8", TOKYO_MAGNITUDE_8, "E%ep%"),
    ],
)
def test_ordered_filenames(
    name: str,
    filenames: list[str],
    pattern: str,
) -> None:
    generated_pattern = build_filename_pattern(filenames)

    assert generated_pattern is not None, f"Pattern should not be None for {name}"

    # fmt: off
    expected_regex = (pattern
        .replace(*EP_TEMPLATE, 1)
        .replace(*EP_TITLE_TEMPLATE, 1)
    )
    generated_regex = (generated_pattern
        .replace(*EP_TEMPLATE, 1)
        .replace(*EP_TITLE_TEMPLATE, 1)
    )
    # fmt: on

    c_expected = re.compile(expected_regex)
    c_generated = re.compile(generated_regex)

    for filename in exclude_non_media_files(filenames):
        expected_match = c_expected.search(filename)
        generated_match = c_generated.search(filename)

        assert bool(expected_match) is bool(generated_match), (
            f"Match presence mismatch on {filename}"
        )

        if not (expected_match and generated_match):
            continue

        assert int(expected_match.group("ep")) == int(generated_match.group("ep")), (
            f"Episode mismatch on {filename}"
        )

        if "title" not in expected_match.groupdict():
            continue

        assert "title" in generated_match.groupdict(), (
            f"Generated pattern missing %title% capture on {filename}"
        )
        assert (
            expected_match.group("title").strip()
            == generated_match.group("title").strip()
        ), f"Title mismatch on {filename}"


@pytest.mark.parametrize(
    ("name", "filenames"),
    [
        ("nato", ["alpha.mkv", "beta.mkv", "gamma.mkv"]),
        ("alphabetic", ["file_a.mkv", "file_b.mkv", "file_c.mkv"]),
    ],
)
def test_filenames_with_no_numbers(name: str, filenames: list[str]) -> None:
    pattern = build_filename_pattern(filenames)

    assert pattern is None, (
        f"Sequence {name} returns a pattern (should be None instead)"
    )


def test_filenames_with_hashes_only() -> None:
    filenames = [
        "[37A7738A].mkv",
        "[FD85DB3B].mkv",
        "[DA3A7942].mkv",
        "[15C004DC].mkv",
        "[67F09F1E].mkv",
        "[31495666].mkv",
        "[CC62BE28].mkv",
        "[80D8938E].mkv",
        "[E13D3D71].mkv",
        "[7E21DEAC].mkv",
        "[3234B245].mkv",
        "[AA7A5258].mkv",
        "[8BA96863].mkv",
        "[D65FDE01].mkv",
        "[FB68E283].mkv",
        "[9C0F12FB].mkv",
        "[A43D8299].mkv",
        "[4D8326BF].mkv",
        "[D5611B67].mkv",
        "[4B3CBDD9].mkv",
        "[764EED02].mkv",
        "[DA2E0498].mkv",
        "[BF6EE038].mkv",
        "[0EA543A4].mkv",
    ]
    pattern = build_filename_pattern(filenames)
    assert pattern is None, "Pattern should return None for invalid sequences"


@pytest.mark.parametrize(
    ("name", "filenames"),
    [
        ("arifureta", ARIFURETA[:1]),
        ("dandadan", DANDADAN[:1]),
        ("salaryman", SALARYMAN[:1]),
        ("breaking_bad", BREAKING_BAD[:1]),
        ("house_md", HOUSE_MD[:1]),
        ("the_punisher", THE_PUNISHER[:1]),
        ("dungeon_meshi", DUNGEON_MESHI[:1]),
        ("bokuyaba", BOKUYABA[:1]),
        ("synthetic", SYNTHETIC_WITH_INCONSISTENT_PREFIXES_AND_SUFFIXES[:1]),
    ],
)
def test_single_filename(name: str, filenames: list[str]):
    pattern = build_filename_pattern(filenames)
    assert pattern is None, f"Pattern should be None for {name}"
