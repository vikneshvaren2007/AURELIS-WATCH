import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import sqlite3
from werkzeug.security import generate_password_hash
from backend.database import get_db
from backend.models import init_db
from backend.config import Config

WATCHES = [
    {
        "name": "AURELIS CLASSIC",
        "slug": "aurelis-classic",
        "category_slug": "classic-luxury",
        "style": "Classic Luxury",
        "color": "Silver & Brown Leather",
        "sku": "AUR-CLS-01",
        "base_price": 5499.0,
        "discount_price": 6999.0,
        "stock": 15,
        "image": "./assets/watches/watch_1.jpg",
        "short_description": "Timeless dress timepiece featuring a polished silver case, porcelain cream dial, and supple brown leather strap.",
        "description": "The AURELIS Classic embodies the zenith of heritage dress horology. Encased in high-density 316L surgical stainless steel and paired with a hand-stitched Italian leather strap, this timepiece offers an understated yet commanding presence. The porcelain cream dial features subtle Roman numerals and an independent small-seconds register.",
        "specs": {
            "Movement": "Caliber 2035 High-Precision Japanese Quartz",
            "Case Diameter": "40 mm",
            "Case Thickness": "9.5 mm",
            "Case Material": "316L Surgical Stainless Steel (Mirror Polished)",
            "Dial": "Porcelain Cream with Applied Roman Numerals and Small Seconds",
            "Strap": "20mm Hand-Stitched Italian Brown Calfskin Leather",
            "Crystal": "Scratch-Resistant Sapphire Shield with AR Coating",
            "Water Resistance": "3 ATM / 30 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "Engraved Stainless Steel Pin Buckle"
        }
    },
    {
        "name": "VELOR CHRONOGRAPH",
        "slug": "velor-chronograph",
        "category_slug": "chronographs",
        "style": "Chronograph",
        "color": "Gunmetal & Charcoal",
        "sku": "AUR-VEL-02",
        "base_price": 6999.0,
        "discount_price": 8999.0,
        "stock": 12,
        "image": "./assets/watches/watch_2.jpg",
        "short_description": "Multi-function chronograph engineered with a gunmetal case, dark charcoal dial, and solid steel bracelet.",
        "description": "Built for decisive individuals who demand mechanical precision. The Velor Chronograph features a robust gunmetal finish with dual chronograph pushers and three textured sub-registers for split-second timing. The brushed stainless-steel bracelet delivers enduring comfort and wrist authority.",
        "specs": {
            "Movement": "Caliber VD57 Multi-Function Quartz Chronograph",
            "Case Diameter": "43 mm",
            "Case Thickness": "11.2 mm",
            "Case Material": "Ion-Plated Gunmetal 316L Stainless Steel",
            "Dial": "Textured Charcoal Sunray with Three Sub-Registers and Date",
            "Strap": "22mm Solid Brushed Stainless Steel Link Bracelet",
            "Crystal": "Hardened Anti-Reflective Mineral Crystal",
            "Water Resistance": "5 ATM / 50 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "Double-Push Safety Deployant Clasp"
        }
    },
    {
        "name": "NOIR EDGE",
        "slug": "noir-edge",
        "category_slug": "minimalist",
        "style": "Minimalist",
        "color": "Matte Black & Alligator Leather",
        "sku": "AUR-NOIR-03",
        "base_price": 5999.0,
        "discount_price": 7499.0,
        "stock": 18,
        "image": "./assets/watches/watch_3.jpg",
        "short_description": "Pure minimalist monochrome timepiece with an ultra-slim black case and genuine black leather strap.",
        "description": "Stripped of all superfluous ornament, the Noir Edge represents the purest manifestation of modern horological minimalism. Its ultra-slim 7.8mm profile glides effortlessly under tailored cuffs, while the pitch-black dial with polished silver hands delivers instant legibility.",
        "specs": {
            "Movement": "Ultra-Slim High-Torque Japanese Quartz Caliber",
            "Case Diameter": "39 mm",
            "Case Thickness": "7.8 mm (Ultra-Slim Profile)",
            "Case Material": "Matte Black DLC (Diamond-Like Carbon) Coated Steel",
            "Dial": "Matte Pitch Black with Slender Silver Baton Hands",
            "Strap": "20mm Full-Grain Black Alligator-Textured Genuine Leather",
            "Crystal": "Shatter-Resistant Hardened Crystal",
            "Water Resistance": "3 ATM / 30 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "Matte Black Anodized Pin Buckle"
        }
    },
    {
        "name": "IMPERIAL STEEL",
        "slug": "imperial-steel",
        "category_slug": "business-luxury",
        "style": "Business Luxury",
        "color": "Silver & Midnight Blue",
        "sku": "AUR-IMP-04",
        "base_price": 7499.0,
        "discount_price": 9499.0,
        "stock": 14,
        "image": "./assets/watches/watch_4.jpg",
        "short_description": "Commanding business luxury timepiece with a radiant sunburst blue dial and multi-link steel bracelet.",
        "description": "Engineered for executive environments, the Imperial Steel balances timeless boardroom elegance with modern metallurgical poise. The captivating sunburst midnight blue dial captures ambient light dynamically across brushed silver facets.",
        "specs": {
            "Movement": "Precision Date Quartz Movement with Quick-Set Function",
            "Case Diameter": "41 mm",
            "Case Thickness": "10.0 mm",
            "Case Material": "Dual-Finish 316L Solid Stainless Steel",
            "Dial": "Sunburst Midnight Blue with Applied Luminescent Markers",
            "Strap": "20mm Multi-Link Solid Stainless Steel Bracelet",
            "Crystal": "Flame-Fusion Scratch-Resistant Crystal with Anti-Glare",
            "Water Resistance": "5 ATM / 50 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "Concealed Butterfly Deployment Clasp"
        }
    },
    {
        "name": "ROYALE MESH",
        "slug": "royale-mesh",
        "category_slug": "modern-mesh",
        "style": "Modern Mesh",
        "color": "Silver & Champagne Gold",
        "sku": "AUR-ROY-05",
        "base_price": 6499.0,
        "discount_price": 7999.0,
        "stock": 10,
        "image": "./assets/watches/watch_5.jpg",
        "short_description": "Contemporary dress timepiece featuring an ethereal champagne dial and supple Milanese mesh strap.",
        "description": "A study in fluid sophistication. The Royale Mesh combines a polished silver bezel with a warm champagne gold sunray dial and a micro-woven Milanese mesh bracelet that drapes seamlessly around the wrist.",
        "specs": {
            "Movement": "Japanese Ultra-Thin Quartz Caliber",
            "Case Diameter": "40 mm",
            "Case Thickness": "8.2 mm",
            "Case Material": "Mirror-Polished 316L Stainless Steel",
            "Dial": "Warm Champagne Sunburst with Faceted Silver Indices",
            "Strap": "20mm Stainless Steel Milanese Weave Mesh",
            "Crystal": "High-Clarity Scratch-Resistant Mineral Crystal",
            "Water Resistance": "3 ATM / 30 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "Self-Adjustable Sliding Safety Lock"
        }
    },
    {
        "name": "OBSIDIAN ELITE",
        "slug": "obsidian-elite",
        "category_slug": "chronographs",
        "style": "Chronograph",
        "color": "All-Black DLC & Metal",
        "sku": "AUR-OBS-06",
        "base_price": 7999.0,
        "discount_price": 9999.0,
        "stock": 16,
        "image": "./assets/watches/watch_6.jpg",
        "short_description": "Stealth luxury sports chronograph in full DLC black finish with textured subdials and black metal bracelet.",
        "description": "Uncompromising authority in complete shadow. The Obsidian Elite is treated with a specialized diamond-like carbon coating that resists daily scuffs while exuding an unmistakable dark architectural poise with triple chronograph registers.",
        "specs": {
            "Movement": "Multi-Eye Chronometer Movement with Tachymeter Bezel",
            "Case Diameter": "42 mm",
            "Case Thickness": "11.5 mm",
            "Case Material": "Diamond-Like Carbon (DLC) Coated 316L Steel",
            "Dial": "Satin Obsidian Black with Concentric Guilloché Sub-Registers",
            "Strap": "22mm DLC Coated Solid Steel Three-Link Bracelet",
            "Crystal": "Deep Tinted Anti-Reflective Hardened Crystal",
            "Water Resistance": "5 ATM / 50 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "Dual-Push Security Deployant Clasp"
        }
    },
    {
        "name": "TITAN CLASSIC",
        "slug": "titan-classic",
        "category_slug": "business-luxury",
        "style": "Business Luxury",
        "color": "Gunmetal & Slate Grey",
        "sku": "AUR-TIT-07",
        "base_price": 8499.0,
        "discount_price": 10499.0,
        "stock": 11,
        "image": "./assets/watches/watch_7.jpg",
        "short_description": "Rugged business sport luxury watch with faceted gunmetal case, luminescent dial, and architectural link bracelet.",
        "description": "Engineered for executive authority and extreme resilience. The Titan Classic pairs a faceted coin-edge bezel with high-output SuperLuminova markers and a heavy-duty stainless-steel link bracelet built to command attention.",
        "specs": {
            "Movement": "Shock-Resistant Japanese Quartz Movement",
            "Case Diameter": "44 mm",
            "Case Thickness": "12.0 mm",
            "Case Material": "Gunmetal Ion-Plated Solid Steel with Coin-Edge Bezel",
            "Dial": "Matte Slate Grey with High-Luminescence Hour Markers",
            "Strap": "22mm Heavy Architectural Metal Link Bracelet",
            "Crystal": "Impact-Resistant Flame-Fusion Crystal",
            "Water Resistance": "10 ATM / 100 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "Diver Safety Flip-Lock Clasp"
        }
    },
    {
        "name": "AUREN SIGNATURE",
        "slug": "auren-signature",
        "category_slug": "classic-luxury",
        "style": "Classic Luxury",
        "color": "18K Gold-Tone & Cognac Leather",
        "sku": "AUR-AUR-08",
        "base_price": 5799.0,
        "discount_price": 7299.0,
        "stock": 15,
        "image": "./assets/watches/watch_8.jpg",
        "short_description": "Heritage gold-tone dress timepiece featuring a guilloché dial, blued steel hands, and cognac leather.",
        "description": "Drawing inspiration from 19th-century Swiss pocket chronometers, the Auren Signature radiates warmth and aristocratic balance. Its 18K yellow gold-toned case frames a multi-textured guilloché dial with heat-blued Breguet hands.",
        "specs": {
            "Movement": "Swiss-Pattern Small Seconds Quartz Movement",
            "Case Diameter": "41 mm",
            "Case Thickness": "9.8 mm",
            "Case Material": "18K Yellow Gold Ion-Plated 316L Stainless Steel",
            "Dial": "Multi-Pattern Champagne Guilloché with Blued Steel Hands",
            "Strap": "20mm Hand-Burnished Cognac Brown Calfskin Leather",
            "Crystal": "Scratch-Resistant Sapphire Crystal Shield",
            "Water Resistance": "3 ATM / 30 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "18K Gold Plated Engraved Tang Buckle"
        }
    },
    {
        "name": "MONARCH BLACK",
        "slug": "monarch-black",
        "category_slug": "modern-mesh",
        "style": "Modern Mesh",
        "color": "Steel, Black & Emerald Green",
        "sku": "AUR-MON-09",
        "base_price": 6799.0,
        "discount_price": 8499.0,
        "stock": 13,
        "image": "./assets/watches/watch_9.jpg",
        "short_description": "Modern contemporary timepiece with ceramic bezel, sunburst emerald green dial, and woven steel bracelet.",
        "description": "A magnificent contrast of ceramic gloss, deep emerald green dial, and satin-brushed steel mesh. The Monarch Black commands admiration in any setting, equipped with a magnifying cyclops date lens and luminescent diver indices.",
        "specs": {
            "Movement": "High-Beat Quartz Movement with Date Complication",
            "Case Diameter": "41 mm",
            "Case Thickness": "11.0 mm",
            "Case Material": "316L Stainless Steel with Unidirectional Ceramic Bezel",
            "Dial": "Sunburst Emerald Green with Luminous Applied Indices",
            "Strap": "20mm Contemporary Woven Steel Mesh Bracelet",
            "Crystal": "Magnifying Cyclops Lens over Mineral Crystal",
            "Water Resistance": "10 ATM / 100 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "Fold-Over Oysterlock Safety Clasp"
        }
    },
    {
        "name": "SILVER CREST",
        "slug": "silver-crest",
        "category_slug": "minimalist",
        "style": "Minimalist",
        "color": "Mirror Silver & White Porcelain",
        "sku": "AUR-SIL-10",
        "base_price": 5299.0,
        "discount_price": 6599.0,
        "stock": 20,
        "image": "./assets/watches/watch_10.jpg",
        "short_description": "Pure minimalist silver elegance with a porcelain white dial, blued sweep second hand, and Jubilee steel bracelet.",
        "description": "Purity, proportion, and luminous presence. The Silver Crest celebrates minimalist horological restraint with its radiant white dial, subtle date aperture, blued central seconds hand, and five-link Jubilee bracelet.",
        "specs": {
            "Movement": "Japanese Precision Three-Hand Quartz with Quick-Set Date",
            "Case Diameter": "40 mm",
            "Case Thickness": "9.2 mm",
            "Case Material": "Mirror-Polished 316L Solid Stainless Steel",
            "Dial": "Pure Enamel White with Silver Indices & Blued Second Hand",
            "Strap": "20mm Five-Link Jubilee Stainless Steel Bracelet",
            "Crystal": "Flame-Fusion Scratch-Resistant Crystal",
            "Water Resistance": "5 ATM / 50 Meters",
            "Warranty": "6-Month Warranty",
            "Clasp": "Concealed Butterfly Deployment Clasp"
        }
    },
    {
        "name": "AURELIS ROYAL TOURBILLON SQUELETTE",
        "slug": "aurelis-royal-tourbillon-squelette",
        "category_slug": "masterpiece-collection",
        "style": "Masterpiece Collection",
        "color": "18K Rose Gold & Skeleton Caliber",
        "sku": "AUR-MST-01-TRB",
        "base_price": 49999.0,
        "discount_price": 59999.0,
        "stock": 5,
        "image": "./assets/masterpiece/tourbillon-squelette.jpg",
        "short_description": "Bespoke high-horology flying tourbillon in 18K rose gold with hand-finished skeleton bridges.",
        "description": "The Royal Tourbillon Squelette represents the pinnacle of AURELIS Haute Horlogerie. Encased in 18K rose gold with an openworked architectural sapphire dial, the exposed flying tourbillon compensates for gravitational variations with poetic grace. Hand-beveled anglage and hand-stitched alligator leather.",
        "specs": {
            "Movement": "Caliber AT-01 In-House Flying Tourbillon (28,800 vph, 72-Hour Power Reserve)",
            "Case Diameter": "42 mm",
            "Case Thickness": "11.8 mm",
            "Case Material": "18K Rose Gold Coated 316L Surgical Stainless Steel",
            "Dial": "Openworked Skeleton with Hand-Chamfered Bridges and Sapphire Crystal",
            "Strap": "22mm Genuine Louisiana Alligator-Pattern Full-Grain Leather",
            "Crystal": "Double-Domed Flame-Fusion Sapphire Crystal with Multi-Layer AR Coating",
            "Water Resistance": "5 ATM / 50 Meters",
            "Warranty": "6-Month Manufacturer Movement Warranty",
            "Clasp": "18K Rose Gold Folding Deployant Buckle"
        }
    },
    {
        "name": "AURELIS CELESTIAL GRAND COMPLICATION",
        "slug": "aurelis-celestial-grand-complication",
        "category_slug": "masterpiece-collection",
        "style": "Masterpiece Collection",
        "color": "Midnight Blue Enamel & Platinum Steel",
        "sku": "AUR-MST-02-CLS",
        "base_price": 44999.0,
        "discount_price": 54999.0,
        "stock": 7,
        "image": "./assets/masterpiece/celestial-moonphase.jpg",
        "short_description": "Astronomical calendar chronograph featuring a guilloché midnight blue dial and poetic moonphase.",
        "description": "Capturing the cosmic mechanics of time, the Celestial Grand Complication pairs a split-second column-wheel chronograph with an astronomical lunar phase indicator accurate to one day every 122 years. Finished with a deep midnight blue sunray dial and polished steel.",
        "specs": {
            "Movement": "Caliber GC-55 Column-Wheel Automatic Chronograph with Astronomical Moonphase",
            "Case Diameter": "41.5 mm",
            "Case Thickness": "12.0 mm",
            "Case Material": "High-Polish 316L Surgical Grade Stainless Steel",
            "Dial": "Deep Midnight Blue Guilloché Enamel with Applied Breguet Gold Numerals",
            "Strap": "20mm Hand-Rolled Navy Italian Calfskin Leather Strap",
            "Crystal": "Scratch-Resistant Sapphire Crystal with Blue AR Shield",
            "Water Resistance": "5 ATM / 50 Meters",
            "Warranty": "6-Month Manufacturer Movement Warranty",
            "Clasp": "Dual-Release Push-Button Deployant Clasp"
        }
    },
    {
        "name": "AURELIS SOVEREIGN PLATINUM CHRONOMETER",
        "slug": "aurelis-sovereign-platinum-chronometer",
        "category_slug": "masterpiece-collection",
        "style": "Masterpiece Collection",
        "color": "Liquid Platinum & Opaline Silver",
        "sku": "AUR-MST-03-PLT",
        "base_price": 38999.0,
        "discount_price": 46999.0,
        "stock": 8,
        "image": "./assets/masterpiece/sovereign-platinum.jpg",
        "short_description": "Regulated chronometer in liquid platinum finish with blued steel hands and roman indices.",
        "description": "Engineered for connoisseurs of pure classical proportion, the Sovereign Platinum Chronometer achieves chronometer-certified precision. Its multi-tiered silver opaline dial displays concentric guilloché clous de Paris textures accented by thermal-blued steel leaf hands.",
        "specs": {
            "Movement": "Caliber CH-28 Certified High-Beat Chronometer Automatic",
            "Case Diameter": "40.5 mm",
            "Case Thickness": "9.8 mm",
            "Case Material": "Mirror-Polished Liquid Platinum Vapor-Deposition 316L Steel",
            "Dial": "Silver Opaline with Hand-Engine-Turned Clous de Paris Guilloché",
            "Strap": "20mm Semi-Matte Black Crocodile-Embossed Leather Strap",
            "Crystal": "Scratch-Resistant Flame-Fusion Sapphire Shield",
            "Water Resistance": "5 ATM / 50 Meters",
            "Warranty": "6-Month Manufacturer Movement Warranty",
            "Clasp": "Concealed Butterfly Deployment Buckle"
        }
    },
    {
        "name": "AURELIS MONACO HERITAGE AUTOMATIC",
        "slug": "aurelis-monaco-heritage-automatic",
        "category_slug": "masterpiece-collection",
        "style": "Masterpiece Collection",
        "color": "Brushed Gunmetal & Racing Emerald Green",
        "sku": "AUR-MST-04-MNC",
        "base_price": 32499.0,
        "discount_price": 39999.0,
        "stock": 10,
        "image": "./assets/masterpiece/monaco-heritage.jpg",
        "short_description": "High-octane racing chronograph with sunburst emerald green dial, tachymeter bezel, and rally strap.",
        "description": "Paying tribute to vintage circuit racing, the Monaco Heritage combines an aggressive brushed gunmetal case with a sunburst British racing green dial. Twin recessed registers, a high-precision tachymetric scale, and perforated rally strap evoke classic motorsport heritage.",
        "specs": {
            "Movement": "Caliber RC-88 High-Frequency Twin-Register Chronograph",
            "Case Diameter": "42.5 mm",
            "Case Thickness": "11.5 mm",
            "Case Material": "Brushed Ion-Plated Gunmetal Titanium-Alloy Steel",
            "Dial": "Sunburst British Racing Green with Dual Matte Silver Subdials",
            "Strap": "22mm Perforated Vintage Rally Calfskin Leather with Green Stitching",
            "Crystal": "Anti-Reflective Sapphire Crystal",
            "Water Resistance": "10 ATM / 100 Meters",
            "Warranty": "6-Month Manufacturer Movement Warranty",
            "Clasp": "Brushed Gunmetal Signed Tang Buckle"
        }
    },
    {
        "name": "AURELIS OCTO FINISSIMO CERAMIC",
        "slug": "aurelis-octo-finissimo-ceramic",
        "category_slug": "masterpiece-collection",
        "style": "Masterpiece Collection",
        "color": "Matte Stealth Black & Monolithic Ceramic",
        "sku": "AUR-MST-05-OCT",
        "base_price": 27999.0,
        "discount_price": 34999.0,
        "stock": 12,
        "image": "./assets/masterpiece/octo-ceramic.jpg",
        "short_description": "Avant-garde ultra-thin geometric architecture crafted in sandblasted stealth black high-tech ceramic.",
        "description": "Redefining contemporary haute horlogerie with architectural boldness, the Octo Finissimo Ceramic features an ultra-thin 8.2mm multi-faceted case. Crafted from scratch-proof zirconium oxide ceramic with an integrated seamless link bracelet, it is virtually indestructible.",
        "specs": {
            "Movement": "Caliber SL-12 Ultra-Thin High-Torque Mechanical Movement",
            "Case Diameter": "40 mm (Faceted Octagonal Architecture)",
            "Case Thickness": "8.2 mm (Ultra-Slim Design)",
            "Case Material": "Sandblasted Matte High-Tech Monolithic Ceramic",
            "Dial": "Monochrome Matte Anthracite with Skeletonized Hands and Minimalist Indices",
            "Strap": "Seamless Integrated Sandblasted Ceramic Link Bracelet",
            "Crystal": "Flat Sapphire Crystal with Double-Sided Anti-Reflective Shield",
            "Water Resistance": "5 ATM / 50 Meters",
            "Warranty": "6-Month Manufacturer Movement Warranty",
            "Clasp": "Integrated Three-Blade Titanium Concealed Deployant Clasp"
        }
    }
]

