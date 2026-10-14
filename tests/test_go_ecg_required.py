"""!go always prints the ECG recommend copy line."""

from __future__ import annotations

from pathlib import Path

from sepa.macro import print_go_ecg_required_copy


def test_print_go_ecg_required_when_file_exists(tmp_path: Path, capsys):
    (tmp_path / "ecg_recommend_tickers_20261014.txt").write_text(
        "SLDE,VRNS,FRSH\n", encoding="utf-8"
    )
    n, line = print_go_ecg_required_copy("20261014", report_dir=tmp_path)
    assert n == 3
    assert line == "SLDE,VRNS,FRSH"
    out = capsys.readouterr().out
    assert "[필수] ECG 추천" in out
    assert "SLDE,VRNS,FRSH" in out
    assert "생략 없음" in out


def test_print_go_ecg_required_missing_file_errors(tmp_path: Path, capsys):
    n, line = print_go_ecg_required_copy("20261014", report_dir=tmp_path)
    assert n == 0
    assert line == ""
    out = capsys.readouterr().out
    assert "[오류] ECG 추천 파일이 없습니다" in out
    assert "[필수] ECG 추천" in out
    assert "(해당 없음)" in out
