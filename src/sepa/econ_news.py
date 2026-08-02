"""경제뉴스() — overnight US market brief PDF.

Usage:
    python -m sepa.econ_news
    python -m sepa.econ_news --as-of 2026-07-21
"""

from __future__ import annotations

import argparse
import logging
import shutil
from datetime import date
from pathlib import Path

from sepa.artifacts import publish, publish_github_release_asset, release_download_url
from sepa.econ_news_data import build_bundle
from sepa.econ_news_report import write_pdf

logger = logging.getLogger(__name__)


def econ_release_tag(session: str) -> str:
    """``2026-07-21`` → ``sepa-econ-20260721``."""
    compact = session.replace("-", "")
    return f"sepa-econ-{compact}"


def publish_econ_pdf_release(pdf_path: Path, *, session: str) -> dict:
    """Upload econ news PDF to GitHub Release (same UX as ``!sepa.anal``)."""
    from sepa.artifacts import github_repo_slug

    tag = econ_release_tag(session)
    repo = github_repo_slug() or "Informatica-king/easy-python-project"
    download = release_download_url(repo, tag, pdf_path.name)
    notes = (
        f"SEPA `경제뉴스()` / `!sepa.econ` overnight brief ({session}).\n\n"
        f"Direct download: {download}\n"
    )
    rel = publish_github_release_asset(
        pdf_path,
        tag=tag,
        title=f"SEPA Econ News {session}",
        notes=notes,
        repo=repo,
    )
    if rel.get("ok"):
        rel["pdf_name"] = pdf_path.name
    return rel


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="경제뉴스() — prior US session brief PDF")
    p.add_argument("--as-of", type=str, default=None, help="Session date YYYY-MM-DD")
    p.add_argument("--portfolio", type=str, default="config/portfolio_watch.yaml")
    p.add_argument("--out-dir", type=str, default="reports")
    p.add_argument(
        "--skip-github-release",
        action="store_true",
        help="Skip uploading PDF to GitHub Release (no public download link)",
    )
    args = p.parse_args(argv)

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    print("[경제뉴스] collecting market bars + RSS + portfolio news…")
    bundle = build_bundle(session=as_of, portfolio_path=args.portfolio)
    stamp = bundle.session_date.isoformat()
    out = Path(args.out_dir) / f"Econ_News_{stamp}.pdf"
    write_pdf(bundle, [out])
    print(f"[경제뉴스] session={stamp} mood={bundle.mood}")
    print(f"[경제뉴스] PDF {out} ({out.stat().st_size} bytes)")

    art = publish(out)
    if art is not None:
        print(f"[경제뉴스] artifact {art}")

    assets_dir = Path("assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    assets_pdf = assets_dir / out.name
    shutil.copy2(out, assets_pdf)
    print(f"[경제뉴스] assets {assets_pdf}")

    if not args.skip_github_release:
        print("\n" + "=" * 64)
        print("  PDF 직접 다운로드 링크 (GitHub Release)")
        print("=" * 64)
        rel = publish_econ_pdf_release(out, session=stamp)
        if rel.get("ok"):
            print(f"\n  PDF 직접 다운로드:\n  {rel['download_url']}\n")
            print(f"  릴리즈 페이지: {rel['release_url']}")
        else:
            print(f"[경고] GitHub Release 업로드 실패: {rel.get('error')}")
            print("  (로컬 PDF/artifacts는 생성됨 — --skip-github-release 로 생략 가능)")

    for b in bundle.bullets:
        print(f"  • {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