CORE_10_VARIANTS = {
    "aurelis-classic": [
        {
            "color_name": "Classic Brown Leather",
            "color_code": "#6b4423",
            "sku": "AUR-CLS-01-BRN",
            "price": 5499.0,
            "discount_price": 6999.0,
            "stock": 15,
            "image": "./assets/watches/variants/watch-01-original.jpg",
            "strap_color": "Hand-Stitched Italian Brown Calfskin Leather",
            "accent_color": "Porcelain Ivory Dial with Roman Numerals"
        },
        {
            "color_name": "Deep Brown Leather",
            "color_code": "#3e2723",
            "sku": "AUR-CLS-01-DBRN",
            "price": 5499.0,
            "discount_price": 6999.0,
            "stock": 12,
            "image": "./assets/watches/variants/watch-01-alternate.jpg",
            "strap_color": "Deep Brown Full-Grain Leather Strap",
            "accent_color": "Porcelain Ivory Dial with Blued Small Seconds"
        }
    ],
    "velor-chronograph": [
        {
            "color_name": "Brushed Steel & Charcoal",
            "color_code": "#4a4e52",
            "sku": "AUR-VEL-02-STL",
            "price": 6999.0,
            "discount_price": 8999.0,
            "stock": 12,
            "image": "./assets/watches/variants/watch-02-original.jpg",
            "strap_color": "Brushed Stainless Steel Link Bracelet",
            "accent_color": "Charcoal Sunray Chronograph Dial"
        },
        {
            "color_name": "Navy Blue",
            "color_code": "#1b3557",
            "sku": "AUR-VEL-02-NVY",
            "price": 6999.0,
            "discount_price": 8999.0,
            "stock": 10,
            "image": "./assets/watches/variants/watch-02-alternate.jpg",
            "strap_color": "Navy Blue Textured Leather Strap",
            "accent_color": "Charcoal Dial with Navy Blue Accents"
        }
    ],
    "noir-edge": [
        {
            "color_name": "Matte Black & Onyx",
            "color_code": "#1a1a1a",
            "sku": "AUR-NOIR-03-BLK",
            "price": 5999.0,
            "discount_price": 7499.0,
            "stock": 18,
            "image": "./assets/watches/variants/watch-03-original.jpg",
            "strap_color": "Onyx Black Alligator Leather Strap",
            "accent_color": "Matte Black Dial with Slender Silver Hands"
        },
        {
            "color_name": "Cognac Brown",
            "color_code": "#964b00",
            "sku": "AUR-NOIR-03-CGN",
            "price": 5999.0,
            "discount_price": 7499.0,
            "stock": 14,
            "image": "./assets/watches/variants/watch-03-alternate.jpg",
            "strap_color": "Cognac Brown Alligator Leather Strap",
            "accent_color": "Matte Black Dial with Warm Cognac Contrast"
        }
    ],
    "imperial-steel": [
        {
            "color_name": "Silver Steel & Midnight Blue",
            "color_code": "#1a365d",
            "sku": "AUR-IMP-04-SLV",
            "price": 7499.0,
            "discount_price": 9499.0,
            "stock": 14,
            "image": "./assets/watches/variants/watch-04-original.jpg",
            "strap_color": "Multi-Link 316L Solid Stainless Steel Bracelet",
            "accent_color": "Sunburst Midnight Blue Dial"
        },
        {
            "color_name": "Forest Green",
            "color_code": "#1b4d3e",
            "sku": "AUR-IMP-04-GRN",
            "price": 7499.0,
            "discount_price": 9499.0,
            "stock": 11,
            "image": "./assets/watches/variants/watch-04-alternate.jpg",
            "strap_color": "Forest Green Textured Sailcloth Strap",
            "accent_color": "Midnight Blue Dial with Green Contrast"
        }
    ],
    "royale-mesh": [
        {
            "color_name": "Silver Milanese Mesh",
            "color_code": "#c0c0c0",
            "sku": "AUR-ROY-05-SLV",
            "price": 6499.0,
            "discount_price": 7999.0,
            "stock": 10,
            "image": "./assets/watches/variants/watch-05-original.jpg",
            "strap_color": "Stainless Steel Milanese Weave Mesh",
            "accent_color": "Champagne Sunburst Dial"
        },
        {
            "color_name": "Burgundy / Dark Wine",
            "color_code": "#581825",
            "sku": "AUR-ROY-05-BUR",
            "price": 6499.0,
            "discount_price": 7999.0,
            "stock": 9,
            "image": "./assets/watches/variants/watch-05-alternate.jpg",
            "strap_color": "Burgundy Dark Wine Leather Strap",
            "accent_color": "Champagne Sunburst Dial with Wine Accents"
        }
    ],
    "obsidian-elite": [
        {
            "color_name": "All-Black DLC Steel",
            "color_code": "#181818",
            "sku": "AUR-OBS-06-DLC",
            "price": 7999.0,
            "discount_price": 9999.0,
            "stock": 16,
            "image": "./assets/watches/variants/watch-06-original.jpg",
            "strap_color": "Matte Diamond-Like Carbon (DLC) Steel Bracelet",
            "accent_color": "Monochrome Pitch Black Tactical Dial"
        },
        {
            "color_name": "Dark Tan",
            "color_code": "#8b5a2b",
            "sku": "AUR-OBS-06-TAN",
            "price": 7999.0,
            "discount_price": 9999.0,
            "stock": 12,
            "image": "./assets/watches/variants/watch-06-alternate.jpg",
            "strap_color": "Dark Tan Saddle Leather Strap",
            "accent_color": "Matte Black DLC Bezel with Tan Contrast"
        }
    ],
    "titan-classic": [
        {
            "color_name": "Gunmetal Steel & Graphite",
            "color_code": "#4a4e52",
            "sku": "AUR-TTN-07-GM",
            "price": 8499.0,
            "discount_price": 10499.0,
            "stock": 16,
            "image": "./assets/watches/variants/watch-07-original.jpg",
            "strap_color": "Ion-Plated Gunmetal Solid Link Bracelet",
            "accent_color": "Matte Slate Grey Dial with High Lume"
        },
        {
            "color_name": "Charcoal Grey",
            "color_code": "#36454f",
            "sku": "AUR-TTN-07-CHR",
            "price": 8499.0,
            "discount_price": 10499.0,
            "stock": 13,
            "image": "./assets/watches/variants/watch-07-alternate.jpg",
            "strap_color": "Charcoal Grey Tactical Diver Strap",
            "accent_color": "Gunmetal Ceramic Bezel with Slate Accents"
        }
    ],
    "auren-signature": [
        {
            "color_name": "18K Gold & Cognac Leather",
            "color_code": "#b8860b",
            "sku": "AUR-SIG-08-CGN",
            "price": 5799.0,
            "discount_price": 7299.0,
            "stock": 15,
            "image": "./assets/watches/variants/watch-08-original.jpg",
            "strap_color": "Hand-Stitched Cognac Brown Calfskin Leather",
            "accent_color": "18K Gold Guilloché Dial with Blued Hands"
        },
        {
            "color_name": "Olive / Dark Green",
            "color_code": "#354a21",
            "sku": "AUR-SIG-08-OLV",
            "price": 5799.0,
            "discount_price": 7299.0,
            "stock": 10,
            "image": "./assets/watches/variants/watch-08-alternate.jpg",
            "strap_color": "Olive Dark Green Calfskin Leather Strap",
            "accent_color": "18K Gold Case with Olive Leather Accents"
        }
    ],
    "monarch-black": [
        {
            "color_name": "Brushed Steel & Emerald Green",
            "color_code": "#1f5c38",
            "sku": "AUR-MNR-09-STL",
            "price": 6799.0,
            "discount_price": 8499.0,
            "stock": 13,
            "image": "./assets/watches/variants/watch-09-original.jpg",
            "strap_color": "Brushed Stainless Steel Link Bracelet",
            "accent_color": "Sunburst Emerald Green Dial with Cyclops Date"
        },
        {
            "color_name": "Coffee Brown",
            "color_code": "#4b3621",
            "sku": "AUR-MNR-09-COF",
            "price": 6799.0,
            "discount_price": 8499.0,
            "stock": 10,
            "image": "./assets/watches/variants/watch-09-alternate.jpg",
            "strap_color": "Coffee Brown Textured Diver Strap",
            "accent_color": "Emerald Green Dial with Coffee Brown Strap"
        }
    ],
    "silver-crest": [
        {
            "color_name": "Mirror Silver Links",
            "color_code": "#d1d5db",
            "sku": "AUR-SLV-10-SLV",
            "price": 5299.0,
            "discount_price": 6599.0,
            "stock": 20,
            "image": "./assets/watches/variants/watch-10-original.jpg",
            "strap_color": "Five-Link Jubilee Stainless Steel Bracelet",
            "accent_color": "Porcelain White Dial with Blued Seconds Hand"
        },
        {
            "color_name": "Deep Black",
            "color_code": "#121212",
            "sku": "AUR-SLV-10-BLK",
            "price": 5299.0,
            "discount_price": 6599.0,
            "stock": 15,
            "image": "./assets/watches/variants/watch-10-alternate.jpg",
            "strap_color": "Deep Black Crocodile Leather Strap with Metallic Buckle",
            "accent_color": "Porcelain White Dial with Black Crocodile Accent"
        }
    ]
}

