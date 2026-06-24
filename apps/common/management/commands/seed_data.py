import random
from django.core.management.base import BaseCommand
from faker import Faker

fake = Faker()

# ---------------------------------------------------------------------------
# Realistic category → product templates
# ---------------------------------------------------------------------------
CATEGORY_PRODUCTS = {
    "Electronics": [
        "iPhone 15", "iPhone 15 Pro", "iPhone 14", "Samsung Galaxy S24",
        "Samsung Galaxy S23 Ultra", "OnePlus 12", "Xiaomi 14 Pro", "Google Pixel 8",
        "Sony Xperia 1 V", "Motorola Edge 40",
        "Dell Inspiron 15", "HP Pavilion Laptop", "Lenovo IdeaPad 3",
        "Asus VivoBook 15", "Acer Aspire 5", "MacBook Air M2", "MacBook Pro 14",
        "HP Spectre x360", "Lenovo ThinkPad X1 Carbon", "Dell XPS 13",
        "Apple Watch Series 9", "Samsung Galaxy Watch 6", "Fitbit Charge 6",
        "Garmin Fenix 7", "Amazfit GTR 4",
        "Sony WH-1000XM5 Headphones", "JBL Tune 770NC", "Bose QuietComfort 45",
        "Sennheiser HD 450BT", "boAt Rockerz 450",
        "JBL Bluetooth Speaker", "Sony SRS-XB13", "Bose SoundLink Flex",
        "Logitech Wireless Mouse", "Logitech MX Master 3", "Razer DeathAdder V3",
        "HP LaserJet Printer", "Canon PIXMA G3010", "Epson EcoTank L3250",
        "iPad Air 5th Gen", "Samsung Galaxy Tab S9", "Lenovo Tab P12",
        "LG 32-inch 4K Monitor", "Dell 27-inch IPS Monitor", "BenQ 24-inch Gaming Monitor",
        "Western Digital 1TB SSD", "Seagate 2TB HDD", "Samsung 970 EVO SSD",
        "Corsair 16GB RAM DDR5", "Kingston 32GB USB Drive",
        "Anker 65W GaN Charger", "Belkin 10000mAh Power Bank",
    ],
    "Fashion": [
        "Nike Air Max 270", "Nike Running Shoes", "Adidas Ultraboost 23",
        "Puma RS-X Sneakers", "Reebok Classic Leather", "New Balance 574",
        "Nike Sports T-Shirt", "Adidas Sports T-Shirt", "Puma Dry Cell Polo",
        "Levi's 511 Slim Jeans", "Wrangler Regular Fit Jeans", "H&M Stretch Chinos",
        "Allen Solly Formal Shirt", "Van Heusen Slim Fit Shirt", "Peter England Casual Shirt",
        "Zara Women Floral Dress", "H&M A-Line Skirt", "Mango Wrap Dress",
        "Woodland Leather Boots", "Red Tape Loafers", "Bata Casual Shoes",
        "Ray-Ban Aviator Sunglasses", "Fastrack UV Protection Shades",
        "Tommy Hilfiger Belt", "Fossil Leather Wallet",
        "Nike Dri-FIT Running Shorts", "Adidas Track Pants", "Puma Joggers",
        "Titan Analog Watch", "Fossil Gen 6 Smartwatch",
        "Lavie Handbag", "Caprese Tote Bag", "Wildcraft Backpack 30L",
    ],
    "Grocery": [
        "Tata Tea Gold 1kg", "Nescafe Classic 200g", "Bru Instant Coffee 100g",
        "Aashirvaad Atta 10kg", "Fortune Sunflower Oil 5L", "Saffola Gold Oil 2L",
        "Maggi Noodles 12-pack", "Yippee Masala Noodles", "Knorr Soup Packet",
        "Amul Butter 500g", "Mother Dairy Ghee 1L", "Nestlé Condensed Milk 400g",
        "Britannia Marie Gold Biscuits", "Parle-G Biscuits Family Pack",
        "Lay's Classic Chips 100g", "Kurkure Masala Munch", "Haldiram Bhujia 400g",
        "Tropicana Orange Juice 1L", "Real Fruit Power Juice", "Minute Maid Pulpy Orange",
        "Patanjali Honey 500g", "Dabur Chyawanprash 1kg",
        "Tata Salt 1kg", "Catch Black Pepper Powder", "MDH Garam Masala 100g",
        "Basmati Rice 5kg Premium", "Toor Dal 1kg", "Chana Dal 1kg",
    ],
    "Home & Kitchen": [
        "Prestige Pressure Cooker 5L", "Hawkins Contura Cooker 3L",
        "Philips Air Fryer HD9252", "Bajaj Mixer Grinder 750W",
        "Butterfly Mixer Grinder 3 Jar", "Preethi Eco Plus Mixer",
        "Milton Thermosteel Flask 1L", "Cello Stainless Steel Bottle",
        "Borosil Glass Bowl Set", "La Opala Dinner Set 27pcs",
        "Godrej Refrigerator 260L", "LG 7kg Washing Machine",
        "Whirlpool 1.5 Ton AC", "Havells Pedestal Fan",
        "Crompton LED Ceiling Fan", "Orient Electric Fan 48-inch",
        "Asian Paints Royale Paint 4L", "Pidilite Fevicol 1kg",
        "IKEA Study Table", "Nilkamal Plastic Chair",
        "Cello Bubble Bed Sheet Queen", "D'Décor Curtains Set",
        "Surf Excel Matic 3kg", "Ariel Liquid Detergent 2L",
        "Pril Dishwash Gel 750ml", "Colin Glass Cleaner 500ml",
        "Prestige Non-Stick Tawa", "Meyer Hard Anodised Kadai",
    ],
    "Sports": [
        "Yonex Badminton Racket", "Victor Thruster F Racket",
        "Cosco Football Size 5", "Nivia Storm Football",
        "SG Cricket Bat English Willow", "SS Ton Cricket Bat",
        "Kookaburra Pace Cricket Ball", "SG Practice Cricket Ball",
        "Boldfit Yoga Mat 6mm", "Strauss Anti-Slip Yoga Mat",
        "Skullcandy Sport Earphones", "JBL Endurance Run Earphones",
        "Fitkit FK500 Dumbbell Set", "Kore PVC Dumbell 10kg Pair",
        "Yonex Badminton Shuttle Cock", "Cosco Smash Shuttle Cock",
        "Nivia Basketball Size 7", "Spalding NBA Street Basketball",
        "Adidas Gym Gloves", "Nike Training Gloves",
        "Decathlon Swimming Goggles", "Speedo Swim Goggles",
        "Cosco Tennis Racket", "Head Speed MP Tennis Racket",
        "Strauss Skipping Rope", "Boldfit Jump Rope Steel",
        "Puma Sports Water Bottle 750ml", "Nalgene Wide Mouth Bottle",
    ],
    "Books": [
        "Atomic Habits by James Clear", "The Psychology of Money",
        "Rich Dad Poor Dad", "Think and Grow Rich",
        "The Alchemist by Paulo Coelho", "Ikigai: The Japanese Secret",
        "Deep Work by Cal Newport", "Digital Minimalism",
        "Sapiens: A Brief History", "21 Lessons for the 21st Century",
        "The Lean Startup", "Zero to One by Peter Thiel",
        "Clean Code by Robert Martin", "The Pragmatic Programmer",
        "Designing Data-Intensive Applications", "System Design Interview",
        "Harry Potter Box Set", "The Lord of the Rings",
        "Wings of Fire by APJ Abdul Kalam", "My Experiments with Truth",
        "NCERT Physics Class 12", "HC Verma Concepts of Physics",
        "RD Sharma Mathematics", "RS Aggarwal Quantitative Aptitude",
        "Indian Polity by Laxmikanth", "UPSC General Studies Paper 1",
    ],
    "Beauty": [
        "Lakme Absolute Foundation", "Maybelline Fit Me Foundation",
        "L'Oréal Revitalift Cream", "Olay Total Effects Moisturizer",
        "Neutrogena Hydro Boost Gel", "Himalaya Moisturizing Cream",
        "Dove Body Lotion 400ml", "Nivea Soft Moisturizing Cream",
        "TRESemmé Keratin Shampoo", "Pantene Pro-V Shampoo",
        "Head & Shoulders Anti-Dandruff", "Dove Intense Repair Shampoo",
        "Mamaearth Onion Hair Oil", "Indulekha Bringha Hair Oil",
        "Gillette Mach3 Razor", "Gillette Fusion5 ProGlide",
        "Axe Dark Temptation Deo", "Park Avenue Deo Spray",
        "Lakme Eyeconic Kajal", "Maybelline Colossal Kajal",
        "Biotique Bio Papaya Scrub", "Lotus Herbals White Glow Scrub",
        "Himalaya Face Wash Neem", "Cetaphil Gentle Skin Cleanser",
        "Vaseline Intensive Care Lotion", "WOW Vitamin C Serum",
        "Plum Green Tea Face Mask", "mCaffeine Coffee Face Pack",
    ],
    "Automotive": [
        "Bosch Car Battery 35Ah", "Exide Mileage Battery 45Ah",
        "3M Car Wax Polish 200g", "Turtle Wax Ice Spray",
        "Michelin Tyre 185/65 R15", "Apollo Alnac 4G Tyre",
        "Varta Car Battery 60Ah", "Amaron Pro Car Battery",
        "Car Seat Cover PU Leather", "Auto Kraft Seat Cover Set",
        "Garmin Dash Cam 47", "70mai Dash Cam A400",
        "Portronics Car Bluetooth FM", "Boat Bluetooth Car Kit",
        "Amsoil 5W-30 Engine Oil 1L", "Castrol GTX 10W-40 1L",
        "Hella Halogen Bulb H4", "Philips CrystalVision H4 Bulb",
        "Bosch Wiper Blade 21-inch", "Valeo Wiper Blade Pair",
        "3M Car Interior Cleaner", "Meguiar's Quick Detailer",
        "AutoSun Car Phone Holder", "Olixar Car Phone Mount",
    ],
    "Office Supplies": [
        "Classmate Spiral Notebook A4", "Navneet Youva Notebook 200 Pages",
        "Pilot G2 Gel Pen 10-pack", "Reynolds Trimax Ballpen Set",
        "Faber-Castell Colour Pencils 24", "Staedtler Pencil Set HB",
        "HP 802 Ink Cartridge Black", "Canon PG-745 Ink Cartridge",
        "3M Post-It Notes 100 Sheets", "Kores Sticky Notes Yellow",
        "Scotch Transparent Tape 18mm", "Oddy Tape Dispenser Set",
        "Kangaro Stapler HD-10", "Kangaro Stapler Pins 1000pcs",
        "Maped Sharpener Twin Hole", "Apsara Platinum Eraser Pack",
        "Leitz WOW Hole Punch", "Kangaro 2-Hole Punch",
        "ACCO Binder Clips 25mm", "Gem Paper Clips 100pcs",
        "Duracell AAA Battery 10-pack", "Eveready AA Battery 8-pack",
        "HP A4 Paper 75gsm 500 Sheets", "JK Copier A4 Paper 500 Sheets",
        "Godrej Interio Office Chair", "Green Soul Ergonomic Chair",
    ],
    "Toys": [
        "LEGO Classic Creative Set", "LEGO Technic Car Model",
        "Hot Wheels 10-Car Pack", "Matchbox Die-Cast Vehicles",
        "Barbie Dreamhouse", "Barbie Fashion Doll Set",
        "Funskool Monopoly", "Hasbro Scrabble Classic",
        "UNO Card Game", "Jenga Classic Block Game",
        "Nerf N-Strike Blaster", "Nerf Fortnite Blaster",
        "Play-Doh Modelling Compound 10-pack", "Crayola Art Set 100pcs",
        "Remote Control Car 1:18 Scale", "Webby RC Helicopter",
        "Rubik's Cube 3x3", "Rubik's Speed Cube",
        "Funskool Snakes & Ladders", "Hasbro Sorry! Board Game",
        "Fisher-Price Baby Activity Gym", "Chicco Baby Walker",
        "Marvel Iron Man Action Figure", "DC Batman Figure 12-inch",
        "Peppa Pig Playhouse Set", "PAW Patrol Lookout Tower",
        "Mega Bloks First Builders 80pcs", "K'NEX Building Set",
    ],
}

