import os
import cv2
import numpy as np

def shift_color_lab(img, mask, target_a_shift, target_b_shift, l_scale=1.0):
    """
    Transforms the color of masked pixels in LAB color space.
    Preserves L (luminance/shading/highlights) while shifting A and B channels.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    l, a, b = cv2.split(lab)
    
    # Smooth mask for natural blending at edges
    blur_mask = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (15, 15), 0)
    blur_mask_3d = np.repeat(blur_mask[:, :, np.newaxis], 3, axis=2)
    
    # Adjust channels
    new_l = np.clip(l * l_scale, 0, 255)
    new_a = np.clip(a + target_a_shift, 0, 255)
    new_b = np.clip(b + target_b_shift, 0, 255)
    
    new_lab = cv2.merge([new_l, new_a, new_b])
    new_bgr = cv2.cvtColor(new_lab.astype(np.uint8), cv2.COLOR_LAB2BGR)
    
    # Blend original and transformed
    result = (img.astype(np.float32) * (1.0 - blur_mask_3d) + new_bgr.astype(np.float32) * blur_mask_3d).astype(np.uint8)
    return result

def get_dial_protect_mask(h, w, center, radius):
    """Creates an elliptical/circular mask protecting the dial, bezel, and background."""
    protect = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(protect, center, radius, 255, -1)
    return protect

def process_all_variants():
    assets_dir = os.path.join(os.path.dirname(__file__), "assets", "watches")
    print(f"Generating secondary watch variants in: {assets_dir}")

    # Watch 2: VELOR CHRONOGRAPH -> Gunmetal DLC & Midnight Navy / Two-Tone Rose Gold Links
    # Original: Brushed Steel & Charcoal
    p2 = os.path.join(assets_dir, "watch_2.jpg")
    img2 = cv2.imread(p2)
    if img2 is not None:
        h, w = img2.shape[:2]
        # Strap is outside dial area (center ~450, 480, r=260)
        mask2 = np.zeros((h, w), dtype=np.uint8)
        # Bracelet regions: top-left and right/bottom
        cv2.fillPoly(mask2, [
            np.array([[50, 200], [300, 210], [250, 450], [90, 400]], dtype=np.int32),
            np.array([[550, 320], [920, 420], [860, 680], [530, 580]], dtype=np.int32),
            np.array([[400, 640], [800, 720], [700, 800], [250, 780]], dtype=np.int32),
            np.array([[150, 450], [130, 620], [320, 750], [250, 600]], dtype=np.int32)
        ], 255)
        # Exclude dial
        cv2.circle(mask2, (440, 520), 250, 0, -1)
        # Shift to Warm Two-Tone Rose Gold
        var2_img = shift_color_lab(img2, mask2, target_a_shift=14, target_b_shift=22, l_scale=1.02)
        out2 = os.path.join(assets_dir, "watch_2_variant2.jpg")
        cv2.imwrite(out2, var2_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 2 Variant 2 generated: Two-Tone Rose Gold & Steel Links")

    # Watch 3: NOIR EDGE -> Matte Black & Saddle Cognac Brown Leather
    # Original: Matte Black & Onyx Alligator Leather
    p3 = os.path.join(assets_dir, "watch_3.jpg")
    img3 = cv2.imread(p3)
    if img3 is not None:
        h, w = img3.shape[:2]
        mask3 = np.zeros((h, w), dtype=np.uint8)
        # Top strap: (20,20) to (500, 320)
        cv2.fillPoly(mask3, [
            np.array([[20, 20], [480, 280], [280, 420], [10, 180]], dtype=np.int32),
            np.array([[580, 680], [780, 580], [1000, 850], [780, 1020]], dtype=np.int32)
        ], 255)
        cv2.circle(mask3, (530, 500), 240, 0, -1)
        # Cognac Brown: warm lightness boost, +A (red), +B (yellow)
        var3_img = shift_color_lab(img3, mask3, target_a_shift=20, target_b_shift=38, l_scale=1.45)
        out3 = os.path.join(assets_dir, "watch_3_variant2.jpg")
        cv2.imwrite(out3, var3_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 3 Variant 2 generated: Matte Black & Saddle Cognac Brown Leather")

    # Watch 4: IMPERIAL STEEL -> Two-Tone Rose Gold & Steel
    # Original: Silver Multi-Link Bracelet & Midnight Blue Dial
    p4 = os.path.join(assets_dir, "watch_4.jpg")
    img4 = cv2.imread(p4)
    if img4 is not None:
        h, w = img4.shape[:2]
        mask4 = np.zeros((h, w), dtype=np.uint8)
        # Left bracelet links:
        cv2.fillPoly(mask4, [
            np.array([[160, 420], [330, 400], [330, 620], [160, 640]], dtype=np.int32),
            np.array([[650, 460], [920, 480], [920, 660], [650, 660]], dtype=np.int32)
        ], 255)
        cv2.circle(mask4, (510, 500), 220, 0, -1)
        var4_img = shift_color_lab(img4, mask4, target_a_shift=18, target_b_shift=26, l_scale=1.05)
        out4 = os.path.join(assets_dir, "watch_4_variant2.jpg")
        cv2.imwrite(out4, var4_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 4 Variant 2 generated: Two-Tone Rose Gold & Steel Bracelet")

    # Watch 5: ROYALE MESH -> Stealth Black Milanese Mesh & Champagne Dial
    # Original: Silver Milanese Mesh
    p5 = os.path.join(assets_dir, "watch_5.jpg")
    img5 = cv2.imread(p5)
    if img5 is not None:
        h, w = img5.shape[:2]
        mask5 = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask5, [
            np.array([[200, 220], [600, 240], [350, 480], [210, 460]], dtype=np.int32),
            np.array([[600, 300], [940, 460], [860, 680], [580, 680]], dtype=np.int32)
        ], 255)
        cv2.circle(mask5, (470, 510), 210, 0, -1)
        # Darken to sleek stealth black
        var5_img = shift_color_lab(img5, mask5, target_a_shift=0, target_b_shift=0, l_scale=0.45)
        out5 = os.path.join(assets_dir, "watch_5_variant2.jpg")
        cv2.imwrite(out5, var5_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 5 Variant 2 generated: Stealth Black Milanese Mesh")
    # Watch 6: OBSIDIAN ELITE -> DLC Black & Deep Burgundy Alligator Strap
    # Original: All-Black DLC Metal Bracelet
    p6 = os.path.join(assets_dir, "watch_6.jpg")
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
        # Rich deep burgundy: +A (red), slight +B, moderate lightness
        var6_img = shift_color_lab(img6, mask6, target_a_shift=28, target_b_shift=6, l_scale=1.35)
        out6 = os.path.join(assets_dir, "watch_6_variant2.jpg")
        cv2.imwrite(out6, var6_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 6 Variant 2 generated: DLC Black & Deep Burgundy Strap")

    # Watch 7: TITAN CLASSIC -> Brushed Silver Steel & Slate Grey
    # Original: Gunmetal Steel
    p7 = os.path.join(assets_dir, "watch_7.jpg")
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
        # Brighten to mirror/brushed surgical steel
        var7_img = shift_color_lab(img7, mask7, target_a_shift=-2, target_b_shift=-4, l_scale=1.45)
        out7 = os.path.join(assets_dir, "watch_7_variant2.jpg")
        cv2.imwrite(out7, var7_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 7 Variant 2 generated: Brushed Silver Steel & Slate Grey")

    # Watch 8: AUREN SIGNATURE -> 18K Gold & Midnight Onyx Black Leather
    # Original: 18K Gold & Cognac Brown Leather
    p8 = os.path.join(assets_dir, "watch_8.jpg")
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
        # Shift cognac brown to deep sleek onyx black leather: lower L, desaturate
        var8_img = shift_color_lab(img8, mask8, target_a_shift=-18, target_b_shift=-30, l_scale=0.42)
        out8 = os.path.join(assets_dir, "watch_8_variant2.jpg")
        cv2.imwrite(out8, var8_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 8 Variant 2 generated: 18K Gold & Midnight Onyx Black Leather")

    # Watch 9: MONARCH BLACK -> DLC Stealth Black & Emerald Green
    # Original: Solid Brushed Steel Bracelet & Emerald Green Dial
    p9 = os.path.join(assets_dir, "watch_9.jpg")
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
        # Darken steel bracelet to stealth black DLC
        var9_img = shift_color_lab(img9, mask9, target_a_shift=0, target_b_shift=0, l_scale=0.48)
        out9 = os.path.join(assets_dir, "watch_9_variant2.jpg")
        cv2.imwrite(out9, var9_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 9 Variant 2 generated: DLC Stealth Black Steel & Emerald Green")

    # Watch 10: SILVER CREST -> 18K Rose Gold-Tone Links & White Porcelain
    # Original: Mirror Silver Link Bracelet
    p10 = os.path.join(assets_dir, "watch_10.jpg")
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
        # Warm rose gold shift
        var10_img = shift_color_lab(img10, mask10, target_a_shift=16, target_b_shift=24, l_scale=1.04)
        out10 = os.path.join(assets_dir, "watch_10_variant2.jpg")
        cv2.imwrite(out10, var10_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print("[OK] Watch 10 Variant 2 generated: 18K Rose Gold-Tone Links & White Porcelain")

if __name__ == "__main__":
    process_all_variants()
