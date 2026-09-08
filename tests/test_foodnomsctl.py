"""Tests over a synthetic store.

The CLI has no third-party dependencies and neither do these; `unittest` and a
fixture database are enough, and they run without FoodNoms installed. What is
worth testing is the arithmetic and the matching — the places where a wrong
answer looks like a right one.
"""
import importlib.util
import os
import re
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

    # The bridge name is configurable (FOODNOMSCTL_BRIDGE), so these anchor on
    # whatever this build actually dispatches to rather than on a literal.
    def test_exact_name_only(self):
        self.assertEqual(fn.bridge_installed(f"Log Water\n{fn.BRIDGE}\n"),
                         (True, []))

    def test_a_numbered_copy_is_not_the_bridge(self):
        other = fn.BRIDGE + " 9"
        present, near = fn.bridge_installed(f"Log Water\n{other}\n")
        self.assertFalse(present)
        self.assertEqual(near, [other])

    def test_surrounding_whitespace_does_not_hide_it(self):
        self.assertTrue(fn.bridge_installed(f"  {fn.BRIDGE}  \n")[0])

    def test_an_empty_library_is_not_a_crash(self):
        self.assertEqual(fn.bridge_installed(""), (False, []))
        self.assertEqual(fn.bridge_installed(None), (False, []))


class TestRequiredMacros(unittest.TestCase):
    """The guard on the four macros FoodNoms insists on.

    Without it, a `log` missing one does not fail — FoodNoms puts up its own
    prompt and waits, so a headless run blocks on a dialog nobody can answer.
    """

    def test_all_four_present_is_clean(self):
        self.assertEqual(fn.missing_macros(
            {"energyCalories": 100, "protein": 5, "carbs": 2, "fat": 1}), [])

    def test_zero_is_a_value_not_a_gap(self):
        self.assertEqual(fn.missing_macros(
            {"energyCalories": 0, "protein": 0, "carbs": 0, "fat": 0}), [])

    def test_names_every_missing_one_as_its_flag(self):
        self.assertEqual(fn.missing_macros({"energyCalories": 7, "protein": 1}),
                         ["--carbs", "--fat"])

    def test_the_optional_three_are_not_required(self):
        # The nine-item meal that logged unattended supplied the four and
        # omitted fiber, sugars and sodium.
        self.assertEqual(fn.missing_macros(
            {"energyCalories": 560, "protein": 18, "carbs": 48, "fat": 34}), [])


class TestBridgeVersioning(unittest.TestCase):
    """Picking the bridge to dispatch through.

    Builds are stamped because importing never replaces a same-named Shortcut,
    so a rebuild under a fixed name leaves the old actions answering.
    """

    def pick(self, names, env=None):
        real_names, real_env = fn.library_names, os.environ.get("FOODNOMSCTL_BRIDGE")
        fn.library_names = lambda: names
        if env: os.environ["FOODNOMSCTL_BRIDGE"] = env
        else: os.environ.pop("FOODNOMSCTL_BRIDGE", None)
        try:
            return fn.find_bridge()
        finally:
            fn.library_names = real_names
            if real_env is not None: os.environ["FOODNOMSCTL_BRIDGE"] = real_env
            else: os.environ.pop("FOODNOMSCTL_BRIDGE", None)

    def test_newest_stamp_wins(self):
        self.assertEqual(self.pick([
            "Log Water",
            "FoodNomsCTL Bridge 2026.09.07.0900",
            "FoodNomsCTL Bridge 2026.09.07.1729",
            "FoodNomsCTL Bridge 2026.08.30.2201",
        ]), "FoodNomsCTL Bridge 2026.09.07.1729")

    def test_stamps_sort_by_time_not_string_length(self):
        self.assertEqual(self.pick([
            "FoodNomsCTL Bridge 2026.09.07.0900",
            "FoodNomsCTL Bridge 2026.10.01.0001",
        ]), "FoodNomsCTL Bridge 2026.10.01.0001")

    def test_a_stamped_build_beats_an_unstamped_one(self):
        self.assertEqual(self.pick([
            "FoodNomsCTL Bridge 3",
            "FoodNomsCTL Bridge 2026.09.07.1729",
        ]), "FoodNomsCTL Bridge 2026.09.07.1729")

    def test_falls_back_to_a_legacy_name(self):
        self.assertEqual(self.pick(["FoodNomsCTL Bridge 3"]),
                         "FoodNomsCTL Bridge 3")

    def test_the_env_override_wins_over_everything(self):
        self.assertEqual(self.pick(["FoodNomsCTL Bridge 2026.09.07.1729"],
                                   env="Some Other Bridge"), "Some Other Bridge")


