"""Seed 100+ luxury dummy auctions with images, diverse sellers, statuses, and timers."""
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

from werkzeug.security import generate_password_hash
from app import app, db_execute, db_commit, _use_postgres

# ─── 12 Diverse Sellers (mix of verified and unverified) ─────────
SELLERS = [
    {"username": "RoyalAntiques",    "email": "contact@royalantiques.com",     "verified": True},
    {"username": "LuxuryAutoHub",    "email": "sales@luxuryauto.com",          "verified": False},
    {"username": "FineArtGallery",   "email": "curator@fineart.com",           "verified": True},
    {"username": "EliteJewels",      "email": "info@elitejewels.com",          "verified": False},
    {"username": "TechPioneer",      "email": "support@techpioneer.com",       "verified": False},
    {"username": "HauteHorology",    "email": "time@hautehorology.com",        "verified": True},
    {"username": "VintageVault",     "email": "hello@vintagevault.com",        "verified": False},
    {"username": "OpulentEstate",    "email": "sales@opulentestate.com",       "verified": True},
    {"username": "ArtisanCraft",     "email": "studio@artisancraft.com",       "verified": False},
    {"username": "PrimeCollectors",  "email": "info@primecollectors.com",      "verified": True},
    {"username": "GoldenEra",        "email": "curator@goldenera.com",         "verified": False},
    {"username": "SilkRouteArts",    "email": "contact@silkroutearts.com",     "verified": True},
]

# ─── Image pools per category (Unsplash, royalty-free) ───────────
IMAGES = {
    "art": [
        "https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?q=80&w=800",
        "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?q=80&w=800",
        "https://images.unsplash.com/photo-1549490349-8643362247b5?q=80&w=800",
        "https://images.unsplash.com/photo-1547891654-e66ed7ebb968?q=80&w=800",
        "https://images.unsplash.com/photo-1578926288207-a90a6e309f15?q=80&w=800",
        "https://images.unsplash.com/photo-1513364776144-60967b0f800f?q=80&w=800",
        "https://images.unsplash.com/photo-1518998053901-5348d3961a04?q=80&w=800",
        "https://images.unsplash.com/photo-1561214115-f2f134cc4912?q=80&w=800",
        "https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?q=80&w=800",
        "https://images.unsplash.com/photo-1605721911519-3dfeb3be25e7?q=80&w=800",
    ],
    "car": [
        "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?q=80&w=800",
        "https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=800",
        "https://images.unsplash.com/photo-1614162692292-7ac56d7f7f1e?q=80&w=800",
        "https://images.unsplash.com/photo-1544636331-e26879cd4d9b?q=80&w=800",
        "https://images.unsplash.com/photo-1580273916550-e323be2ae537?q=80&w=800",
        "https://images.unsplash.com/photo-1542362567-b07e54358753?q=80&w=800",
        "https://images.unsplash.com/photo-1525609004556-c46c43d3a5e5?q=80&w=800",
        "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?q=80&w=800",
        "https://images.unsplash.com/photo-1583121274602-3e2820c69888?q=80&w=800",
        "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?q=80&w=800",
    ],
    "antique": [
        "https://images.unsplash.com/photo-1581024317772-88229a435889?q=80&w=800",
        "https://images.unsplash.com/photo-1525044439130-141a0842db74?q=80&w=800",
        "https://images.unsplash.com/photo-1604571762756-4273a7f47b03?q=80&w=800",
        "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?q=80&w=800",
        "https://images.unsplash.com/photo-1596568362037-a6163422e8ba?q=80&w=800",
        "https://images.unsplash.com/photo-1587582345426-bf07f534e160?q=80&w=800",
        "https://images.unsplash.com/photo-1530982011887-3cc11cc85693?q=80&w=800",
        "https://images.unsplash.com/photo-1513519245088-0e12902e35ca?q=80&w=800",
        "https://images.unsplash.com/photo-1542435503-956c469947f6?q=80&w=800",
        "https://images.unsplash.com/photo-1560440021-33f9b867899d?q=80&w=800",
    ],
    "jewelry": [
        "https://images.unsplash.com/photo-1605100804763-247f67b3557e?q=80&w=800",
        "https://images.unsplash.com/photo-1535633302704-b04044a1074e?q=80&w=800",
        "https://images.unsplash.com/photo-1601121141461-9d6647bca1ed?q=80&w=800",
        "https://images.unsplash.com/photo-1611591437281-460bfbe1220a?q=80&w=800",
        "https://images.unsplash.com/photo-1603561591411-07134e71a2a9?q=80&w=800",
        "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?q=80&w=800",
        "https://images.unsplash.com/photo-1515562141589-67f0d932b7d6?q=80&w=800",
        "https://images.unsplash.com/photo-1573408301185-9146fe634ad0?q=80&w=800",
        "https://images.unsplash.com/photo-1602751584552-8ba73aad10e1?q=80&w=800",
        "https://images.unsplash.com/photo-1588444837495-c6cfeb53f32d?q=80&w=800",
    ],
    "electronics": [
        "https://images.unsplash.com/photo-1507584175317-bf49ea636a0d?q=80&w=800",
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?q=80&w=800",
        "https://images.unsplash.com/photo-1546868871-af0de0ae72be?q=80&w=800",
        "https://images.unsplash.com/photo-1593642532973-d31b6557fa68?q=80&w=800",
        "https://images.unsplash.com/photo-1519389950473-47ba0277781c?q=80&w=800",
        "https://images.unsplash.com/photo-1550009158-9ebf69173e03?q=80&w=800",
        "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?q=80&w=800",
        "https://images.unsplash.com/photo-1496348136257-1bc0249db665?q=80&w=800",
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?q=80&w=800",
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=800",
    ],
    "watch": [
        "https://images.unsplash.com/photo-1587836374828-4dbafa94cf0e?q=80&w=800",
        "https://images.unsplash.com/photo-1524592094714-0f0654e20314?q=80&w=800",
        "https://images.unsplash.com/photo-1522312346375-d1a52e2b99b3?q=80&w=800",
        "https://images.unsplash.com/photo-1547996160-81dfa63595aa?q=80&w=800",
        "https://images.unsplash.com/photo-1612817159949-195b6eb9e31a?q=80&w=800",
        "https://images.unsplash.com/photo-1523170335258-f5ed11844a49?q=80&w=800",
        "https://images.unsplash.com/photo-1539874754764-5a96559165b0?q=80&w=800",
        "https://images.unsplash.com/photo-1614164185128-e4ec99c436d7?q=80&w=800",
        "https://images.unsplash.com/photo-1509048191080-d2984bad6ae5?q=80&w=800",
        "https://images.unsplash.com/photo-1618220179428-22790b461013?q=80&w=800",
    ],
}