STORE_NAMES = [
    ("Chennai Central Store", "Chennai, Tamil Nadu"),
    ("Bangalore Tech Store", "Bangalore, Karnataka"),
    ("Mumbai Retail Hub", "Mumbai, Maharashtra"),
    ("Hyderabad Electronics Center", "Hyderabad, Telangana"),
    ("Delhi Shopping Point", "New Delhi, Delhi"),
    ("Pune Mega Store", "Pune, Maharashtra"),
    ("Coimbatore Mart", "Coimbatore, Tamil Nadu"),
    ("Ambur Retail Center", "Ambur, Tamil Nadu"),
    ("Kolkata Bazaar", "Kolkata, West Bengal"),
    ("Ahmedabad Trade Center", "Ahmedabad, Gujarat"),
    ("Jaipur Pink City Store", "Jaipur, Rajasthan"),
    ("Surat Diamond Mall", "Surat, Gujarat"),
    ("Kochi Spice Market Store", "Kochi, Kerala"),
    ("Nagpur Central Retail", "Nagpur, Maharashtra"),
    ("Lucknow Nawabi Store", "Lucknow, Uttar Pradesh"),
    ("Chandigarh City Store", "Chandigarh, Punjab"),
    ("Indore MegaMart", "Indore, Madhya Pradesh"),
    ("Bhopal City Center Store", "Bhopal, Madhya Pradesh"),
    ("Visakhapatnam Port Store", "Visakhapatnam, Andhra Pradesh"),
    ("Patna Grand Bazaar", "Patna, Bihar"),
    ("Mysore Heritage Store", "Mysore, Karnataka"),
    ("Tiruppur Textile Hub", "Tiruppur, Tamil Nadu"),
]