def seed():
    init_db()
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Seed Site Settings
        settings = [
            ("shipping_fee", "0"),
            ("free_shipping_threshold", "0"),
            ("tax_percent", "0"), # Complimentary taxes included in MRP
            ("return_days", str(Config.DEFAULT_RETURN_DAYS)),
            ("cod_enabled", "true"),
            ("admin_name", Config.ADMIN_NAME),
            ("admin_phone", Config.ADMIN_PHONE),
            ("admin_location", Config.ADMIN_LOCATION),
            ("admin_email", Config.ADMIN_EMAIL),
            ("brand_name", "AURELIS TIMEPIECES"),
            ("currency", "INR"),
            ("currency_symbol", "₹"),
            ("warranty_period", "6 Months"),
            ("warranty_terms", "Every AURELIS timepiece is protected by our comprehensive 6-Month Manufacturer Warranty covering internal movement accuracy, mechanical defects, and artisan craftsmanship.")
        ]
        for key, val in settings:
            cursor.execute("""
                INSERT INTO site_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """, (key, val))
            
        # 2. Seed Admin User (Vikneshvaren)
        admin_pass_hash = generate_password_hash(Config.ADMIN_PASSWORD)
        cursor.execute("SELECT id FROM users WHERE email = ?", (Config.ADMIN_EMAIL,))
        existing_admin = cursor.fetchone()
        
        if not existing_admin:
            cursor.execute("""
                INSERT INTO users (name, email, phone, password_hash, role)
                VALUES (?, ?, ?, ?, 'admin')
            """, (Config.ADMIN_NAME, Config.ADMIN_EMAIL, Config.ADMIN_PHONE, admin_pass_hash))
            admin_user_id = cursor.lastrowid
        else:
            admin_user_id = existing_admin["id"]
            cursor.execute("""
                UPDATE users SET password_hash = ?, role = 'admin', name = ?, phone = ?
                WHERE id = ?
            """, (admin_pass_hash, Config.ADMIN_NAME, Config.ADMIN_PHONE, admin_user_id))
            
        # Admins table entry
        cursor.execute("SELECT id FROM admins WHERE user_id = ?", (admin_user_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO admins (user_id, name, email, phone, location)
                VALUES (?, ?, ?, ?, ?)
            """, (admin_user_id, Config.ADMIN_NAME, Config.ADMIN_EMAIL, Config.ADMIN_PHONE, Config.ADMIN_LOCATION))
            
        # 3. Seed Categories
        categories = [
            ("Classic Luxury", "classic-luxury", "Timeless heritage timepieces with hand-stitched leather and porcelain dials."),
            ("Chronographs", "chronographs", "Multi-register sports and split-second precision timepieces."),
            ("Minimalist", "minimalist", "Ultra-slim monochrome timepieces celebrating clean horological restraint."),
            ("Business Luxury", "business-luxury", "Executive timepieces featuring architectural steel link bracelets."),
            ("Modern Mesh", "modern-mesh", "Contemporary timepieces with supple Milanese woven steel mesh bands."),
            ("Masterpiece Collection", "masterpiece-collection", "Haute Horlogerie crown collection featuring flying tourbillons, grand complications, and architectural ceramic cases.")
        ]
        cat_map = {}
        for cname, cslug, cdesc in categories:
            cursor.execute("SELECT id FROM categories WHERE slug = ?", (cslug,))
            crow = cursor.fetchone()
            if not crow:
                cursor.execute("INSERT INTO categories (name, slug, description) VALUES (?, ?, ?)", (cname, cslug, cdesc))
                cat_map[cslug] = cursor.lastrowid
            else:
                cat_map[cslug] = crow["id"]
                
        # 4. Clean up old test transactions to ensure clean state
        cursor.execute("DELETE FROM return_items")
        cursor.execute("DELETE FROM returns")
        cursor.execute("DELETE FROM cancellations")
        cursor.execute("DELETE FROM refunds")
        cursor.execute("DELETE FROM payments")
        cursor.execute("DELETE FROM order_status_history")
        cursor.execute("DELETE FROM order_items")
        cursor.execute("DELETE FROM orders")
        cursor.execute("DELETE FROM inventory_logs")
        cursor.execute("DELETE FROM cart_items")
        cursor.execute("DELETE FROM wishlists")
        cursor.execute("DELETE FROM reviews")
        cursor.execute("DELETE FROM product_images")
        cursor.execute("DELETE FROM product_variants")
        cursor.execute("DELETE FROM products")
        cursor.execute("DELETE FROM coupons")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('products', 'product_variants', 'product_images', 'coupons')")
        
        for idx, w in enumerate(WATCHES):
            cursor.execute("SELECT id FROM products WHERE slug = ?", (w["slug"],))
            p_existing = cursor.fetchone()
            
            # Map category explicitly from dictionary
            cat_slug = w.get("category_slug", "classic-luxury")
            cat_id = cat_map.get(cat_slug, 1)
                
            specs_json = json.dumps(w["specs"])
            
            if not p_existing:
                cursor.execute("""
                    INSERT INTO products (
                        name, slug, brand, short_description, description, category_id, featured,
                        base_price, discount_price, specifications, warranty, return_days,
                        style, color, sku, stock_quantity, main_image, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    w["name"], w["slug"], "AURELIS", w["short_description"], w["description"],
                    cat_id, 1, w["base_price"], w["discount_price"], specs_json, "6-Month Warranty",
                    7, w["style"], w["color"], w["sku"], w["stock"], w["image"], 1
                ))
                product_id = cursor.lastrowid
            else:
                product_id = p_existing["id"]
                cursor.execute("""
                    UPDATE products SET
                        name = ?, brand = 'AURELIS', short_description = ?, description = ?,
                        category_id = ?, featured = 1, base_price = ?, discount_price = ?,
                        specifications = ?, warranty = '6-Month Warranty', return_days = 7,
                        style = ?, color = ?, sku = ?, stock_quantity = ?, main_image = ?, is_active = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    w["name"], w["short_description"], w["description"], cat_id,
                    w["base_price"], w["discount_price"], specs_json,
                    w["style"], w["color"], w["sku"], w["stock"], w["image"], product_id
                ))
                
            # Seed Variants
            if w["slug"] in CORE_10_VARIANTS:
                variants_data = CORE_10_VARIANTS[w["slug"]]
                cursor.execute("UPDATE products SET main_image = ? WHERE id = ?", (variants_data[0]["image"], product_id))
                cursor.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
                for v_idx, v in enumerate(variants_data):
                    cursor.execute("""
                        INSERT INTO product_variants (
                            product_id, color_name, color_code, sku, price, discount_price,
                            stock_quantity, reserved_quantity, low_stock_threshold, image_url,
                            strap_color, accent_color
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 3, ?, ?, ?)
                    """, (
                        product_id, v["color_name"], v["color_code"], v["sku"],
                        v["price"], v["discount_price"], v["stock"], v["image"],
                        v.get("strap_color", ""), v.get("accent_color", "")
                    ))
                    var_id = cursor.lastrowid
                    cursor.execute("""
                        INSERT INTO product_images (product_id, variant_id, image_url, is_primary, sort_order)
                        VALUES (?, ?, ?, ?, ?)
                    """, (product_id, var_id, v["image"], 1 if v_idx == 0 else 0, v_idx + 1))
            else:
                # Masterpiece Collection timepieces (Calibers 11-15) - Single Masterwork Edition
                cursor.execute("""
                    INSERT INTO product_variants (
                        product_id, color_name, color_code, sku, price, discount_price,
                        stock_quantity, reserved_quantity, low_stock_threshold, image_url,
                        strap_color, accent_color
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 3, ?, ?, ?)
                """, (
                    product_id, w["color"], "#d9ae55", w["sku"], w["base_price"], w["discount_price"],
                    w["stock"], w["image"], w["specs"].get("Strap", "Artisan Strap"), w["specs"].get("Dial", "Horological Dial")
                ))
                var_id = cursor.lastrowid
                cursor.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
                cursor.execute("""
                    INSERT INTO product_images (product_id, variant_id, image_url, is_primary, sort_order)
                    VALUES (?, ?, ?, 1, 1)
                """, (product_id, var_id, w["image"]))
            
        # 5. Seed Coupons
        coupons = [
            ("AURELIS10", "PERCENTAGE", 10.0, 2000.0, 500.0, 500, 1),
            ("WELCOME100", "FIXED", 100.0, 2000.0, 100.0, 200, 1),
            ("VIP200", "FIXED", 200.0, 2400.0, 200.0, 100, 1)
        ]
        for code, dtype, val, min_amt, max_disc, limit, per_user in coupons:
            cursor.execute("""
                INSERT INTO coupons (code, discount_type, discount_value, min_order_amount, max_discount, usage_limit, per_user_limit)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO NOTHING
            """, (code, dtype, val, min_amt, max_disc, limit, per_user))

        # 6. Seed Test Customer Inquiry Message in customer_messages
        cursor.execute("SELECT id FROM customer_messages LIMIT 1")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO customer_messages (name, email, phone, subject, message, status)
                VALUES (?, ?, ?, ?, ?, 'PENDING')
            """, (
                "Kavitha Raman",
                "kavitha.raman@example.com",
                "9876543210",
                "Watch 5 Strap Sizing Inquiry",
                "Hello Vikneshvaren, I am interested in acquiring the Royale Mesh watch. Can the Milanese mesh strap be easily adjusted for smaller wrists? Thank you."
            ))

    print(f"Database seeded successfully with EXACTLY {len(WATCHES)} luxury watches (prices starting from INR 5,299), 6-Month Warranty, and Admin details!")

if __name__ == "__main__":
    seed()
