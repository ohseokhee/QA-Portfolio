"""day81_mem_measure 파서·판정 단위 테스트 (기기 불필요)"""
import pytest

from day81_mem_measure import analyze, demo_texts, parse_meminfo, parse_status

# 상세 표(TOTAL 행, 콜론 없음) + App Summary(TOTAL PSS:)가 함께 있는 안드로이드 10 이후 형식
MEMINFO_NEW = """** MEMINFO in pid 12345 [com.example.app] **
                   Pss  Private  Private  SwapPss      Rss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty    Total     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------   ------
  Native Heap    41236    41180        0       52    43120    65536    48211    17324
  Dalvik Heap    10220    10160        0       40    18200    24576    12288    12288
        TOTAL   149088   120044    18320      120   197420    90112    60499    29612

 App Summary
                       Pss(KB)                        Rss(KB)
                        ------                         ------
           Java Heap:    12488                          28392
         Native Heap:    41180                          43120
                Code:    15232                          58864
               Stack:     1092                           1100
            Graphics:    60412                          60412
       Private Other:     8340
              System:    10344
             Unknown:                                    5532

           TOTAL PSS:   149088            TOTAL RSS:   197420       TOTAL SWAP PSS:      120
"""

# 안드로이드 9 이전 형식: TOTAL: 뒤에 SWAP PSS만
MEMINFO_OLD = """ App Summary
                       Pss(KB)
                        ------
           Java Heap:     9000
         Native Heap:    20000
                Code:     5000
               Stack:      500
            Graphics:    30000
       Private Other:     2000
              System:     3500

               TOTAL:    70000       TOTAL SWAP PSS:       40
"""

# LDPlayer(안드로이드 14) 설정 앱 실제 출력 발췌: Summary 힙 PSS는 0, 상세 표 Heap Alloc은 정상, 스왑 표기 "TOTAL SWAP (KB):"
MEMINFO_EMULATOR = """** MEMINFO in pid 2417 [com.android.settings] **
                   Pss  Private  Private     Swap      Rss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty    Total     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------   ------
  Native Heap        0        0        0        0        0    20040    18258     1781
  Dalvik Heap        0        0        0        0        0     8361     5467     2894
 Dalvik Other       16       16        0        0       32                           
        TOTAL    67294    22692    27200        0   180584    28401    23725     4675
 
 App Summary
                       Pss(KB)                        Rss(KB)
                        ------                         ------
           Java Heap:       72                            224
         Native Heap:        0                              0
                Code:    24388                         114428
               Stack:       60                             68
            Graphics:        0                              0
       Private Other:    25372
              System:    17402
             Unknown:                                   65864
 
           TOTAL PSS:    67294            TOTAL RSS:   180584      TOTAL SWAP (KB):        0
"""

STATUS = """Name:\tcom.example.app
Pid:\t12345
VmRSS:\t  197420 kB
RssAnon:\t  121500 kB
RssFile:\t   74100 kB
VmSwap:\t     310 kB
"""


def test_mm_01_new_format_summary():
    row = parse_meminfo(MEMINFO_NEW)
    assert row["total_pss"] == 149088
    assert row["total_rss"] == 197420
    assert row["swap_pss"] == 120
    assert row["native_heap"] == 41180  # 상세 표의 41236이 아니라 App Summary 값
    assert row["graphics"] == 60412
    assert (row["native_alloc"], row["dalvik_alloc"]) == (48211, 12288)  # 상세 표 Heap Alloc 열


def test_mm_02_old_format_total():
    row = parse_meminfo(MEMINFO_OLD)
    assert row["total_pss"] == 70000
    assert row["total_rss"] == 0
    assert row["swap_pss"] == 40


def test_mm_09_emulator_android14_format():
    row = parse_meminfo(MEMINFO_EMULATOR)
    assert (row["total_pss"], row["total_rss"], row["swap_pss"]) == (67294, 180584, 0)
    assert row["native_heap"] == 0
    assert (row["native_alloc"], row["dalvik_alloc"], row["heap_alloc"]) == (18258, 5467, 23725)


