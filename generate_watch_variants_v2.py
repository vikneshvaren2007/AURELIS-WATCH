import os
import shutil
import cv2
import numpy as np

def shift_color_lab(img, mask, target_a_shift, target_b_shift, l_scale=1.0, blur_ksize=21):
    """
    Transforms the color of masked pixels in LAB color space.
    Preserves L (luminance/shading/texture) while shifting A and B channels.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    l, a, b = cv2.split(lab)
    
    blur_mask = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (blur_ksize, blur_ksize), 0)
    blur_mask_3d = np.repeat(blur_mask[:, :, np.newaxis], 3, axis=2)
    
    new_l = np.clip(l * l_scale, 0, 255)
    new_a = np.clip(a + target_a_shift, 0, 255)
    new_b = np.clip(b + target_b_shift, 0, 255)
    
    new_lab = cv2.merge([new_l, new_a, new_b])
    new_bgr = cv2.cvtColor(new_lab.astype(np.uint8), cv2.COLOR_LAB2BGR)
    
    result = (img.astype(np.float32) * (1.0 - blur_mask_3d) + new_bgr.astype(np.float32) * blur_mask_3d).astype(np.uint8)
    return result

def apply_color_tint(img, mask, target_bgr, alpha=0.6, l_scale=1.0, blur_ksize=21):
    """
    Applies a target color tint while preserving underlying highlights, shadows, and texture.
    """
    blur_mask = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (blur_ksize, blur_ksize), 0)
    blur_mask_3d = np.repeat(blur_mask[:, :, np.newaxis], 3, axis=2)
    
    # Convert image to HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = cv2.split(hsv)
    
    # Target color in HSV
    target_pixel = np.uint8([[target_bgr]])
    target_hsv = cv2.cvtColor(target_pixel, cv2.COLOR_BGR2HSV)[0][0]
    
    target_h = target_hsv[0]
    target_s = target_hsv[1]
    
    new_h = target_h * np.ones_like(h)
    new_s = np.clip(target_s * 0.8 + s * 0.2, 0, 255)
    new_v = np.clip(v * l_scale, 0, 255)
    
    tinted_hsv = cv2.merge([new_h, new_s, new_v])
    tinted_bgr = cv2.cvtColor(tinted_hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    
    blended = img.astype(np.float32) * (1.0 - alpha) + tinted_bgr * alpha
    result = (img.astype(np.float32) * (1.0 - blur_mask_3d) + blended * blur_mask_3d).astype(np.uint8)
    return result

def generate_all_10_variants():
    base_dir = os.path.dirname(__file__)
    watches_dir = os.path.join(base_dir, "assets", "watches")
    variants_dir = os.path.join(watches_dir, "variants")
    os.makedirs(variants_dir, exist_ok=True)
    
    print(f"Generating 10 alternate watch variants in: {variants_dir}")

    # =========================================================================
    # WATCH 01: AURELIS CLASSIC
    # Original: Polished Silver Case, Ivory Dial, Medium Alligator Leather
    # Requested Alternate: Deep Brown / Rich Espresso Brown leather strap
    # =========================================================================
    p1 = os.path.join(watches_dir, "watch_1.jpg")
    img1 = cv2.imread(p1)
    if img1 is not None:
        h, w = img1.shape[:2]
        mask1 = np.zeros((h, w), dtype=np.uint8)
        # Top strap
        cv2.fillPoly(mask1, [
            np.array([[380, 150], [670, 150], [670, 310], [390, 280]], dtype=np.int32),
            # Bottom strap curve
            np.array([[300, 670], [550, 720], [700, 870], [530, 890], [310, 780]], dtype=np.int32),
            # Right side strap loop
            np.array([[550, 500], [880, 350], [890, 700], [550, 870]], dtype=np.int32)
        ], 255)
        # Protect dial and bezel (center at ~490, 500, r=240)
        cv2.circle(mask1, (485, 505), 235, 0, -1)
        # Deep espresso / dark chocolate brown: darken and enrich red/yellow undertones
        var1 = shift_color_lab(img1, mask1, target_a_shift=8, target_b_shift=12, l_scale=0.55)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-01-original.jpg"), img1, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-01-alternate.jpg"), var1, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_1_variant2.jpg"), var1, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 01 alternate generated: Deep Brown Leather Strap")

    # =========================================================================
    # WATCH 02: VELOR CHRONOGRAPH
    # Original: Brushed Gunmetal Steel & Charcoal
    # Requested Alternate: Navy Blue strap
    # =========================================================================
    p2 = os.path.join(watches_dir, "watch_2.jpg")
    img2 = cv2.imread(p2)
    if img2 is not None:
        h, w = img2.shape[:2]
        mask2 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask2, [
            np.array([[50, 200], [300, 210], [250, 450], [90, 400]], dtype=np.int32),
            np.array([[550, 320], [920, 420], [860, 680], [530, 580]], dtype=np.int32),
            np.array([[400, 640], [800, 720], [700, 800], [250, 780]], dtype=np.int32),
            np.array([[150, 450], [130, 620], [320, 750], [250, 600]], dtype=np.int32)
        ], 255)
        # Protect dial and tachymeter bezel
        cv2.circle(mask2, (440, 520), 250, 0, -1)
        # Shift to rich Navy Blue: LAB -a (blue/green), -b (blue), subtle L
        var2 = shift_color_lab(img2, mask2, target_a_shift=-5, target_b_shift=-35, l_scale=0.88)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-02-original.jpg"), img2, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-02-alternate.jpg"), var2, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_2_variant2.jpg"), var2, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 02 alternate generated: Navy Blue Strap")

    # =========================================================================
    # WATCH 03: NOIR EDGE
    # Original: Matte Black & Onyx Alligator Leather
    # Requested Alternate: Cognac Brown strap
    # =========================================================================
    p3 = os.path.join(watches_dir, "watch_3.jpg")
    img3 = cv2.imread(p3)
    if img3 is not None:
        h, w = img3.shape[:2]
        mask3 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask3, [
            np.array([[20, 20], [480, 280], [280, 420], [10, 180]], dtype=np.int32),
            np.array([[580, 680], [780, 580], [1000, 850], [780, 1020]], dtype=np.int32)
        ], 255)
        cv2.circle(mask3, (530, 500), 240, 0, -1)
        # Cognac Brown: warm golden-brown leather (+A, ++B, L scale 1.5)
        var3 = shift_color_lab(img3, mask3, target_a_shift=22, target_b_shift=42, l_scale=1.55)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-03-original.jpg"), img3, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-03-alternate.jpg"), var3, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_3_variant2.jpg"), var3, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 03 alternate generated: Cognac Brown Strap")

    # =========================================================================
    # WATCH 04: IMPERIAL STEEL
    # Original: Silver Multi-Link Bracelet & Midnight Blue Dial
    # Requested Alternate: Forest Green strap
    # =========================================================================
    p4 = os.path.join(watches_dir, "watch_4.jpg")
    img4 = cv2.imread(p4)
    if img4 is not None:
        h, w = img4.shape[:2]
        mask4 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask4, [
            np.array([[160, 400], [330, 400], [330, 640], [160, 640]], dtype=np.int32),
            np.array([[650, 440], [920, 480], [920, 660], [650, 660]], dtype=np.int32)
        ], 255)
        cv2.circle(mask4, (510, 500), 220, 0, -1)
        # Forest Green: -A (green), +B (olive/warm green), dark luxury tone
        var4 = shift_color_lab(img4, mask4, target_a_shift=-28, target_b_shift=16, l_scale=0.82)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-04-original.jpg"), img4, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-04-alternate.jpg"), var4, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_4_variant2.jpg"), var4, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 04 alternate generated: Forest Green Strap")

    # =========================================================================
    # WATCH 05: ROYALE MESH
    # Original: Silver Milanese Mesh & Champagne Dial
    # Requested Alternate: Burgundy / Dark Wine strap
    # =========================================================================
    p5 = os.path.join(watches_dir, "watch_5.jpg")
    img5 = cv2.imread(p5)
    if img5 is not None:
        h, w = img5.shape[:2]
        mask5 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask5, [
            np.array([[200, 220], [600, 240], [350, 480], [210, 460]], dtype=np.int32),
            np.array([[600, 300], [940, 460], [860, 680], [580, 680]], dtype=np.int32)
        ], 255)
        cv2.circle(mask5, (470, 510), 210, 0, -1)
        # Deep Burgundy / Dark Wine: +A (red), slight +B, darkened luminance
        var5 = shift_color_lab(img5, mask5, target_a_shift=32, target_b_shift=8, l_scale=0.65)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-05-original.jpg"), img5, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-05-alternate.jpg"), var5, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_5_variant2.jpg"), var5, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 05 alternate generated: Burgundy/Dark Wine Strap")

    # =========================================================================
    # WATCH 06: OBSIDIAN ELITE
    # Original: All-Black DLC Metal Bracelet
    # Requested Alternate: Dark Tan strap
    # =========================================================================
    p6 = os.path.join(watches_dir, "watch_6.jpg")
    img6 = cv2.imread(p6)
    if img6 is not None:
        h, w = img6.shape[:2]
        mask6 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask6, [
            np.array([[420, 140], [740, 150], [580, 340], [380, 240]], dtype=np.int32),
            np.array([[550, 340], [860, 440], [780, 780], [580, 780]], dtype=np.int32),
            np.array([[270, 720], [680, 780], [650, 890], [280, 800]], dtype=np.int32)
        ], 255)
        cv2.circle(mask6, (440, 480), 260, 0, -1)
        # Dark Tan: warm earth tone, +A 18, +B 36, boost L from black
        var6 = shift_color_lab(img6, mask6, target_a_shift=18, target_b_shift=36, l_scale=1.40)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-06-original.jpg"), img6, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-06-alternate.jpg"), var6, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_6_variant2.jpg"), var6, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 06 alternate generated: Dark Tan Strap")

    # =========================================================================
    # WATCH 07: TITAN CLASSIC
    # Original: Gunmetal Steel & Slate Grey
    # Requested Alternate: Charcoal Grey strap (Sleek Platinum Silver & Charcoal)
    # =========================================================================
    p7 = os.path.join(watches_dir, "watch_7.jpg")
    img7 = cv2.imread(p7)
    if img7 is not None:
        h, w = img7.shape[:2]
        mask7 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask7, [
            np.array([[80, 200], [420, 200], [300, 600], [80, 550]], dtype=np.int32),
            np.array([[650, 200], [920, 210], [920, 460], [720, 450]], dtype=np.int32),
            np.array([[160, 620], [370, 650], [330, 920], [160, 880]], dtype=np.int32)
        ], 255)
        cv2.circle(mask7, (500, 470), 250, 0, -1)
        # Charcoal Grey: deep neutral dark graphite with crisp brushed highlights
        var7 = shift_color_lab(img7, mask7, target_a_shift=-2, target_b_shift=-4, l_scale=0.72)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-07-original.jpg"), img7, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-07-alternate.jpg"), var7, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_7_variant2.jpg"), var7, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 07 alternate generated: Charcoal Grey Strap")

    # =========================================================================
    # WATCH 08: AUREN SIGNATURE
    # Original: 18K Gold & Cognac Brown Leather
    # Requested Alternate: Olive / Dark Green strap
    # =========================================================================
    p8 = os.path.join(watches_dir, "watch_8.jpg")
    img8 = cv2.imread(p8)
    if img8 is not None:
        h, w = img8.shape[:2]
        mask8 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask8, [
            np.array([[380, 120], [720, 140], [600, 330], [380, 310]], dtype=np.int32),
            np.array([[620, 320], [880, 340], [880, 600], [650, 520]], dtype=np.int32),
            np.array([[330, 740], [540, 740], [540, 840], [330, 840]], dtype=np.int32)
        ], 255)
        cv2.circle(mask8, (480, 530), 245, 0, -1)
        # Shift cognac brown to Olive / Dark Green: -A (green), +B (olive yellow), L adjusted
        var8 = shift_color_lab(img8, mask8, target_a_shift=-36, target_b_shift=12, l_scale=0.78)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-08-original.jpg"), img8, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-08-alternate.jpg"), var8, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_8_variant2.jpg"), var8, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 08 alternate generated: Olive/Dark Green Strap")

    # =========================================================================
    # WATCH 09: MONARCH BLACK
    # Original: Brushed Steel Bracelet & Emerald Green Dial
    # Requested Alternate: Coffee Brown strap
    # =========================================================================
    p9 = os.path.join(watches_dir, "watch_9.jpg")
    img9 = cv2.imread(p9)
    if img9 is not None:
        h, w = img9.shape[:2]
        mask9 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask9, [
            np.array([[70, 250], [420, 190], [220, 580], [70, 540]], dtype=np.int32),
            np.array([[600, 270], [880, 420], [880, 770], [600, 770]], dtype=np.int32),
            np.array([[480, 720], [820, 760], [680, 870], [370, 840]], dtype=np.int32)
        ], 255)
        cv2.circle(mask9, (450, 500), 260, 0, -1)
        # Coffee Brown: rich warm roasted coffee tone (+A 16, +B 28, L scale 0.75)
        var9 = shift_color_lab(img9, mask9, target_a_shift=16, target_b_shift=28, l_scale=0.75)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-09-original.jpg"), img9, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-09-alternate.jpg"), var9, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_9_variant2.jpg"), var9, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 09 alternate generated: Coffee Brown Strap")

    # =========================================================================
    # WATCH 10: SILVER CREST
    # Original: Mirror Silver Link Bracelet
    # Requested Alternate: Deep Black strap with premium metallic accents
    # =========================================================================
    p10 = os.path.join(watches_dir, "watch_10.jpg")
    img10 = cv2.imread(p10)
    if img10 is not None:
        h, w = img10.shape[:2]
        mask10 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask10, [
            np.array([[460, 110], [740, 160], [530, 310], [440, 230]], dtype=np.int32),
            np.array([[550, 300], [880, 410], [820, 680], [600, 620]], dtype=np.int32),
            np.array([[250, 540], [470, 650], [380, 930], [250, 820]], dtype=np.int32)
        ], 255)
        cv2.circle(mask10, (480, 440), 240, 0, -1)
        # Deep Black with metallic highlights: reduce L while preserving specular shine
        var10 = shift_color_lab(img10, mask10, target_a_shift=0, target_b_shift=0, l_scale=0.38)
        
        cv2.imwrite(os.path.join(variants_dir, "watch-01-original.jpg"), img1, [cv2.IMWRITE_JPEG_QUALITY, 95]) # already done
        cv2.imwrite(os.path.join(variants_dir, "watch-10-original.jpg"), img10, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(variants_dir, "watch-10-alternate.jpg"), var10, [cv2.IMWRITE_JPEG_QUALITY, 95])
        cv2.imwrite(os.path.join(watches_dir, "watch_10_variant2.jpg"), var10, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 10 alternate generated: Deep Black Strap with Metallic Accents")

    print("\n[SUCCESS] ALL 10 WATCH VARIANTS SUCCESSFULLY GENERATED & SAVED IN assets/watches/variants/")

if __name__ == "__main__":
    generate_all_10_variants()
