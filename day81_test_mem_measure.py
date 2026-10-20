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


def test_mm_02_old_format_total():
    row = parse_meminfo(MEMINFO_OLD)
    assert row["total_pss"] == 70000
    assert row["total_rss"] == 0
    assert row["swap_pss"] == 40


def test_mm_03_not_running_raises():
    with pytest.raises(ValueError):
        parse_meminfo("No process found for: com.example.app\n")


def test_mm_04_anon_plus_swap():
    row = parse_status(STATUS)
    assert (row["rss_anon"], row["vm_swap"], row["anon_swap"]) == (121500, 310, 121810)


def _rows(native_by_label, anon_by_label):
    return [{"label": label, "total_pss": 0, "graphics": 0, "native_heap": native, "anon_swap": anon_by_label[label]}
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