# ─── 120 Luxury Auction Items ────────────────────────────────────
AUCTIONS = [
    # ══════════════ ART (20 items) ══════════════
    {"cat": "art", "title": "Renaissance Madonna Oil Painting", "desc": "16th-century style oil painting on wood panel. Museum-quality frame with gold leaf. **Category:** Art", "price": 320000},
    {"cat": "art", "title": "Abstract Expressionist Canvas", "desc": "Large-format acrylic on canvas, 6ft x 4ft. Bold strokes in crimson and cobalt. **Category:** Art", "price": 185000},
    {"cat": "art", "title": "Japanese Woodblock Print — Mount Fuji", "desc": "Authentic Edo-period print by a master craftsman. Framed in paulownia wood. **Category:** Art", "price": 95000},
    {"cat": "art", "title": "Bronze Sculpture — Dancing Nataraja", "desc": "Handcrafted South Indian Chola-style bronze, 24 inches tall. Museum provenance. **Category:** Art", "price": 450000},
    {"cat": "art", "title": "Mughal Miniature Painting on Ivory", "desc": "19th-century court scene with intricate gold detailing. Certificate of authenticity. **Category:** Art", "price": 280000},
    {"cat": "art", "title": "Contemporary Glass Sculpture", "desc": "Murano glass art piece by a renowned Italian artist. Iridescent blues and greens. **Category:** Art", "price": 175000},
    {"cat": "art", "title": "Impressionist Garden Landscape", "desc": "Oil on linen capturing light through a Provençal garden. Signed and dated 1920. **Category:** Art", "price": 520000},
    {"cat": "art", "title": "Pop Art Silkscreen Print", "desc": "Limited edition 12/50 silkscreen with vibrant neon palette. Gallery-wrapped. **Category:** Art", "price": 78000},
    {"cat": "art", "title": "Tanjore Painting — Lord Krishna", "desc": "Traditional Thanjavur painting with 22K gold leaf and semi-precious stones. **Category:** Art", "price": 65000},
    {"cat": "art", "title": "Marble Venus de Milo Reproduction", "desc": "Hand-carved Carrara marble, life-size (80 inches). Museum-grade replica. **Category:** Art", "price": 890000},
    {"cat": "art", "title": "Persian Calligraphy on Silk", "desc": "Gold ink on hand-dyed silk. Quranic verses in Nastaliq script. **Category:** Art", "price": 145000},
    {"cat": "art", "title": "Surrealist Dream Canvas", "desc": "Dali-inspired surrealist oil painting, 48x36 inches. Floating clocks and melting landscapes. **Category:** Art", "price": 210000},
    {"cat": "art", "title": "Chinese Ink Wash Bamboo Scroll", "desc": "Hanging scroll painting on rice paper. Traditional sumi-e technique by a Beijing master. **Category:** Art", "price": 125000},
    {"cat": "art", "title": "Art Deco Bronze Panther", "desc": "Sleek 1930s Art Deco bronze panther on marble base. Patina preserved. **Category:** Art", "price": 195000},
    {"cat": "art", "title": "Digital NFT Art — Cosmic Journey", "desc": "Physical high-res print of award-winning digital art with NFT certificate. **Category:** Art", "price": 55000},
    {"cat": "art", "title": "Rajasthani Pichwai Painting", "desc": "Large-scale devotional painting depicting Shrinathji. Natural pigments on cloth. **Category:** Art", "price": 340000},
    {"cat": "art", "title": "African Tribal Mask Collection", "desc": "Set of 5 hand-carved West African ceremonial masks. Each with provenance document. **Category:** Art", "price": 89000},
    {"cat": "art", "title": "Watercolour — Himalayan Monastery", "desc": "Plein air watercolour of Hemis Monastery by a noted Indian landscape painter. **Category:** Art", "price": 72000},
    {"cat": "art", "title": "Cubist Still Life Oil Painting", "desc": "Post-Cubist oil on canvas, 36x48 inches. Geometric forms in warm earth tones. **Category:** Art", "price": 165000},
    {"cat": "art", "title": "Keith Haring Style Mural Panel", "desc": "Large acrylic mural panel (5ft x 8ft) in the style of 1980s street art. **Category:** Art", "price": 420000},

    # ══════════════ CAR (20 items) ══════════════
    {"cat": "car", "title": "1967 Ford Mustang Shelby GT500", "desc": "Fully restored in Highland Green. Matching numbers, 428ci V8 engine. **Category:** Car", "price": 8500000},
    {"cat": "car", "title": "Lamborghini Huracán Performante", "desc": "2019 model, Giallo Orion with carbon fiber aero kit. 3,200 km on odometer. **Category:** Car", "price": 32000000},
    {"cat": "car", "title": "1955 Mercedes-Benz 300SL Gullwing", "desc": "Silver with red leather interior. Matching luggage set. Concours-winning condition. **Category:** Car", "price": 95000000},
    {"cat": "car", "title": "Tesla Model S Plaid", "desc": "2024 model, Midnight Silver. Full Self-Driving, white interior. 800 km range. **Category:** Car", "price": 12500000},
    {"cat": "car", "title": "Aston Martin DB11 V12", "desc": "Magnetic Silver with obsidian black quilted leather. Only 8,000 km. **Category:** Car", "price": 25000000},
    {"cat": "car", "title": "Porsche 911 Turbo S Cabriolet", "desc": "Guards Red, Sport Chrono Package, PCCB brakes. 650 HP of pure engineering. **Category:** Car", "price": 28000000},
    {"cat": "car", "title": "Vintage Rolls-Royce Silver Cloud", "desc": "1962 Silver Cloud II. Cream over burgundy. Walnut burl dashboard. Chauffeur-ready. **Category:** Car", "price": 18000000},
    {"cat": "car", "title": "Ferrari 488 Spider", "desc": "Rosso Corsa with tan leather. Carbon fiber racing seats, JBL premium audio. **Category:** Car", "price": 35000000},
    {"cat": "car", "title": "Range Rover Autobiography LWB", "desc": "2023, Santorini Black. Executive rear seats, refrigerated coolbox. **Category:** Car", "price": 14000000},
    {"cat": "car", "title": "McLaren 720S Performance", "desc": "Papaya Spark orange, Carbon Fiber Luxury Pack, 4,000 km. Track-oriented beast. **Category:** Car", "price": 38000000},
    {"cat": "car", "title": "Bentley Continental GT Speed", "desc": "British Racing Green, 659 HP W12 engine. Mulliner driving specification. **Category:** Car", "price": 30000000},
    {"cat": "car", "title": "1970 Dodge Charger R/T Hemi", "desc": "Plum Crazy Purple. Numbers matching 426 Hemi. Full nut-and-bolt restoration. **Category:** Car", "price": 12000000},
    {"cat": "car", "title": "Mercedes-AMG GT Black Series", "desc": "Designo Graphite Grey. Most powerful AMG V8 production car ever built. **Category:** Car", "price": 42000000},
    {"cat": "car", "title": "Land Rover Defender V8 Bond Edition", "desc": "Santorini Black, 525 HP supercharged V8. James Bond 007 special edition. **Category:** Car", "price": 16500000},
    {"cat": "car", "title": "Bugatti Chiron Scale Model 1:8", "desc": "Official Bugatti licensed hand-assembled 1:8 model. Over 3,500 parts. **Category:** Car", "price": 850000},
    {"cat": "car", "title": "BMW M3 Competition xDrive", "desc": "2024, Isle of Man Green. 503 HP, M Carbon bucket seats. **Category:** Car", "price": 11500000},
    {"cat": "car", "title": "Jaguar E-Type Series 1 Roadster", "desc": "1966, British Racing Green. Enzo Ferrari called it the most beautiful car ever made. **Category:** Car", "price": 22000000},
    {"cat": "car", "title": "Maserati MC20 Cielo", "desc": "Blu Infinito, retractable glass roof. Nettuno V6, 630 HP. 1,200 km. **Category:** Car", "price": 36000000},
    {"cat": "car", "title": "Classic Ambassador Mark IV", "desc": "1975 Hindustan Ambassador in pristine white. Fully restored to concours standards. **Category:** Car", "price": 1800000},
    {"cat": "car", "title": "Toyota Land Cruiser Heritage Edition", "desc": "2024, Army Green. Off-road legend with Snorkel and locking differentials. **Category:** Car", "price": 9500000},

    # ══════════════ ANTIQUE (20 items) ══════════════
    {"cat": "antique", "title": "18th Century Victorian Vase", "desc": "Porcelain vase from the Victorian era with intricate floral gold leaf gilding. **Category:** Antique", "price": 45000},
    {"cat": "antique", "title": "Antique Gramophone — Columbia", "desc": "Fully functional 1910s Columbia gramophone with brass horn and 5 original records. **Category:** Antique", "price": 32000},
    {"cat": "antique", "title": "Mughal Era Silver Hookah", "desc": "Ornate silver hookah from the late Mughal period. Engraved floral motifs. **Category:** Antique", "price": 185000},
    {"cat": "antique", "title": "Persian Silk Carpet — 19th Century", "desc": "Hand-knotted Isfahan silk carpet, 8x10 ft. Over 1 million knots per sq meter. **Category:** Antique", "price": 750000},
    {"cat": "antique", "title": "Edwardian Mahogany Writing Desk", "desc": "Roll-top writing desk with secret compartments and original brass hardware. **Category:** Antique", "price": 120000},
    {"cat": "antique", "title": "Ming Dynasty Celadon Bowl", "desc": "Rare 15th-century celadon glazed bowl. Museum-certified with provenance. **Category:** Antique", "price": 2500000},
    {"cat": "antique", "title": "WWI British Officer's Sword", "desc": "1914 pattern officer's sword with leather scabbard. Engraved regiment insignia. **Category:** Antique", "price": 65000},
    {"cat": "antique", "title": "Art Nouveau Tiffany Lamp", "desc": "Original leaded glass Tiffany lamp, Dragonfly pattern. Bronze base. Electrified. **Category:** Antique", "price": 1200000},
    {"cat": "antique", "title": "Vintage Rolleiflex Twin-Lens Camera", "desc": "1950s Rolleiflex 2.8F in excellent working condition. Original leather case. **Category:** Antique", "price": 48000},
    {"cat": "antique", "title": "Indian Ivory Chess Set", "desc": "Pre-ban hand-carved ivory Rajasthani chess set with rosewood board. **Category:** Antique", "price": 350000},
    {"cat": "antique", "title": "Georgian Silver Tea Service", "desc": "Complete 5-piece sterling silver tea service, London 1820. Hallmarked. **Category:** Antique", "price": 285000},
    {"cat": "antique", "title": "Japanese Samurai Katana", "desc": "Edo-period folded steel katana with tsuba guard. Signed by the swordsmith. **Category:** Antique", "price": 920000},
    {"cat": "antique", "title": "Victorian Jewellery Box", "desc": "Walnut burl box with mother-of-pearl inlay. Red velvet interior. Multiple trays. **Category:** Antique", "price": 38000},
    {"cat": "antique", "title": "1920s Globe Bar Cabinet", "desc": "Italian-made antique globe that opens to reveal a fully stocked bar cabinet. **Category:** Antique", "price": 145000},
    {"cat": "antique", "title": "Rare Indian Postage Stamp — 1854", "desc": "Half anna lithograph stamp in unused condition. Extremely rare for collectors. **Category:** Antique", "price": 580000},
    {"cat": "antique", "title": "Crystal Decanter Set — Waterford", "desc": "Set of 6 crystal decanters with matching glasses. Original Waterford packaging. **Category:** Antique", "price": 75000},
    {"cat": "antique", "title": "French Ormolu Mantle Clock", "desc": "19th-century gilded bronze clock with porcelain face. Chimes on the hour. **Category:** Antique", "price": 210000},
    {"cat": "antique", "title": "Ottoman Empire Ceremonial Dagger", "desc": "Gold and jewel-encrusted ceremonial dagger, circa 1700s. Provenance documented. **Category:** Antique", "price": 1500000},
    {"cat": "antique", "title": "Vintage Nautical Sextant", "desc": "Brass marine sextant by Kelvin & Hughes, London. Complete with mahogany box. **Category:** Antique", "price": 42000},
    {"cat": "antique", "title": "Hand-Painted Delft Tile Panel", "desc": "18th-century Dutch Delft blue-and-white tile panel (12 tiles). Windmill scene. **Category:** Antique", "price": 95000},

    # ══════════════ JEWELRY (20 items) ══════════════
    {"cat": "jewelry", "title": "Diamond Solitaire Ring — 3 Carat", "desc": "Brilliant-cut VS1 diamond in platinum setting. GIA certified. **Category:** Jewelry", "price": 1800000},
    {"cat": "jewelry", "title": "Ruby & Diamond Necklace", "desc": "Burmese ruby cabochon surrounded by 4 carats of diamonds. 18K white gold. **Category:** Jewelry", "price": 2500000},
    {"cat": "jewelry", "title": "Emerald Tennis Bracelet", "desc": "Colombian emeralds (12 carats total) set in 18K yellow gold links. **Category:** Jewelry", "price": 950000},
    {"cat": "jewelry", "title": "South Sea Pearl Earrings", "desc": "Matching pair of 14mm golden South Sea pearls. Diamond-studded 18K settings. **Category:** Jewelry", "price": 420000},
    {"cat": "jewelry", "title": "Art Deco Sapphire Brooch", "desc": "1920s Art Deco platinum brooch with a 5-carat Kashmir sapphire center. **Category:** Jewelry", "price": 3200000},
    {"cat": "jewelry", "title": "Tanzanite Cocktail Ring", "desc": "Exceptional 8-carat AAA tanzanite surrounded by brilliant-cut diamonds. **Category:** Jewelry", "price": 680000},
    {"cat": "jewelry", "title": "Kundan Bridal Set", "desc": "Traditional Rajasthani kundan bridal jewelry set: necklace, earrings, maang tikka, and bangles. **Category:** Jewelry", "price": 550000},
    {"cat": "jewelry", "title": "Men's Diamond Cufflinks", "desc": "18K white gold cufflinks with 1 carat of pavé diamonds each. Black onyx accent. **Category:** Jewelry", "price": 185000},
    {"cat": "jewelry", "title": "Vintage Cartier Love Bracelet", "desc": "Iconic 18K yellow gold Cartier Love bracelet. Original box and screwdriver. **Category:** Jewelry", "price": 450000},
    {"cat": "jewelry", "title": "Pink Diamond Pendant", "desc": "Rare Argyle pink diamond (0.5 carat, Fancy Intense) in rose gold halo setting. **Category:** Jewelry", "price": 4500000},
    {"cat": "jewelry", "title": "Polki Diamond Choker", "desc": "Uncut polki diamonds in 22K gold. Traditional Hyderabadi craftsmanship. **Category:** Jewelry", "price": 780000},
    {"cat": "jewelry", "title": "Men's Signet Ring — Gold", "desc": "Heavy 22K gold signet ring with custom family crest engraving. **Category:** Jewelry", "price": 125000},
    {"cat": "jewelry", "title": "Jade Bangle — Imperial Green", "desc": "Type A certified Burmese jade bangle. Intense imperial green colour. **Category:** Jewelry", "price": 1200000},
    {"cat": "jewelry", "title": "Diamond Anklet — 18K White Gold", "desc": "Delicate diamond anklet with 3 carats of brilliant-cut stones. **Category:** Jewelry", "price": 320000},
    {"cat": "jewelry", "title": "Opal & Diamond Festoon Necklace", "desc": "Australian black opal centerpiece (8 carats) with diamond festoon. Platinum. **Category:** Jewelry", "price": 2800000},
    {"cat": "jewelry", "title": "Temple Jewelry — Lakshmi Set", "desc": "Traditional South Indian temple jewelry set in gold-plated silver with kemp stones. **Category:** Jewelry", "price": 95000},
    {"cat": "jewelry", "title": "Platinum Wedding Band Set", "desc": "His and hers matching platinum bands with channel-set diamonds. **Category:** Jewelry", "price": 280000},
    {"cat": "jewelry", "title": "Coral & Gold Necklace", "desc": "Mediterranean red coral beads strung with 22K gold spacers and clasp. **Category:** Jewelry", "price": 165000},
    {"cat": "jewelry", "title": "Sapphire Stud Earrings", "desc": "Ceylon blue sapphires (2 carats each) in 18K white gold basket settings. **Category:** Jewelry", "price": 520000},
    {"cat": "jewelry", "title": "Antique Cameo Brooch — Victorian", "desc": "Hand-carved shell cameo in a 15K gold frame with seed pearl border. **Category:** Jewelry", "price": 75000},

    # ══════════════ ELECTRONICS (10 items) ══════════════
    {"cat": "electronics", "title": "Professional 8K Cinema Camera", "desc": "Broadcast-grade 8K cinema camera with PL mount. Internal RAW recording. **Category:** Electronics", "price": 1500000},
    {"cat": "electronics", "title": "Bang & Olufsen Beolab 90 Speakers", "desc": "Pair of flagship floor-standing speakers. 18 drivers per unit. Active room adaptation. **Category:** Electronics", "price": 5500000},
    {"cat": "electronics", "title": "Leica M11 Rangefinder Camera", "desc": "Black chrome body, 60MP full-frame sensor. Includes Summicron 35mm f/2 lens. **Category:** Electronics", "price": 820000},
    {"cat": "electronics", "title": "Custom Water-Cooled Gaming PC", "desc": "Dual RTX 5090, Intel i9-15900K, 128GB RAM, custom hard-line cooling loop. **Category:** Electronics", "price": 950000},
    {"cat": "electronics", "title": "Devialet Phantom II 108 dB", "desc": "Compact high-fidelity wireless speaker. Iconic design with 108 dB output. **Category:** Electronics", "price": 280000},
    {"cat": "electronics", "title": "DJI Inspire 3 Professional Drone", "desc": "8K cinema drone with dual-operator capability. Full-frame Hasselblad camera. **Category:** Electronics", "price": 1200000},
    {"cat": "electronics", "title": "McIntosh MA12000 Amplifier", "desc": "Flagship hybrid integrated amplifier. 350W per channel. Iconic blue watt meters. **Category:** Electronics", "price": 1800000},
    {"cat": "electronics", "title": "Sony A1 Mirrorless Camera Body", "desc": "50MP stacked CMOS sensor, 30fps, 8K video. Professional sports photography. **Category:** Electronics", "price": 520000},
    {"cat": "electronics", "title": "Apple Vision Pro — 1TB", "desc": "Spatial computing headset, 1TB storage. Zeiss prescription lenses included. **Category:** Electronics", "price": 450000},
    {"cat": "electronics", "title": "Hasselblad X2D 100C Medium Format", "desc": "100 megapixel medium format camera. 16-bit RAW. Swedish precision optics. **Category:** Electronics", "price": 680000},

    # ══════════════ WATCH (10 items) ══════════════
    {"cat": "watch", "title": "Luxury Chronograph — Rose Gold", "desc": "Swiss-made chronograph with perpetual calendar. 18K rose gold case, alligator strap. **Category:** Watch", "price": 2800000},
    {"cat": "watch", "title": "Diver's Watch — Titanium 300M", "desc": "Professional diver's watch rated to 300 metres. Titanium case with ceramic bezel. **Category:** Watch", "price": 450000},
    {"cat": "watch", "title": "Vintage Dress Watch — 1960s", "desc": "Ultra-thin manual wind dress watch. 18K yellow gold case, original box and papers. **Category:** Watch", "price": 1200000},
    {"cat": "watch", "title": "Skeleton Tourbillon — Limited", "desc": "Limited edition (25/100) skeleton dial with flying tourbillon. Platinum case. **Category:** Watch", "price": 8500000},
    {"cat": "watch", "title": "GMT Master II — Meteorite Dial", "desc": "Luxury GMT watch with genuine meteorite dial. Oystersteel and Everose gold. **Category:** Watch", "price": 3500000},
    {"cat": "watch", "title": "Grand Complication — Minute Repeater", "desc": "Handcrafted minute repeater with cathedral gongs. 18K white gold. 5-year waiting list piece. **Category:** Watch", "price": 15000000},
    {"cat": "watch", "title": "Pilot's Watch — Big Case 46mm", "desc": "Aviator-style pilot watch with power reserve indicator. Brown calfskin strap. **Category:** Watch", "price": 680000},
    {"cat": "watch", "title": "Lady's Diamond Watch — Platinum", "desc": "Full diamond-set platinum case with mother-of-pearl dial. Swiss quartz movement. **Category:** Watch", "price": 4200000},
    {"cat": "watch", "title": "Racing Chronograph — Carbon Fiber", "desc": "Lightweight carbon fiber chronograph designed for motorsport. Tachymeter bezel. **Category:** Watch", "price": 520000},
    {"cat": "watch", "title": "World Timer — Enamel Dial", "desc": "Grand Feu enamel world-time dial showing 24 cities. 18K white gold, 39mm. **Category:** Watch", "price": 6800000},
]