_bspec = importlib.util.spec_from_loader(
    "fnbridge", SourceFileLoader("fnbridge", os.path.join(HERE, os.pardir, "foodnomsctl-bridge")))
fb = importlib.util.module_from_spec(_bspec)
_bspec.loader.exec_module(fb)


def _venc(n):
    out = bytearray()
    while True:
        x = n & 0x7f; n >>= 7
        if n: out.append(x | 0x80)
        else: out.append(x); return bytes(out)


def _f(field, payload):
    """One length-delimited protobuf field."""
    return bytes([(field << 3) | 2]) + _venc(len(payload)) + payload


def _v(field, n):
    return bytes([field << 3]) + _venc(n)


class TestFolderIdentifiers(unittest.TestCase):
    """Reading a folder's identifier out of the Library CRDT record.

    A synthetic document in the shape the decoder relies on: a string table
    under doc field 2, and ops under top-level field 4 whose field 5 carries an
    inline object id and whose field 4 holds a register set to a string ref.
    """

    def blob(self):
        strs = ["name", "shortcuts", "Nutrition", "Fitness"]
        doc = b"".join(_f(2, s.encode()) for s in strs)
        def op(obj, str_idx):
            reg = _f(2, _v(3, str_idx))
            return _f(4, _f(4, _f(2, reg)) + _f(5, _f(2, b"\x01" + obj.encode())))
        body = (_f(6, doc)
                + op("24C2199D-AFF4-44F8-935A-AA54194CDA47", 2)
                + op("EBD7D7DE-179B-4F35-9628-FF10B83276E4", 3)
                # A shortcut object naming itself must not be mistaken for a folder.
                + op("2D6D9DB2-DB7B-4B87-BE89-CD1469938158", 2))
        return b"crdt\x07\x00\x00\x00" + body

    def test_pairs_each_folder_name_with_its_object_id(self):
        real = fb.library_workflows
        fb.library_workflows = lambda: {"Bridge": "2D6D9DB2-DB7B-4B87-BE89-CD1469938158"}
        try:
            got = fb.folder_identifiers(self.blob())
        finally:
            fb.library_workflows = real
        self.assertEqual(got, {"Nutrition": "24C2199D-AFF4-44F8-935A-AA54194CDA47",
                               "Fitness": "EBD7D7DE-179B-4F35-9628-FF10B83276E4"})

    def test_a_non_crdt_blob_yields_nothing(self):
        self.assertEqual(fb.folder_identifiers(b"bplist00junk"), {})

    def test_the_filer_binds_both_entities_as_literals(self):
        w = fb.build_filer("ZZ Filer 1", "Bridge", "2D6D9DB2-DB7B-4B87-BE89-CD1469938158",
                           "Nutrition", "24C2199D-AFF4-44F8-935A-AA54194CDA47",
                           [("ZZ Filer 0", "00000000-0000-4000-8000-000000000000")])
        acts = w["WFWorkflowActions"]
        move = acts[1]["WFWorkflowActionParameters"]
        # The editor's own shape for a picked folder: title/subtitle keys and the
        # bare collection UUID. The displayString envelope falls through to the
        # picker even with the right UUID.
        self.assertEqual(move["folder"], {"title": {"key": "Nutrition"},
                                          "subtitle": {"key": "Nutrition"},
                                          "identifier": "24C2199D-AFF4-44F8-935A-AA54194CDA47"})
        self.assertEqual(move["shortcuts"][0]["identifier"], "2D6D9DB2-DB7B-4B87-BE89-CD1469938158")
        self.assertFalse(move["ShowWhenRun"])
        self.assertEqual(acts[2]["WFWorkflowActionIdentifier"], "com.apple.shortcuts.DeleteWorkflowAction")


