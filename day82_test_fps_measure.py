"""day82_fps_measure 파서·계산 단위 테스트 (기기 불필요)"""
import pytest

from day82_fps_measure import (PENDING, demo_sf_texts, fps_metrics, hist_intervals, judge, parse_framestats,
                               parse_gfxinfo, parse_sf_latency, parse_timestats)

VSYNC = 16_666_667

SF_LATENCY = f"""{VSYNC}
0 0 0
1000000000 1016666667 1008000000
1016666667 1033333334 1025000000
1033333334 1066666668 1058000000
0 {PENDING} 0
"""

GFXINFO = """Applications Graphics Acceleration Info:
Uptime: 5123456 Realtime: 5123456

** Graphics info for pid 12345 [com.android.settings] **

Stats since: 5100000000000ns
Total frames rendered: 482
Janky frames: 37 (7.68%)
Janky frames (legacy): 52 (10.79%)
50th percentile: 8ms
90th percentile: 14ms
95th percentile: 21ms
99th percentile: 38ms
Number Missed Vsync: 9
"""

FRAMESTATS = """---PROFILEDATA---
Flags,FrameTimelineVsyncId,IntendedVsync,Vsync,InputEventId,HandleInputStart,FrameCompleted,
0,1,1000000000,1000000000,0,1001000000,1010000000,
1,2,1016666667,1016666667,0,1017000000,1030000000,
0,3,1033333334,1033333334,0,1034000000,1043000000,
---PROFILEDATA---
"""


# LDPlayer(안드로이드 14) --timestats -dump 실제 출력 발췌 (히스토그램은 값이 있는 칸 위주로 줄임)
TIMESTATS = """displayRefreshRate = 60 fps
renderRate = 60 fps
uid = 10047
layerName = com.android.chrome/ChromeChildSurface#836
packageName =
gameMode = Unsupported
totalFrames = 489
droppedFrames = 0
averageFPS = 62.436
present2present histogram is as below:
0ms=8 1ms=0 15ms=0 16ms=473 17ms=0 32ms=0 33ms=8 34ms=0 36ms=0
latch2present histogram is as below:
0ms=0 5ms=4 6ms=6

displayRefreshRate = 60 fps
uid = 10047
layerName = none
packageName =
totalFrames = 0
droppedFrames = 0
"""


def test_fp_10_timestats_layers():
    layers = parse_timestats(TIMESTATS)
    assert [x["layer"] for x in layers] == ["com.android.chrome/ChromeChildSurface#836", "none"]
    chrome = layers[0]
    assert (chrome["frames"], chrome["dropped"], chrome["avg_fps"]) == (489, 0, 62.436)
    assert chrome["hist"][16] == 473 and chrome["hist"][33] == 8  # latch2present 줄과 섞이지 않음
    assert layers[1]["hist"] == {}


def test_fp_11_hist_intervals_skip_zero_bucket():
    intervals = hist_intervals({0: 8, 16: 3, 33: 1})
    assert intervals == [16, 16, 16, 33]


def test_fp_01_sf_latency_skips_zero_and_pending():
    period, presents = parse_sf_latency(SF_LATENCY)
    assert period == VSYNC
    assert presents == [1016666667, 1033333334, 1066666668]


def test_fp_02_sf_latency_invalid():
    with pytest.raises(ValueError):
        parse_sf_latency("Unknown layer: foo\n")


def test_fp_03_gfxinfo_summary():
    row = parse_gfxinfo(GFXINFO)
    assert (row["frames"], row["janky"], row["janky_pct"]) == (482, 37, 7.68)  # legacy 줄이 아닌 값
    assert (row["p50_ms"], row["p90_ms"], row["p99_ms"]) == (8, 14, 38)


def test_fp_04_framestats_excludes_flagged():
    assert parse_framestats(FRAMESTATS) == [1010000000, 1043000000]


def test_fp_05_steady_60fps():
    m = fps_metrics([i * VSYNC for i in range(121)])
    assert round(m["avg"], 1) == 60.0 and round(m["p99"], 1) == 60.0
    assert all(judge(m).values())


def test_fp_06_two_vsync_frames_count_as_30fps():
    # 100프레임 중 2개가 vsync 2개 → 하위 1%가 정확히 30fps, 기준 30 이상으로 판정돼야 함
    t, presents = 0, [0]
    for i in range(100):
        t += VSYNC * (2 if i in (10, 60) else 1)
        presents.append(t)
    m = fps_metrics(presents)
    assert m["p99"] < 30  # 부동소수 그대로면 29.99999
    assert judge(m)["p99"] is True


def test_fp_07_average_hides_spikes():
    # 평균은 55 이상이어도 하위 1%가 30 미만이면 FAIL
    t, presents = 0, [0]
    for i in range(300):
        t += VSYNC * (4 if i % 50 == 0 else 1)
        presents.append(t)
    ok = judge(fps_metrics(presents))
    assert ok["avg"] and not ok["p99"]


def test_fp_08_too_few_frames():
    with pytest.raises(ValueError):
        fps_metrics([0, VSYNC, 2 * VSYNC])


def test_fp_09_demo_texts_parse():
    segments = list(demo_sf_texts())
    assert [label for label, _ in segments] == ["lobby", "battle", "boss_skill"]
    for _, texts in segments:
        assert all(parse_sf_latency(t)[0] == VSYNC for t in texts)