class Command(BaseCommand):
    help = 'Seed the database with realistic e-commerce dummy data.'

    def handle(self, *args, **options):
        from apps.products.models import Category, Product
        from apps.stores.models import Store, Inventory

        self.stdout.write('Seeding categories...')
        categories = {}
        for name in CATEGORY_PRODUCTS:
            cat, _ = Category.objects.get_or_create(name=name)
            categories[name] = cat
        self.stdout.write(self.style.SUCCESS(f'  {len(categories)} categories ready.'))

        self.stdout.write('Seeding products...')
        existing_titles = set(Product.objects.values_list('title', flat=True))
        products_to_create = []

        for cat_name, titles in CATEGORY_PRODUCTS.items():
            cat = categories[cat_name]
            for title in titles:
                if title not in existing_titles:
                    products_to_create.append(
                        Product(
                            title=title,
                            description=self._description(title, cat_name),
                            price=self._price(cat_name),
                            category=cat,
                        )
                    )
                    existing_titles.add(title)


        total_after_first = Product.objects.count() + len(products_to_create)
        needed = max(0, 1000 - total_after_first)

        variant_suffixes = [
            "Pro", "Lite", "Plus", "Ultra", "Max", "Mini", "SE",
            "2024 Edition", "Limited Edition", "Special Pack",
            "Combo Pack", "Bundle", "Refurbished", "Renewed",
        ]

        all_templates = [
            (title, cat_name)
            for cat_name, titles in CATEGORY_PRODUCTS.items()
            for title in titles
        ]

        generated = 0
        idx = 0
        while generated < needed:
            base_title, cat_name = all_templates[idx % len(all_templates)]
            suffix = random.choice(variant_suffixes)
            variant_title = f"{base_title} - {suffix}"
            if variant_title not in existing_titles:
                products_to_create.append(
                    Product(
                        title=variant_title,
                        description=self._description(base_title, cat_name),
                        price=self._price(cat_name),
                        category=categories[cat_name],
                    )
                )
                existing_titles.add(variant_title)
                generated += 1
            idx += 1

        Product.objects.bulk_create(products_to_create, batch_size=200, ignore_conflicts=True)
        all_products = list(Product.objects.all())
        self.stdout.write(self.style.SUCCESS(f'  Total products: {len(all_products)}.'))

       
        self.stdout.write('Seeding stores...')
        for name, location in STORE_NAMES:
            Store.objects.get_or_create(name=name, defaults={'location': location})
        all_stores = list(Store.objects.all())
        self.stdout.write(self.style.SUCCESS(f'  Total stores: {len(all_stores)}.'))

        
        self.stdout.write('Seeding inventory...')
        total_inv = 0
        for store in all_stores:
            sample_size = min(len(all_products), random.randint(300, 500))
            store_products = random.sample(all_products, sample_size)

            existing_inv = set(
                Inventory.objects.filter(store=store).values_list('product_id', flat=True)
            )
            new_inv = [
                Inventory(
                    store=store,
                    product=p,
                    quantity=random.randint(0, 500),
                )
                for p in store_products
                if p.id not in existing_inv
            ]
            Inventory.objects.bulk_create(new_inv, batch_size=500, ignore_conflicts=True)
            total_inv += len(new_inv)

        self.stdout.write(self.style.SUCCESS(f'  Created {total_inv} inventory records.'))
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

   
 
    def _price(self, category: str) -> float:
        """Return a realistic price range for each category."""
        ranges = {
            "Electronics":     (499, 149999),
            "Fashion":         (299, 24999),
            "Grocery":         (29, 2999),
            "Home & Kitchen":  (199, 49999),
            "Sports":          (199, 14999),
            "Books":           (99, 1999),
            "Beauty":          (99, 4999),
            "Automotive":      (199, 19999),
            "Office Supplies": (29, 4999),
            "Toys":            (199, 9999),
        }
        lo, hi = ranges.get(category, (99, 9999))
        return round(random.uniform(lo, hi), 2)

    def _description(self, title: str, category: str) -> str:
        """Return a short realistic product description."""
        templates = [
            f"High-quality {title} designed for everyday use. A trusted choice in {category}.",
            f"Experience the best of {category} with {title}. Reliable, durable, and value for money.",
            f"{title} — a premium pick in the {category} segment. Loved by customers across India.",
            f"Upgrade your {category.lower()} experience with the {title}. Top-rated and highly recommended.",
        ]
        return random.choice(templates)