class TestStoreDiscovery(unittest.TestCase):
    def test_the_abandoned_stores_are_named_so_they_can_be_ruled_out(self):
        # Both are still on disk on any machine that has run FoodNoms for long
        # enough, both are populated, and both answer confidently with data
        # years stale.
        self.assertTrue(all("Group Containers" in p for p in fn.LEGACY))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestCreateFoodPanel(unittest.TestCase):
    """create-food exposes exactly the nutrient panel the manifest sends."""

    def manifest_params(self):
        text = open(os.path.join(HERE, os.pardir, "intents.yaml")).read()
        block = text.split("- command: create-food", 1)[1].split("\n  - command:", 1)[0]
        return set(re.findall(r"^\s{6}(\w+): \{type: number\}", block, re.M))

    def test_every_numeric_manifest_param_has_a_flag(self):
        dests = {dest for _, dest in fn.NUTRIENT_FLAGS} | {"servingMetricAmount"}
        self.assertEqual(self.manifest_params(), dests)

    def test_micronutrients_are_in_the_panel(self):
        dests = {dest for _, dest in fn.NUTRIENT_FLAGS}
        for key in ("vitaminD", "vitaminK", "biotin", "zinc", "copper", "magnesium",
                    "molybdenum", "fatPolyunsaturated"):
            self.assertIn(key, dests)


class TestLibraryOnlyFoods(StoreTest):
    """A food saved to the library but never logged is still findable.

    `create-food` leaves exactly this behind, and a script that creates a food
    and then cannot resolve it is worse than one that never created it.
    """

    def test_it_appears_in_the_catalog(self):
        names = {f["name"] for f in fn.catalog(self.con)}
        self.assertIn("Unlogged Supplement", names)

    def test_search_finds_it_with_no_logged_history(self):
        hits = fn.search(self.con, "unlogged supplement")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["food_id"],
                         "local:99999999-9999-4999-8999-999999999999")
        self.assertEqual(hits[0]["calories"], 0)
        self.assertEqual(hits[0]["count"], 0)
        self.assertIsNone(hits[0]["last_logged"])

    def test_a_logged_food_is_not_duplicated_by_its_library_row(self):
        names = [f["name"] for f in fn.catalog(self.con)]
        self.assertEqual(len(names), len(set(names)))

    def test_it_carries_a_measure_an_action_can_send(self):
        hit = fn.search(self.con, "unlogged supplement")[0]
        self.assertEqual(hit["measure"]["unit"], "serving")
        self.assertEqual(hit["unit"], "serving")

    def test_a_min_count_excludes_it(self):
        names = {f["name"] for f in fn.catalog(self.con, min_count=2)}
        self.assertNotIn("Unlogged Supplement", names)


class TestDayComponents(StoreTest):
    """`day --components` shows what actually hit the log.

    Logging a saved Meal writes one row per item and none named after the
    meal, so the default view — which hides components — shows nothing, and a
    caller checking whether the write landed concludes it failed.
    """

    def test_components_are_hidden_by_default(self):
        names = {e["name"] for e in fn.day(self.con, "2026-09-05")["entries"]}
        self.assertNotIn("Oat Milk", names)

    def test_components_can_be_asked_for(self):
        names = {e["name"] for e in
                 fn.day(self.con, "2026-09-05", components=True)["entries"]}
        self.assertIn("Oat Milk", names)

    def test_totals_are_withheld_when_components_are_included(self):
        self.assertIsNone(fn.day(self.con, "2026-09-05", components=True)["totals"])
        self.assertIsNotNone(fn.day(self.con, "2026-09-05")["totals"])
