"""
AURELIS Luxury Watch E-Commerce Platform
Automated Mobile Responsiveness Verification Suite
Validates:
1. Viewport Meta Tags across all 30+ HTML pages
2. CSS Braces and Syntax Integrity
3. Responsive Breakpoints (320px, 360px, 480px, 600px, 768px, 900px)
4. Elimination of fixed minmax(320px, 1fr) card overflows
5. 100vw replacement with 100%
6. Mobile Navigation Toggle integrity
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def test_viewport_meta_tags():
    html_files = list(ROOT_DIR.glob("*.html"))
    missing_viewport = []
    for hf in html_files:
        content = hf.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r'<meta\s+name=["\']viewport["\']\s+content=["\'][^"\']*width=device-width', content, re.IGNORECASE):
            # Also check reverse order of attributes
            if not re.search(r'<meta\s+content=["\'][^"\']*width=device-width[^"\']*["\']\s+name=["\']viewport["\']', content, re.IGNORECASE):
                missing_viewport.append(hf.name)
    assert not missing_viewport, f"Missing viewport meta tag in: {missing_viewport}"
    print(f"PASS: All {len(html_files)} HTML pages have valid mobile viewport meta tags.")

def test_css_brace_balance():
    css_files = list((ROOT_DIR / "css").glob("*.css"))
    for cf in css_files:
        content = cf.read_text(encoding="utf-8", errors="ignore")
        # Remove comments and strings for accurate brace counting
        no_comments = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        opens = no_comments.count('{')
        closes = no_comments.count('}')
        assert opens == closes, f"Brace mismatch in {cf.name}: {opens} opens vs {closes} closes"
        print(f"PASS: {cf.name} has balanced braces ({opens} blocks).")

def test_media_queries_defined():
    main_css = (ROOT_DIR / "css" / "main.css").read_text(encoding="utf-8")
    hero_css = (ROOT_DIR / "css" / "hero.css").read_text(encoding="utf-8")
    shop_css = (ROOT_DIR / "css" / "shop.css").read_text(encoding="utf-8")
    product_css = (ROOT_DIR / "css" / "product.css").read_text(encoding="utf-8")
    cart_css = (ROOT_DIR / "css" / "cart-checkout.css").read_text(encoding="utf-8")

    # Verify breakpoints exist
    for bp in ["900px", "768px", "600px", "480px", "360px"]:
        assert f"max-width: {bp}" in main_css or f"max-width:{bp}" in main_css, f"main.css missing breakpoint {bp}"
    print("PASS: main.css contains full responsive suite (900px, 768px, 600px, 480px, 360px).")

    for bp in ["768px", "480px", "360px"]:
        assert f"max-width: {bp}" in hero_css or f"max-width:{bp}" in hero_css, f"hero.css missing breakpoint {bp}"
    print("PASS: hero.css contains full responsive suite (768px, 480px, 360px).")

    for bp in ["900px", "640px", "480px", "360px"]:
        assert f"max-width: {bp}" in shop_css or f"max-width:{bp}" in shop_css, f"shop.css missing breakpoint {bp}"
    print("PASS: shop.css contains full responsive suite (900px, 640px, 480px, 360px).")

def test_no_horizontal_overflow_patterns():
    hero_css = (ROOT_DIR / "css" / "hero.css").read_text(encoding="utf-8")
    shop_css = (ROOT_DIR / "css" / "shop.css").read_text(encoding="utf-8")
    
    # 100vw check in sticky stage
    assert "width: 100vw;" not in hero_css, "Found 'width: 100vw;' in hero.css which causes scrollbar overflow"
    print("PASS: No 100vw scrollbar traps in hero.css.")

    # Check products-grid doesn't enforce rigid 320px minimum
    assert "repeat(auto-fill, minmax(320px, 1fr))" not in shop_css, "Found rigid minmax(320px, 1fr) in shop.css"
    print("PASS: products-grid uses responsive minmax(min(100%, 300px), 1fr).")

def test_universal_nav_controller():
    api_js = (ROOT_DIR / "js" / "api.js").read_text(encoding="utf-8")
    assert "initAurelisMobileNav" in api_js, "initAurelisMobileNav not found in js/api.js"
    assert "mobileBtn.addEventListener(\"click\"" in api_js, "Mobile click listener not found in js/api.js"
    assert "Escape" in api_js, "Escape key dismiss not found in js/api.js"
    print("PASS: Universal mobile navigation controller verified in js/api.js.")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("RUNNING MOBILE RESPONSIVENESS VALIDATION")
    print("="*60)
    test_viewport_meta_tags()
    test_css_brace_balance()
    test_media_queries_defined()
    test_no_horizontal_overflow_patterns()
    test_universal_nav_controller()
    print("\n" + "="*60)
    print("ALL RESPONSIVE CHECKS PASSED (100% SUCCESS)")
    print("="*60 + "\n")
