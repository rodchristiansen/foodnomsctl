"""A synthetic FoodNoms store.

Column types follow the live schema, which is looser than it declares: `entryID`
and `collectionID` are TEXT columns holding the raw 16 bytes of a UUID, and
`measure`/`measures`/`nutrients` are BLOB columns holding JSON text. SQLite's
dynamic typing is why that works, and why a fixture has to reproduce the values
rather than the declarations.
"""
import json
import sqlite3
import uuid
from datetime import date

UNIX_EPOCH_JD = 2440587.5


def jd(when):
    return (date.fromisoformat(when) - date(1970, 1, 1)).days + UNIX_EPOCH_JD


def measure(unit, value, text=None, qty=1):
    m = {"traits": 0, "unit": unit, "value": value}
    if text:
        m["descriptionText"] = text
        m["descriptionQuantity"] = qty
    return m


SCHEMA = """
CREATE TABLE foodEntryRecord (
  id INTEGER PRIMARY KEY AUTOINCREMENT, entryID TEXT UNIQUE ON CONFLICT REPLACE,
  date DATETIME, day DOUBLE, collectionEditID TEXT, collectionSortIndex INTEGER,
  measure BLOB, quantity DOUBLE, mealTypeID TEXT, foodID TEXT, barcode TEXT,
  name TEXT, brandOwner TEXT, baseUnit TEXT, baseAmount DOUBLE,
  measures BLOB, nutrients BLOB, calories DOUBLE);
CREATE TABLE foodRecord (
  id INTEGER PRIMARY KEY AUTOINCREMENT, foodID TEXT, barcode TEXT, name TEXT,
  brandOwner TEXT, baseUnit TEXT, baseAmount DOUBLE, measures BLOB,
  nutrients BLOB, isHidden INTEGER, dateCreated DATETIME);
CREATE TABLE mealTypeRecord (
  id INTEGER PRIMARY KEY AUTOINCREMENT, mealTypeID TEXT, name TEXT,
  sortIndex INTEGER, disabled INTEGER, alwaysShowInLog INTEGER);
CREATE TABLE foodCollectionRecord (
  id INTEGER PRIMARY KEY AUTOINCREMENT, collectionID TEXT, collectionEditID TEXT,
  name TEXT, collectionType INTEGER);
"""

RICE = uuid.UUID("11111111-1111-4111-8111-111111111111")
CHIA = uuid.UUID("22222222-2222-4222-8222-222222222222")
WATER = uuid.UUID("33333333-3333-4333-8333-333333333333")
OLD_RICE = uuid.UUID("44444444-4444-4444-8444-444444444444")
MEAL_ITEM = uuid.UUID("55555555-5555-4555-8555-555555555555")
MEAL_ID = uuid.UUID("66666666-6666-4666-8666-666666666666")
MEAL_EDIT = uuid.UUID("77777777-7777-4777-8777-777777777777")
RECIPE_ID = uuid.UUID("88888888-8888-4888-8888-888888888888")


def entry(eid, name, when, **kw):
    row = {
        "entryID": eid.bytes, "name": name, "date": f"{when} 12:00:00.000",
        "day": jd(when), "collectionEditID": None, "collectionSortIndex": None,
        "measure": None, "quantity": 1.0, "mealTypeID": None, "foodID": None,
        "barcode": None, "brandOwner": None, "baseUnit": "gram",
        "baseAmount": 100.0, "measures": None, "nutrients": None, "calories": None,
    }
    row.update(kw)
    for k in ("measure", "measures", "nutrients"):
        if isinstance(row[k], (dict, list)):
            row[k] = json.dumps(row[k])
    return row


def rows():
    return [
        # A per-100g food logged as one 163g cup. The eaten/base calorie ratio is
        # the only correct scale factor here.
        entry(RICE, "Rice (White, Cooked)", "2026-09-05",
              foodID="foodnoms:usda:2708403", quantity=1.0,
              measure=measure("gram", 163, "cup, cooked"),
              measures=[measure("gram", 163, "cup, cooked")],
              nutrients={"calories": 129, "protein": 2.67, "carbs": 27.99,
                         "fat": 0.28, "fiber": 0.4, "sugars": 0.05, "sodium": 1},
              calories=210.27),
        # The tablespoon trap: quantity x measure.value would scale by 12, not 0.12.
        entry(CHIA, "Chia Seeds", "2026-09-05", brandOwner="Bulk",
              barcode="0068100084245", foodID="local:ABCD",
              measure=measure("gram", 12, "tbsp"),
              nutrients={"calories": 486, "protein": 16.5, "carbs": 42.1,
                         "fat": 30.7, "fiber": 34.4, "sugars": 0, "sodium": 16},
              calories=58.32),
        # Zero calories gives no ratio; the unit matches the base unit, so the
        # direct calculation is exact.
        entry(WATER, "Water", "2026-09-05", foodID="foodnoms:water",
              quantity=2.0, baseUnit="milliliter", baseAmount=100.0,
              measure=measure("milliliter", 250, "cup"),
              nutrients={"calories": 0, "protein": 0, "sodium": 1.2},
              calories=0.0),
        # An older logging of the same food, with the pre-reformulation numbers.
        # `catalog` must prefer the newer row and still count both.
        entry(OLD_RICE, "Rice (White, Cooked)", "2026-08-01",
              foodID="foodnoms:usda:2708403",
              measure=measure("gram", 150, "cup"),
              nutrients={"calories": 120, "protein": 2.0},
              calories=180.0),
        # Belongs to a saved meal: a component, never a separate thing eaten.
        entry(MEAL_ITEM, "Oat Milk", "2026-09-05", foodID="local:OATS",
              collectionEditID=MEAL_EDIT.bytes, collectionSortIndex=0,
              measure=measure("milliliter", 250),
              nutrients={"calories": 50, "protein": 2.0}, calories=125.0),
    ]


def build(path):
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    for r in rows():
        cols = ",".join(r)
        con.execute(f"INSERT INTO foodEntryRecord ({cols}) "
                    f"VALUES ({','.join('?' * len(r))})", list(r.values()))
    # A food saved to the library that has never been logged — what
    # `create-food` leaves behind. It has no entry, so it appears in the
    # catalog only through library_only().
    con.execute(
        "INSERT INTO foodRecord (foodID, name, brandOwner, baseUnit, baseAmount, "
        "measures, nutrients) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("local:99999999-9999-4999-8999-999999999999", "Unlogged Supplement",
         "Testworks", "serving", 1.0,
         json.dumps([measure("serving", 1, "capsule")]),
         json.dumps({"calories": 0, "zinc": 50})))
    # The six meal types FoodNoms ships. None carry a name — the app knows
    # them by id, which is why five and six read as Pre-/Post-Workout.
    con.executemany(
        "INSERT INTO mealTypeRecord (mealTypeID, name, sortIndex, disabled, "
        "alwaysShowInLog) VALUES (?,?,?,?,?)",
        [(str(i), None, i - 1, 0, 1 if i <= 4 else 0) for i in range(1, 7)])
    con.executemany(
        "INSERT INTO foodCollectionRecord "
        "(collectionID, collectionEditID, name, collectionType) VALUES (?,?,?,?)",
        [(MEAL_ID.bytes, MEAL_EDIT.bytes, "Morning Smoothie", 2),
         (RECIPE_ID.bytes, None, "House Granola", 3)])
    con.commit()
    con.close()
    return path
