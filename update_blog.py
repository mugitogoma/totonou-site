#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_blog.py
記事HTML(01-*.html〜50-*.html)の変更を blog.html に反映する

使い方:
    py update_blog.py
    ※ blog.html と記事HTMLが同じフォルダにあること
"""

import re
import os
import sys
import glob

EXCERPT_MAX = 80  # 一覧に表示するexcertの最大文字数


# ============================================================
# 記事HTMLからメタ情報を抽出
# ============================================================

def extract_article_info(filepath):
    with open(filepath, encoding="utf-8") as f:
        html = f.read()

    # タイトル: <h1 class="article-title">...</h1>
    m = re.search(r'<h1[^>]*class="[^"]*article-title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ""

    # 日付: <time datetime="YYYY-MM-DD">
    m = re.search(r'<time[^>]*datetime="(\d{4}-\d{2}-\d{2})"', html)
    date_iso = m.group(1) if m else ""
    date_display = date_iso.replace("-", ".") if date_iso else ""

    # excerpt: blog-bodyの最初の<p>テキスト（本文修正が一覧に確実に反映される）
    # fallback: <meta name="description">（…">で閉じてる壊れたHTMLも対応）
    m = re.search(r'<div\s+class="blog-body">\s*<p>(.*?)</p>', html, re.DOTALL)
    if m:
        excerpt_full = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    else:
        m = re.search(r'<meta\s+name="description"\s+content="(.*?)"', html, re.DOTALL)
        excerpt_full = m.group(1).strip() if m else ""

    # EXCERPT_MAX字で切り捨て
    if len(excerpt_full) > EXCERPT_MAX:
        excerpt = excerpt_full[:EXCERPT_MAX] + "…"
    else:
        excerpt = excerpt_full

    # 本文テキスト全体（data-search用）
    m = re.search(r'<div\s+class="blog-body">(.*?)</div>\s*\n?\s*<div\s+class="blog-cta"', html, re.DOTALL)
    body_html = m.group(1) if m else ""
    body_text = re.sub(r'<[^>]+>', ' ', body_html)
    body_text = re.sub(r'\s+', ' ', body_text).strip()

    return {
        "title": title,
        "date_iso": date_iso,
        "date_display": date_display,
        "excerpt": excerpt,
        "body_text": body_text,
    }


# ============================================================
# blog.html のカード1枚を更新
# ============================================================

def escape_attr(s):
    return s.replace('"', '&quot;')


def update_card(card_html, article_info, page_title, category):
    title   = article_info["title"]
    d_iso   = article_info["date_iso"]
    d_disp  = article_info["date_display"]
    excerpt = article_info["excerpt"]
    body    = article_info["body_text"]

    data_search = f"{page_title} {category} {d_disp} {title} {excerpt} {body}"

    card_html = re.sub(r'data-title="[^"]*"',   f'data-title="{escape_attr(title)}"',          card_html)
    card_html = re.sub(r'data-date="[^"]*"',    f'data-date="{d_iso}"',                         card_html)
    card_html = re.sub(r'data-excerpt="[^"]*"', f'data-excerpt="{escape_attr(excerpt)}"',        card_html)
    card_html = re.sub(r'data-search="[^"]*"',  f'data-search="{escape_attr(data_search)}"',     card_html)
    card_html = re.sub(
        r'<time datetime="[^"]*">[^<]*</time>',
        f'<time datetime="{d_iso}">{d_disp}</time>',
        card_html
    )
    card_html = re.sub(
        r'(<h2\s+class="blog-title">)[^<]*(</h2>)',
        rf'\g<1>{title}\g<2>',
        card_html
    )
    card_html = re.sub(
        r'(<p\s+class="blog-excerpt">)[^<]*(</p>)',
        rf'\g<1>{excerpt}\g<2>',
        card_html
    )
    return card_html


# ============================================================
# メイン処理
# ============================================================

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    blog_path = os.path.join(script_dir, "blog.html")
    if not os.path.exists(blog_path):
        print(f"ERROR: blog.html が見つかりません: {blog_path}")
        sys.exit(1)

    with open(blog_path, encoding="utf-8") as f:
        blog_html = f.read()

    article_files = sorted(glob.glob(os.path.join(script_dir, "[0-9][0-9]-*.html")))
    if not article_files:
        print("ERROR: 記事HTMLが見つかりません")
        sys.exit(1)

    article_map = {}
    for path in article_files:
        fname = os.path.basename(path)
        try:
            info = extract_article_info(path)
            article_map[fname] = info
            print(f"  読み込み: {fname}  [{info['date_iso']}] {info['title'][:30]}...")
        except Exception as e:
            print(f"  WARNING: {fname} の解析に失敗 ({e})")

    card_pattern = re.compile(
        r'(<a\s+class="blog-card"[^>]+href="([^"]+)"[^>]*>.*?</a>)',
        re.DOTALL
    )

    updated = 0
    skipped = 0

    def replace_card(m):
        nonlocal updated, skipped
        card_html = m.group(1)
        href      = m.group(2)
        fname = os.path.basename(href)
        if fname not in article_map:
            skipped += 1
            return card_html

        info = article_map[fname]
        cat_m = re.search(r'data-category="([^"]*)"', card_html)
        category = cat_m.group(1) if cat_m else "整理収納コラム"
        page_title = f"{info['title']}｜山梨・甲府の片付け整理収納｜totonou（トトノウ）"

        updated += 1
        return update_card(card_html, info, page_title, category)

    new_blog_html = card_pattern.sub(replace_card, blog_html)

    backup_path = blog_path + ".bak"
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(blog_html)

    with open(blog_path, "w", encoding="utf-8") as f:
        f.write(new_blog_html)

    print(f"\n完了: {updated}枚更新, {skipped}枚スキップ")
    print(f"バックアップ: blog.html.bak")
    print(f"出力: blog.html")


if __name__ == "__main__":
    main()
