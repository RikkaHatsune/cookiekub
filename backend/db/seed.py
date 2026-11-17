"""Идемпотентный seed CookieKub: товары, кафе, промокоды, демо-аккаунты, тикеты."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from decimal import Decimal

from werkzeug.security import generate_password_hash

from .connection import connect


@dataclass(frozen=True)
class ProductSeed:
    slug: str
    name: str
    short: str
    description: str
    price: int
    category: str
    stock: int
    sort: int


PRODUCTS = [
    ProductSeed(
        "klassicheskiy-kubik",
        "Классический кубик",
        "Хрустящие края, тягучая серединка и много шоколада.",
        "Наша визитная карточка: тесто на коричневом масле, бельгийский шоколад и щепотка морской соли. Печём небольшими партиями каждые два часа.",
        14900, "classic", 80, 10,
    ),
    ProductSeed(
        "shokoladnyy-krakl",
        "Шоколадный кракл",
        "Печенье с трещинками и жидким шоколадом внутри.",
        "Снаружи — тонкая сахарная корочка, внутри — тёплый шоколадный центр. Идеально к крепкому кофе.",
        18900, "chocolate", 60, 20,
    ),
    ProductSeed(
        "ovsyanaya-izum",
        "Овсяная с изюмом",
        "Мягкая овсянка, изюм и немного корицы.",
        "Совсем не скучная классика: крупные хлопья, сочный изюм и корица. Хороша и утром, и после обеда.",
        15900, "classic", 70, 30,
    ),
    ProductSeed(
        "dvoynoy-shokolad",
        "Двойной шоколад",
        "Какао-тесто и два вида шоколада.",
        "Для тех, кто считает, что шоколада много не бывает: тёмное какао в тесте, молочный и горький шоколад кусочками.",
        21900, "chocolate", 45, 40,
    ),
    ProductSeed(
        "mindalnyy-pesochnyy",
        "Миндальный песочный",
        "Рассыпчатое песочное тесто с миндальными лепестками.",
        "Нежное песочное тесто, миндальная мука и лепестки миндаля сверху. Хрустит, тает и пахнет марципаном.",
        23900, "nuts", 40, 50,
    ),
    ProductSeed(
        "fistashka-malina",
        "Фисташка-малина",
        "Фисташковый крем и кисло-сладкая малина.",
        "Тонкое печенье с фисташковой пастой, малиновым джемом и крошкой из белого шоколада. Наш самый весенний вкус.",
        26900, "nuts", 35, 60,
    ),
    ProductSeed(
        "kokos-limon",
        "Кокос-лимон",
        "Веганское печенье с кокосовой стружкой и цедрой.",
        "Без яиц и молока: кокосовая стружка, цедра лимона и кокосовое масло. Светлое, ароматное и совсем не тяжёлое.",
        19900, "vegan", 50, 70,
    ),
    ProductSeed(
        "bananovyy-vegan",
        "Банановый веган",
        "Мягкое печенье на банане и овсянке.",
        "Спелый банан, овсяные хлопья, грецкий орех и щепотка мускатного ореха. Без сахара и продуктов животного происхождения.",
        17900, "vegan", 55, 80,
    ),
    ProductSeed(
        "solenaya-karamel",
        "Солёная карамель",
        "Карамельная начинка и хлопья соли.",
        "Печенье с густой солёной карамелью внутри. Сладко, солёно и очень опасно — можно съесть всю коробку.",
        20900, "chocolate", 48, 90,
    ),
    ProductSeed(
        "pechenie-sendvich",
        "Печенье-сэндвич",
        "Два печенья и крем-чиз между ними.",
        "Два тонких печенья с кремом из сливочного сыра и ванилью. Упаковано так, чтобы удобно было взять с собой.",
        24900, "classic", 30, 100,
    ),
    ProductSeed(
        "podarochnyy-nabor",
        "Подарочный набор «Пекарня»",
        "9 печений, открытка и крафтовая коробка.",
        "Соберите набор из девяти вкусов: классика, шоколад, орехи и веган. Внутри — открытка с пожеланием и крафтовая коробка с лентой.",
        99000, "gift", 20, 110,
    ),
    ProductSeed(
        "novogodniy-kubik",
        "Новогодний кубик",
        "Пряничные специи, белый шоколад и мандарин.",
        "Сезонное печенье с корицей, имбирём, цедрой мандарина и белым шоколадом. Пахнет праздником даже в феврале.",
        28900, "gift", 25, 120,
    ),
]

CAFES = [
    ("sadovaya", "CookieKub на Садовой", "ул. Садовая, 12", "+7 (999) 123-45-67",
     "09:00", "21:00", Decimal("38.00"), Decimal("42.00"), 10),
    ("park", "CookieKub у Парка", "Парковый бульвар, 3", "+7 (999) 123-45-68",
     "10:00", "22:00", Decimal("68.00"), Decimal("30.00"), 20),
    ("naberezhnaya", "CookieKub на Набережной", "наб. Реки Пряной, 7", "+7 (999) 123-45-69",
     "08:00", "20:00", Decimal("55.00"), Decimal("72.00"), 30),
]

PROMOS = [
    # code, type, percent, amount, min_order, max_uses, starts, ends, active
    ("COOKIE10", "percent", 10, None, 0, None, None, None, True),
    ("SWEET500", "fixed", None, 50000, 150000, 100, None, None, True),
    ("FIRST15", "percent", 15, None, 50000, None, None, None, True),
    ("KUB20", "percent", 20, None, 200000, 50, None, "2027-12-31T23:59:59+03:00", True),
]


def seed(url: str | None = None, verbose: bool = True) -> None:
    with connect(url) as conn:
        # Supabase pooler иногда рвёт длинную транзакцию; seed идемпотентен,
        # поэтому фиксируем каждый шаг отдельно.
        conn.autocommit = True
        # --- кафе ---
        for slug, name, address, phone, opens, closes, x, y, sort in CAFES:
            conn.execute(
                """
                INSERT INTO cafes (slug, name, address, phone, opens_at, closes_at, map_x, map_y, sort_order)
                VALUES (%s, %s, %s, %s, %s::time, %s::time, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    phone = EXCLUDED.phone,
                    opens_at = EXCLUDED.opens_at,
                    closes_at = EXCLUDED.closes_at,
                    map_x = EXCLUDED.map_x,
                    map_y = EXCLUDED.map_y,
                    sort_order = EXCLUDED.sort_order
                """,
                (slug, name, address, phone, opens, closes, x, y, sort),
            )

        # --- товары ---
        for p in PRODUCTS:
            conn.execute(
                """
                INSERT INTO products
                    (slug, name, short_description, description, price_cents,
                     image_url, category, stock_qty, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    short_description = EXCLUDED.short_description,
                    description = EXCLUDED.description,
                    price_cents = EXCLUDED.price_cents,
                    image_url = EXCLUDED.image_url,
                    category = EXCLUDED.category,
                    stock_qty = EXCLUDED.stock_qty,
                    sort_order = EXCLUDED.sort_order
                """,
                (p.slug, p.name, p.short, p.description, p.price,
                 f"assets/cookies/{p.slug}.svg", p.category, p.stock, p.sort),
            )

        # --- промокоды (уникальность по upper(code)) ---
        for code, dtype, percent, amount, min_order, max_uses, starts, ends, active in PROMOS:
            row = conn.execute(
                "SELECT id FROM promos WHERE upper(code) = upper(%s)", (code,)
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE promos SET discount_type = %s, percent_value = %s,
                        amount_cents = %s, min_order_cents = %s, max_uses = %s,
                        starts_at = %s, ends_at = %s, is_active = %s
                    WHERE id = %s
                    """,
                    (dtype, percent, amount, min_order, max_uses, starts, ends, active, row["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO promos
                        (code, discount_type, percent_value, amount_cents, min_order_cents,
                         max_uses, starts_at, ends_at, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (code, dtype, percent, amount, min_order, max_uses, starts, ends, active),
                )

        # --- демо-аккаунты (пароли не перезаписываем) ---
        accounts = [
            ("admin@cookiekub.ru", "Admin123!", "Анна Пекарь", "admin"),
            ("user@cookiekub.ru", "User123!", "Кубик Денис", "user"),
        ]
        for email, password, name, role in accounts:
            exists = conn.execute(
                "SELECT id FROM users WHERE lower(email) = lower(%s)", (email,)
            ).fetchone()
            if not exists:
                conn.execute(
                    """
                    INSERT INTO users (email, password_hash, full_name, role, privacy_consent_at)
                    VALUES (%s, %s, %s, %s, now())
                    """,
                    (email, generate_password_hash(password), name, role),
                )

        # --- тикеты (только если их нет) ---
        ticket_count = conn.execute("SELECT count(*) AS n FROM tickets").fetchone()["n"]
        if ticket_count == 0:
            user = conn.execute(
                "SELECT id FROM users WHERE lower(email) = lower(%s)", ("user@cookiekub.ru",)
            ).fetchone()
            conn.execute(
                """
                INSERT INTO tickets (user_id, email, subject, category, message, status)
                VALUES (%s, %s, %s, %s, %s, 'open')
                """,
                (user["id"] if user else None, "user@cookiekub.ru",
                 "Не пришло письмо с заказом", "bug",
                 "Оформил заказ, но письмо на почту не пришло. Проверьте, пожалуйста."),
            )
            conn.execute(
                """
                INSERT INTO tickets (email, subject, category, message, status)
                VALUES (%s, %s, %s, %s, 'closed')
                """,
                ("gost@example.com", "Можно ли забрать заказ позже?", "question",
                 "Оформил самовывоз, но задержусь. Можно забрать через два часа?"),
            )

        conn.commit()

    if verbose:
        print("Seed применён: 12 товаров, 3 кафе, 4 промокода, 2 аккаунта, тикеты.")


def main() -> int:
    try:
        seed()
    except Exception as exc:  # noqa: BLE001
        print(f"ОШИБКА seed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
