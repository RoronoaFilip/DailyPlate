"""Imports must recognise headers, values, food names and file names regardless of capital letters."""

import tempfile
import unittest
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from calorie_tracker.domain.nutrition import Nutrients
from calorie_tracker.domain.recipes import Food
from calorie_tracker.infrastructure.csv_kind import CsvKind, classify_csv_text
from calorie_tracker.infrastructure.database import Database
from calorie_tracker.infrastructure.diary_csv_importer import CsvDiaryImporter
from calorie_tracker.infrastructure.file_kinds import CSV, IMAGE, ZIP, classify_file
from calorie_tracker.infrastructure.importer import CsvFoodImporter
from calorie_tracker.infrastructure.intake import diary_date_from_name
from calorie_tracker.infrastructure.recipe_csv_importer import CsvRecipeImporter
from calorie_tracker.infrastructure.repositories import FoodRepository, RecipeRepository
from calorie_tracker.infrastructure.zip_intake import ZipIntakeError, extract_zip

FOODS_HEADER = "food_name,basis,calories,fat,carbohydrates,protein"


class CaseInsensitiveImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        database = Database(self.root / "data" / "tracker.sqlite3")
        database.initialize()
        self.foods = FoodRepository(database)
        self.foods.save(Food("oats", "Oats", Nutrients(calories=Decimal("380"))))
        self.foods.save(Food("milk", "Milk", Nutrients(calories=Decimal("60"))))
        self.foods.save(Food("mliako", "Мляко", Nutrients(calories=Decimal("60"))))
        self.foods_importer = CsvFoodImporter(self.foods)
        self.diary_importer = CsvDiaryImporter(self.foods)
        self.recipe_importer = CsvRecipeImporter(self.foods, RecipeRepository(database, self.foods))

    def diary_rows(self, text):
        return self.diary_importer.preview_table(self.diary_importer.read_text(text)).rows

    # ---- headers and kind detection ---------------------------------------------------------------

    def test_headers_in_any_case_are_recognised_and_classified(self):
        cases = {
            CsvKind.DIARY: ("FOOD_NAME,GRAMS_EATEN,MEAL", "Food Name,Amount (G),Meal", "NAME,QUANTITY,TIME"),
            CsvKind.FOODS: ("FOOD_NAME,BASIS,CALORIES,FAT,CARBOHYDRATES,PROTEIN", "Name,KCAL,Fat,CARBS,Protein"),
            CsvKind.RECIPES: ("RECIPE_NAME,YIELD_G,INGREDIENT,AMOUNT", "Recipe Name,Ingredient,AMOUNT"),
        }
        for kind, headers in cases.items():
            for header in headers:
                with self.subTest(kind=kind, header=header):
                    self.assertEqual(classify_csv_text(header + "\nx,1,2,3,4,5\n"), kind)

    def test_uppercase_headers_import_like_lowercase_ones(self):
        rows = self.diary_rows("FOOD_NAME,GRAMS_EATEN,MEAL\nOats,50,Lunch\n")
        self.assertEqual([(row.amount_g, row.meal, row.catalogue_item_id) for row in rows],
                         [(Decimal("50"), "Lunch", "oats")])

    # ---- values -----------------------------------------------------------------------------------

    def test_meal_words_in_any_case(self):
        for text, expected in (("BREAKFAST", "Breakfast"), ("snacks", "Snacks"), ("Snack", "Snacks"),
                               (" dinner ", "Dinner"), ("LuNcH", "Lunch")):
            with self.subTest(meal=text):
                rows = self.diary_rows(f"food_name,grams,meal\nOats,50,{text}\n")
                self.assertEqual((rows[0].meal, rows[0].error), (expected, None))

    def test_basis_words_in_any_case(self):
        for text, expected in (("COUNT", "count"), ("Per Item", "count"), ("EACH", "count"),
                               ("G", "g"), ("GRAMS", "g"), ("PER 100 G", "g")):
            with self.subTest(basis=text):
                preview = self.foods_importer.preview_table(
                    self.foods_importer.read_text(f"{FOODS_HEADER}\nX,{text},1,1,1,1\n"))
                self.assertEqual([row.food.basis for row in preview.foods], [expected])

    def test_units_after_amounts_in_any_case(self):
        for amount in ("45 G", "45 GRAMS", "45G", "45 g"):
            with self.subTest(amount=amount):
                rows = self.diary_rows(f'food_name,grams,meal\nOats,"{amount}",Lunch\n')
                self.assertEqual(rows[0].amount_g, Decimal("45"))

    # ---- food names -------------------------------------------------------------------------------

    def test_food_names_match_in_any_case_for_latin_and_cyrillic(self):
        for name, expected in (("OATS", "oats"), ("oats", "oats"), ("  OaTs ", "oats"),
                               ("МЛЯКО", "mliako"), ("мляко", "mliako"), ("Мляко", "mliako")):
            with self.subTest(name=name):
                self.assertEqual(self.diary_rows(f"food_name,grams,meal\n{name},50,Lunch\n")[0].catalogue_item_id, expected)

    def test_a_food_that_exists_in_another_case_is_a_name_conflict_not_a_second_food(self):
        for name in ("OATS", "oats", "МЛЯКО"):
            with self.subTest(name=name):
                preview = self.foods_importer.preview_table(
                    self.foods_importer.read_text(f"{FOODS_HEADER}\n{name},g,380,7,60,13\n"))
                result = self.foods_importer.apply(preview)
                self.assertEqual((result.imported, result.name_conflicts), (0, 1))

    def test_the_same_food_twice_in_one_file_in_different_case_is_a_duplicate(self):
        preview = self.foods_importer.preview_table(self.foods_importer.read_text(
            "food_name,calories,fat,carbohydrates,protein\nRice,1,1,1,1\nRICE,2,2,2,2\n"))
        self.assertEqual(len(preview.foods), 1)
        self.assertEqual([row.status for row in preview.rows], ["ready", "duplicate"])

    def test_recipe_names_and_ingredients_in_any_case(self):
        table = self.recipe_importer.read_text(
            "recipe_name,yield_g,ingredient,amount\nPorridge,,OATS,50\nPORRIDGE,,milk,200\n")
        items = self.recipe_importer.preview_table(table).items
        self.assertEqual(len(items), 1)  # both rows belong to one recipe
        self.assertEqual(items[0].status, "ready")

    # ---- file and folder names --------------------------------------------------------------------

    def test_file_extensions_in_any_case(self):
        for name, kind in (("DATA.CSV", CSV), ("PHOTO.JPG", IMAGE), ("Bundle.ZIP", ZIP)):
            with self.subTest(name=name):
                path = self.root / name
                path.write_bytes(b"x")
                self.assertEqual(classify_file(path), kind)

    def test_diary_dates_in_file_names_in_any_case(self):
        self.assertEqual(diary_date_from_name("DIARY-2026-10-05.CSV"), date(2026, 10, 5))

    def test_zip_members_and_folders_in_any_case(self):
        def make(members, name="x.zip"):
            path = self.root / name
            with zipfile.ZipFile(path, "w") as archive:
                for member in members:
                    archive.writestr(member, b"x")
            return path

        found = extract_zip(make(["FOODS.CSV", "Photos/A.JPG"]), self.root / "w1")
        self.assertEqual(len(found), 2)
        merged = extract_zip(make(["Photos/a.jpg", "photos/b.jpg"], "y.zip"), self.root / "w2")
        self.assertEqual(len(merged), 2)  # "Photos" and "photos" are one folder
        with self.assertRaises(ZipIntakeError):
            extract_zip(make(["photos/a.jpg", "data/b.csv"], "z.zip"), self.root / "w3")
        junk = extract_zip(make(["f/a.csv", "__MacOSX/f/._a.csv", "__MACOSX/x.csv"], "m.zip"), self.root / "w4")
        self.assertEqual(len(junk), 1)


if __name__ == "__main__":
    unittest.main()
