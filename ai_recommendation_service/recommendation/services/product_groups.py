"""Static product groups used for cold-start and ID validation."""

PRODUCT_GROUPS = {
    'phone': list(range(1, 16)),
    'case': list(range(16, 31)),
    'charger': list(range(31, 46)),
    'laptop': list(range(46, 61)),
    'mouse': list(range(61, 76)),
    'keyboard': list(range(76, 91)),
    'headphone': list(range(91, 106)),
    'tablet': list(range(106, 121)),
    'tshirt': list(range(121, 136)),
    'shirt': list(range(136, 151)),
    'jacket': list(range(151, 166)),
    'jeans': list(range(166, 181)),
    'shorts': list(range(181, 196)),
    'shoes': list(range(196, 211)),
    'sandals': list(range(211, 226)),
    'bag': list(range(226, 241)),
    'backpack': list(range(241, 256)),
    'hat': list(range(256, 271)),
    'watch': list(range(271, 286)),
    'glasses': list(range(286, 301)),
}

ALL_PRODUCT_IDS = [pid for ids in PRODUCT_GROUPS.values() for pid in ids]
