"""Tests over a synthetic store.

The CLI has no third-party dependencies and neither do these; `unittest` and a
fixture database are enough, and they run without FoodNoms installed. What is
worth testing is the arithmetic and the matching — the places where a wrong
answer looks like a right one.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture  # noqa: E402

# The CLI ships as `foodnomsctl` with no extension, so it is loaded by path.
_spec = importlib.util.spec_from_loader(
    "fnctl", SourceFileLoader("fnctl", os.path.join(HERE, os.pardir, "foodnomsctl")))
fn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fn)


class StoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="foodnomsctl-tests.")
        cls.db = fixture.build(os.path.join(cls.tmp, "db.db"))

    def setUp(self):
        self.con = fn.connect(self.db)

    def food(self, name, when="2026-09-05"):
        for e in fn.day(self.con, when)["entries"]:
            if e["name"] == name:
                return e
        self.fail(f"{name} not in the log for {when}")


class TestJulianDay(StoreTest):
    def test_matches_the_apps_own_day_key(self):
        # Anchored on a value read out of a live store, not on a re-derivation
        # of the same formula: an entry stamped 2026-09-05 01:51 UTC carries
        # day = 2461287.5, which is 2026-09-04 in Vancouver. Dates are UTC and
        # `day` is the app's local-day key, which is the whole reason `day`
        # queries that column instead of a date range.
        self.assertEqual(fn.julian_day("2026-09-04"), 2461287.5)

    def test_is_a_local_day_not_a_utc_window(self):
        self.assertEqual(fn.julian_day("2026-09-06") - fn.julian_day("2026-09-05"), 1)


class TestNutrients(StoreTest):
    def test_scales_by_the_calorie_ratio(self):
        rice = self.food("Rice (White, Cooked)")
        self.assertAlmostEqual(rice["calories"], 210.27, places=2)
        self.assertAlmostEqual(rice["carbs"], 45.62, places=1)
        self.assertAlmostEqual(rice["protein"], 4.35, places=1)

    def test_a_tablespoon_of_a_per_100g_food_is_not_a_hundred_grams(self):
        # The bug this guards: scaling by quantity x measure.value turns one
        # tablespoon of chia into 486 kcal and 16.5 g of protein.
        chia = self.food("Chia Seeds")
        self.assertAlmostEqual(chia["calories"], 58.32, places=2)
        self.assertAlmostEqual(chia["protein"], 1.98, places=2)
        self.assertLess(chia["fat"], 5)

    def test_zero_calorie_foods_fall_back_to_the_direct_calculation(self):
        # No ratio to work from, but the logged unit is the base unit, so
        # quantity x measure size over base amount is exact: 2 x 250 / 100.
        water = self.food("Water")
        self.assertEqual(water["calories"], 0)
        self.assertAlmostEqual(water["sodium"], 6.0, places=2)

    def test_a_missing_nutrient_stays_none_rather_than_becoming_zero(self):
        self.assertIsNone(self.food("Water")["fiber"])


class TestIds(unittest.TestCase):
    def test_decodes_the_raw_sixteen_bytes(self):
        self.assertEqual(fn.as_uuid(fixture.RICE.bytes),
                         str(fixture.RICE).upper())

    def test_anything_else_is_not_an_id(self):
        self.assertIsNone(fn.as_uuid(None))
        self.assertIsNone(fn.as_uuid(b"short"))


class TestCatalog(StoreTest):
    def test_the_most_recent_logging_is_canonical(self):
        rice = next(f for f in fn.catalog(self.con)
                    if f["name"] == "Rice (White, Cooked)")
        self.assertEqual(rice["count"], 2)
        self.assertEqual(rice["last_logged"], "2026-09-05 12:00:00.000")
        # The newer row's measure and macros, not the August ones.
        self.assertEqual(rice["unit_quantity"], 163)
        self.assertAlmostEqual(rice["calories"], 210.27, places=2)

    def test_min_count_filters(self):
        names = {f["name"] for f in fn.catalog(self.con, min_count=2)}
        self.assertEqual(names, {"Rice (White, Cooked)"})

    def test_since_narrows_the_window(self):
        rice = next(f for f in fn.catalog(self.con, since="2026-09-01")
                    if f["name"] == "Rice (White, Cooked)")
        self.assertEqual(rice["count"], 1)


class TestSearch(StoreTest):
    def test_by_name_is_a_case_insensitive_substring(self):
        self.assertEqual([f["name"] for f in fn.search(self.con, "RICE")],
                         ["Rice (White, Cooked)"])

    def test_by_barcode(self):
        hits = fn.search(self.con, "barcode:0068100084245")
        self.assertEqual([f["name"] for f in hits], ["Chia Seeds"])

    def test_by_id_in_full(self):
        hits = fn.search(self.con, "id:foodnoms:usda:2708403")
        self.assertEqual([f["name"] for f in hits], ["Rice (White, Cooked)"])

    def test_by_id_tail_finds_a_food_pinned_against_the_old_store(self):
        # The old store kept service and serviceID apart, so anything written
        # then says `usda:2708403` where the live store says `foodnoms:usda:…`.
        hits = fn.search(self.con, "id:usda:2708403")
        self.assertEqual([f["name"] for f in hits], ["Rice (White, Cooked)"])

    def test_a_tail_match_is_on_a_colon_boundary(self):
        # The final segment alone matches, since it is a whole segment.
        self.assertEqual([f["name"] for f in fn.search(self.con, "id:2708403")],
                         ["Rice (White, Cooked)"])
        # Part of a segment does not, so an id is never matched by accident.
        self.assertEqual(fn.search(self.con, "id:08403"), [])

    def test_no_match_is_empty(self):
        self.assertEqual(fn.search(self.con, "kohlrabi"), [])


class TestDay(StoreTest):
    def test_excludes_the_components_of_a_saved_meal(self):
        names = [e["name"] for e in fn.day(self.con, "2026-09-05")["entries"]]
        self.assertNotIn("Oat Milk", names)
        self.assertEqual(len(names), 3)

    def test_totals_are_the_sum_of_what_was_eaten(self):
        totals = fn.day(self.con, "2026-09-05")["totals"]
        self.assertAlmostEqual(totals["calories"], 268.6, places=1)
        self.assertAlmostEqual(totals["protein"], 6.3, places=1)

    def test_a_day_with_nothing_logged_is_empty_not_an_error(self):
        res = fn.day(self.con, "2026-01-01")
        self.assertEqual(res["entries"], [])
        self.assertEqual(res["totals"]["calories"], 0)


class TestMeals(StoreTest):
    def test_a_meal_carries_its_items_and_the_uuid_the_intent_takes(self):
        m = fn.meals(self.con)
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0]["name"], "Morning Smoothie")
        self.assertEqual(m[0]["meal_id"], str(fixture.MEAL_ID).upper())
        self.assertEqual([i["name"] for i in m[0]["items"]], ["Oat Milk"])

    def test_recipes_are_a_different_collection_type(self):
        self.assertEqual([r["name"] for r in fn.meals(self.con, kind=fn.RECIPE)],
                         ["House Granola"])

    def test_filtering_by_name_is_a_substring(self):
        self.assertEqual(len(fn.meals(self.con, "smoothie")), 1)
        self.assertEqual(fn.meals(self.con, "granola"), [])


class TestBridgeInstalled(unittest.TestCase):
    """The write path's health check.

    A substring test here reported the bridge installed while `shortcuts run`
    failed, because importing never replaces and a rebuild lands beside the old
    copy under a new name.
    """

    def test_exact_name_only(self):
        self.assertEqual(fn.bridge_installed("Log Water\nFoodNomsCTL Bridge\n"),
                         (True, []))

    def test_a_numbered_copy_is_not_the_bridge(self):
        present, near = fn.bridge_installed("Log Water\nFoodNomsCTL Bridge 3\n")
        self.assertFalse(present)
        self.assertEqual(near, ["FoodNomsCTL Bridge 3"])

    def test_surrounding_whitespace_does_not_hide_it(self):
        self.assertTrue(fn.bridge_installed("  FoodNomsCTL Bridge  \n")[0])

    def test_an_empty_library_is_not_a_crash(self):
        self.assertEqual(fn.bridge_installed(""), (False, []))
        self.assertEqual(fn.bridge_installed(None), (False, []))


class TestStoreDiscovery(unittest.TestCase):
    def test_the_abandoned_stores_are_named_so_they_can_be_ruled_out(self):
        # Both are still on disk on any machine that has run FoodNoms for long
        # enough, both are populated, and both answer confidently with data
        # years stale.
        self.assertTrue(all("Group Containers" in p for p in fn.LEGACY))


if __name__ == "__main__":
    unittest.main(verbosity=2)
