import re

import pytest

from anime_rpc.matcher import build_filename_pattern

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
    "rpc.config",
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
    "rpc.config",
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


@pytest.mark.parametrize(
    ("name", "filenames", "n_episodes"),
    [
        ("arifureta", ARIFURETA, 16),
        ("dandadan", DANDADAN, 12),
        ("salaryman", SALARYMAN, 12),
        ("breaking_bad", BREAKING_BAD, 7),
        ("house_md", HOUSE_MD, 22),
        ("the_punisher", THE_PUNISHER, 13),
        ("dungeon_meshi", DUNGEON_MESHI, 24),
    ],
)
def test_generated_pattern_ordered(name: str, filenames: list[str], n_episodes: int):
    pattern = build_filename_pattern(filenames)

    assert pattern is not None, f"Pattern should not be None for {name}"

    pattern = pattern.replace("%ep%", r"(?P<ep>\d+)")
    compiled_pattern = re.compile(pattern)
    expected_eps = [*range(1, n_episodes + 1)][::-1]

    for filename in filenames:
        # only test against playable media files
        if not filename.endswith(".mkv"):
            continue
        if not (match := compiled_pattern.search(filename)):
            continue
        ep = int(match.group("ep"))
        assert (
            ep == expected_eps.pop()
        ), f"Episode {ep} does not match expected value for {name}"

    assert not expected_eps, f"Some episodes are unmatched: {expected_eps}"