def seed():
    with app.app_context():
        print(f"Connecting to {'PostgreSQL' if _use_postgres() else 'SQLite'}...")

        # ── Clean up old seed data ──────────────────────────────
        all_seller_usernames = tuple(s["username"] for s in SELLERS)
        try:
            if _use_postgres():
                db_execute("DELETE FROM bids WHERE auction_id IN (SELECT id FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username = ANY(%s)))", ([s["username"] for s in SELLERS],))
                db_execute("DELETE FROM transactions WHERE auction_id IN (SELECT id FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username = ANY(%s)))", ([s["username"] for s in SELLERS],))
                db_execute("DELETE FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username = ANY(%s))", ([s["username"] for s in SELLERS],))
            else:
                placeholders = ','.join('?' * len(all_seller_usernames))
                db_execute(f"DELETE FROM bids WHERE auction_id IN (SELECT id FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username IN ({placeholders})))", all_seller_usernames)
                try:
                    db_execute(f"DELETE FROM transactions WHERE auction_id IN (SELECT id FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username IN ({placeholders})))", all_seller_usernames)
                except Exception:
                    pass
                db_execute(f"DELETE FROM auctions WHERE seller_id IN (SELECT id FROM users WHERE username IN ({placeholders}))", all_seller_usernames)
            db_commit()
            print("Cleared previous seed data.")
        except Exception as e:
            print(f"Notice: Could not clear previous data: {e}")

        # ── Create / ensure sellers ─────────────────────────────
        seller_map = {}
        for s in SELLERS:
            row = db_execute("SELECT id FROM users WHERE username = ?", (s["username"],)).fetchone()
            if not row:
                db_execute(
                    "INSERT INTO users (username, email, password, role, is_verified) VALUES (?, ?, ?, ?, ?)",
                    (s["username"], s["email"], generate_password_hash("demo123"), "seller", s["verified"])
                )
                db_commit()
                row = db_execute("SELECT id FROM users WHERE username = ?", (s["username"],)).fetchone()
                print(f"  Created seller: {s['username']} {'✓ verified' if s['verified'] else ''}")
            else:
                # Update verification status
                db_execute("UPDATE users SET is_verified = ? WHERE id = ?", (s["verified"], row["id"]))
                db_commit()
            seller_map[s["username"]] = row["id"]

        # ── Create a dummy bidder ───────────────────────────────
        bidder = db_execute("SELECT id FROM users WHERE username = ?", ("LuxuryBidder",)).fetchone()
        if not bidder:
            db_execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                ("LuxuryBidder", "bidder@luxurybidder.com", generate_password_hash("demo123"), "bidder")
            )
            db_commit()
            bidder = db_execute("SELECT id FROM users WHERE username = ?", ("LuxuryBidder",)).fetchone()
            print("  Created bidder: LuxuryBidder")
        bidder_id = bidder["id"]

        # ── Insert auctions with varied statuses & timers ───────
        now = datetime.utcnow()
        seller_names = list(seller_map.keys())
        statuses = ["live", "live", "live", "upcoming", "upcoming", "closed", "closed"]
        # Timer variety: various end-day offsets for live/upcoming
        live_end_days = [3, 7, 14, 21, 30, 45, 60, 70, 90]
        upcoming_start_days = [1, 3, 5, 10, 15, 30]

        total = len(AUCTIONS)
        for idx, item in enumerate(AUCTIONS):
            seller_name = seller_names[idx % len(seller_names)]
            seller_id = seller_map[seller_name]
            status = statuses[idx % len(statuses)]
            image = IMAGES[item["cat"]][idx % len(IMAGES[item["cat"]])]

            if status == "live":
                start_time = now - timedelta(days=random.randint(1, 5))
                end_offset = live_end_days[idx % len(live_end_days)]
                end_time = now + timedelta(days=end_offset, hours=random.randint(1, 23))
            elif status == "upcoming":
                start_offset = upcoming_start_days[idx % len(upcoming_start_days)]
                start_time = now + timedelta(days=start_offset)
                end_time = start_time + timedelta(days=random.choice([7, 14, 30, 60, 70]))
            else:  # closed
                start_time = now - timedelta(days=random.randint(15, 90))
                end_time = now - timedelta(days=random.randint(1, 14))

            start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            min_inc = max(500, int(item["price"] * 0.02))

            db_execute(
                "INSERT INTO auctions (seller_id, title, description, image, starting_price, min_increment, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (seller_id, item["title"], item["desc"], image, float(item["price"]), float(min_inc), start_str, end_str, status)
            )
            db_commit()

            # Get the auction ID
            auction_row = db_execute("SELECT id FROM auctions ORDER BY id DESC LIMIT 1").fetchone()
            auction_id = auction_row["id"]

            # Add 2-5 bids for live/closed auctions
            if status in ("live", "closed"):
                num_bids = random.randint(2, 5)
                curr_price = item["price"]
                for b in range(num_bids):
                    curr_price += random.randint(min_inc, min_inc * 3)
                    db_execute(
                        "INSERT INTO bids (auction_id, bidder_id, amount) VALUES (?, ?, ?)",
                        (auction_id, bidder_id, float(curr_price))
                    )
                db_commit()

            print(f"  [{idx+1}/{total}] {status.upper():8s} | {item['cat']:12s} | {item['title'][:45]}")

        # ── Generate dummy transactions for verified sellers ────
        print("\nGenerating completed trades for verified sellers...")
        for s in SELLERS:
            if s["verified"]:
                sid = seller_map[s["username"]]
                for i in range(12):
                    db_execute(
                        "INSERT INTO auctions (seller_id, title, description, starting_price, min_increment, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (sid, f"Completed Sale #{i+1}", "System-generated for verification", 100, 10, "2024-01-01 00:00:00", "2024-01-02 00:00:00", "closed")
                    )
                    db_commit()
                    dummy_id = db_execute("SELECT id FROM auctions ORDER BY id DESC LIMIT 1").fetchone()["id"]
                    db_execute(
                        "INSERT INTO transactions (auction_id, winner_id, amount, status) VALUES (?, ?, ?, ?)",
                        (dummy_id, bidder_id, 150.0, "completed")
                    )
                    db_commit()
                print(f"  Added 12 trades for verified seller: {s['username']}")

        print(f"\n✅ Successfully seeded {total} luxury auctions across {len(set(a['cat'] for a in AUCTIONS))} categories!")
        print(f"   Sellers: {len(SELLERS)} ({sum(1 for s in SELLERS if s['verified'])} verified, {sum(1 for s in SELLERS if not s['verified'])} unverified)")

if __name__ == "__main__":
    seed()