def test_mm_03_not_running_raises():
    with pytest.raises(ValueError):
        parse_meminfo("No process found for: com.example.app\n")


def test_mm_04_anon_plus_swap():
    row = parse_status(STATUS)
    assert (row["rss_anon"], row["vm_swap"], row["anon_swap"]) == (121500, 310, 121810)


def _rows(native_by_label, anon_by_label, heap_by_label=None):
    return [{"label": label, "total_pss": 0, "graphics": 0, "native_heap": native, "anon_swap": anon_by_label[label],
             "heap_alloc": (heap_by_label or {}).get(label, 0)}
            for label, native in native_by_label.items()]


def test_mm_05_leak_detected_when_rising():
    rows = _rows({"lobby": 100, "lobby_after1": 104, "lobby_after2": 108},
                 {"lobby": 1, "lobby_after1": 1, "lobby_after2": 1})
    _, checks = analyze(rows)
    assert checks[0][1] == "누수 의심"


def test_mm_06_no_leak_when_returning():
    rows = _rows({"lobby": 100, "lobby_after1": 112, "lobby_after2": 101},
                 {"lobby": 1, "lobby_after1": 1, "lobby_after2": 1})
    _, checks = analyze(rows)
    assert checks[0][1] == "PASS"


def test_mm_10_leak_uses_heap_alloc_when_available():
    # Summary Native Heap은 0(에뮬레이터)이어도 Heap Alloc이 오르면 누수 의심
    rows = _rows({"lobby": 0, "lobby_after1": 0, "lobby_after2": 0}, {"lobby": 1, "lobby_after1": 1, "lobby_after2": 1},
                 {"lobby": 100, "lobby_after1": 104, "lobby_after2": 108})
    _, checks = analyze(rows)
    assert checks[0][0].endswith("힙 할당량(Native+Dalvik Alloc)") and checks[0][1] == "누수 의심"


def test_mm_11_plateau_is_not_leak():
    # 실측(설정 앱 15회 왕복) 패턴: 초반 증가 후 최근 5회 평탄 → 증가 후 안정
    vals = [23.3, 34.0, 36.4, 37.9, 39.0, 40.4, 40.5, 41.4, 42.4, 42.1, 41.8, 41.8, 42.2, 42.4, 42.5, 42.5]
    labels = ["lobby"] + [f"lobby_after{i}" for i in range(1, len(vals))]
    rows = _rows(dict.fromkeys(labels, 0), dict.fromkeys(labels, 1), dict(zip(labels, vals)))
    _, checks = analyze(rows)
    assert checks[0][1] == "증가 후 안정"


def test_mm_12_still_rising_is_leak():
    # 실측(설정 앱 6회 왕복) 패턴: 최근 5회도 계속 증가 → 아직 누수 의심
    vals = [23.0, 33.8, 35.9, 36.9, 38.0, 38.5, 39.7]
    labels = ["lobby"] + [f"lobby_after{i}" for i in range(1, len(vals))]
    rows = _rows(dict.fromkeys(labels, 0), dict.fromkeys(labels, 1), dict(zip(labels, vals)))
    _, checks = analyze(rows)
    assert checks[0][1] == "누수 의심"


def test_mm_07_background_not_released():
    rows = _rows({"lobby": 100, "lobby_after1": 100, "lobby_after2": 100, "background": 100},
                 {"lobby": 200, "lobby_after1": 200, "lobby_after2": 200, "background": 180})
    _, checks = analyze(rows)
    assert checks[1][1] == "확인 필요"


def test_mm_08_demo_texts_parse():
    texts = list(demo_texts())
    assert len(texts) == 36
    for _, meminfo, status in texts:
        assert parse_meminfo(meminfo)["total_pss"] > 0
        assert parse_status(status)["anon_swap"] > 0
