import unittest
import uuid
from unittest.mock import AsyncMock, patch

from asyncpg import UniqueViolationError
from fastapi import HTTPException

from app import main


class PhoneValidationTests(unittest.TestCase):
    def test_accepts_and_trims_e164_number(self):
        self.assertEqual(main._clean_phone("  +15550101234  "), "+15550101234")

    def test_rejects_local_or_formatted_numbers(self):
        invalid = (
            "5550101234",
            "+1 555 010 1234",
            "+1-555-010-1234",
            "+0123456789",
            "+1234567",
            "+1234567890123456",
            "+١٢٣٤٥٦٧٨٩",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(HTTPException) as caught:
                main._clean_phone(value)
            self.assertEqual(caught.exception.status_code, 400)


class RegistryUpdateTests(unittest.IsolatedAsyncioTestCase):
    async def test_replaces_saved_phone_number(self):
        bank_id = uuid.uuid4()
        request = object()
        with (
            patch.object(main, "gate", return_value=None),
            patch.object(main.db, "fetchrow", AsyncMock(return_value={"phone": "+15550101111"})),
            patch.object(main.db, "execute", AsyncMock(return_value="UPDATE 1")) as execute,
        ):
            response = await main.banks_update(
                request=request,
                bank_id=bank_id,
                name="Central Blood Bank",
                phone=" +15550102222 ",
                area="Central",
                notes="",
                active="on",
            )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(execute.await_args.args[3], "+15550102222")

    async def test_blank_replacement_keeps_saved_phone_number(self):
        bank_id = uuid.uuid4()
        request = object()
        with (
            patch.object(main, "gate", return_value=None),
            patch.object(main.db, "fetchrow", AsyncMock(return_value={"phone": "+15550101111"})),
            patch.object(main.db, "execute", AsyncMock(return_value="UPDATE 1")) as execute,
        ):
            await main.banks_update(
                request=request,
                bank_id=bank_id,
                name="Central Blood Bank",
                phone="",
                area="",
                notes="",
                active="",
            )

        self.assertEqual(execute.await_args.args[3], "+15550101111")

    async def test_invalid_replacement_is_not_saved(self):
        bank_id = uuid.uuid4()
        request = object()
        execute = AsyncMock()
        with (
            patch.object(main, "gate", return_value=None),
            patch.object(main.db, "fetchrow", AsyncMock(return_value={"phone": "+15550101111"})),
            patch.object(main.db, "execute", execute),
        ):
            with self.assertRaises(HTTPException) as caught:
                await main.banks_update(
                    request=request,
                    bank_id=bank_id,
                    name="Central Blood Bank",
                    phone="555-010-2222",
                    area="",
                    notes="",
                    active="on",
                )

        self.assertEqual(caught.exception.status_code, 400)
        execute.assert_not_awaited()

    async def test_rejects_a_number_owned_by_another_bank(self):
        bank_id = uuid.uuid4()
        request = object()
        with (
            patch.object(main, "gate", return_value=None),
            patch.object(main.db, "fetchrow", AsyncMock(return_value={"phone": "+15550101111"})),
            patch.object(
                main.db,
                "execute",
                AsyncMock(side_effect=UniqueViolationError("duplicate phone")),
            ),
        ):
            with self.assertRaises(HTTPException) as caught:
                await main.banks_update(
                    request=request,
                    bank_id=bank_id,
                    name="Central Blood Bank",
                    phone="+15550102222",
                    area="",
                    notes="",
                    active="on",
                )

        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(caught.exception.detail, "phone already belongs to another bank")


if __name__ == "__main__":
    unittest.main()
